# main.py
import time
import os
import tkinter as tk
from tkinter import filedialog, messagebox, Radiobutton, Toplevel
import traceback
from tkinter.ttk import Progressbar
import logging
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed
from pdf_processor import split_pdf_by_layout  # 引入PDF遍历和分割模块
import file_reader  # 引入文件读取模块

# 从 pw.py 文件中导入配置信息
from pw import API_KEY, BASE_URL, MODEL_NAME

os.environ['LIBPNG_WARNING_LEVEL'] = '2'  # 设置为2可以抑制警告
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 更改 API 密钥和基础 URL 为火山接口的信息
client = OpenAI(
    api_key=API_KEY,  # 火山接口 API 密钥
    base_url=BASE_URL,  # 火山接口域名
)

def extract_time_openai(text):
    """
    使用火山接口模型从文本中提取时间信息
    """
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,  # 火山接口模型名称
            messages=[{
                "role": "user",
                "content": f"假设你是文件重命名助手，分析文件生成时间与主要内容，以 “yyyymmdd_标题” 格式返回。若无法识别时间，以 “00000000_标题” 格式输出，标题简洁，不超 20 字。不需要任何解释。不需要解析过程。{text}"
            }]
        )
        logging.info("成功调用火山接口 API")
        result = response.choices[0].message.content.strip()
        return result
    except Exception as e:
        error_message = f"调用火山接口 API 时出错：{e}"
        logging.error(error_message, exc_info=True)
        messagebox.showerror("错误", error_message)
        return None

def get_files(directory):
    """
    让用户选择一个文件夹，并返回该文件夹下的所有文件路径列表
    """
    if directory:
        file_list = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                file_list.append(file_path)
        return file_list
    return []

def sanitize_filename(filename):
    """
    过滤掉文件名中的非法字符
    """
    return "".join(x for x in filename if x.isalnum() or x in "._- ")

def process_file(file, progress_bar, total_files):
    """
    处理单个文件
    """
    try:
        start_time = time.time()  # 记录开始时间
        content = file_reader.get_file_content(file)
        if content is None:
            print(f"读取文件 {file} 失败")  # 输出读取文件失败信息
            return (file, None, None)

        content_length = len(content)  # 记录文件内容长度

        time_info = extract_time_openai(content)
        if time_info:
            file_dir = os.path.dirname(file)
            file_ext = os.path.splitext(file)[1]
            new_file_name = sanitize_filename(f"{time_info}{file_ext}")
            new_file_path = os.path.join(file_dir, new_file_name)
            os.rename(file, new_file_path)
            end_time = time.time()  # 记录结束时间
            elapsed_time = end_time - start_time  # 计算用时
            print(f"文件 {file} 已重命名为 {new_file_path}，用时: {elapsed_time:.2f} 秒")  # 输出成功信息和用时
            logging.info(f"文件 {file} 已重命名为 {new_file_path}")
            return (file, elapsed_time, content_length)
        else:
            print(f"文件 {file} 处理失败，未获取到时间信息")  # 输出处理失败信息
            return (file, None, content_length)
    except Exception as e:
        logging.error(f"处理文件 {file} 时出错：{e}", exc_info=True)
        error_message = f"处理文件 {file} 时出错：{e}\n详细信息：\n{traceback.format_exc()}"
        messagebox.showerror("错误", error_message)
        print(f"处理文件 {file} 失败")  # 输出处理文件失败信息
        return (file, None, None)

def process_files():
    """
    处理多个文件
    """
    directory = filedialog.askdirectory()
    if not directory:
        return

    # 创建一个弹出窗口来选择处理选项
    option_window = Toplevel(root)
    option_window.title("选项")
    option_window.geometry("300x150")

    process_option = tk.IntVar(value=3)  # 默认选择“进行分割和识别”

    only_recognize_radio = Radiobutton(option_window, text="仅进行识别不分割", variable=process_option, value=1)
    only_recognize_radio.pack(pady=5)

    only_split_radio = Radiobutton(option_window, text="仅进行分割不识别", variable=process_option, value=2)
    only_split_radio.pack(pady=5)

    both_radio = Radiobutton(option_window, text="进行分割和识别", variable=process_option, value=3)
    both_radio.pack(pady=5)

    def on_confirm():
        option_window.destroy()
        process_files_with_options(directory, process_option.get())

    confirm_button = tk.Button(option_window, text="确认", command=on_confirm)
    confirm_button.pack(pady=10)

def process_files_with_options(directory, process_option):
    """
    处理多个文件，根据选项决定是否进行PDF分割以及是否进行文件内容的识别和重命名
    """
    if process_option == 1:  # 仅进行识别不分割
        files = get_files(directory)

        if not files:
            return

        total_files = len(files)
        progress_bar = Progressbar(root, orient='horizontal', length=300, mode='determinate')
        progress_bar.pack(pady=10)
        progress_bar['maximum'] = total_files
        processed_count = 0

        def update_progress(value):
            percent = int((value / total_files) * 100)
            progress_label.config(text=f"{percent}% 完成")
            progress_bar['value'] = value
            root.update_idletasks()

        file_times = {}  # 用于存储每个文件的处理时间
        file_sizes = {}  # 用于存储每个文件的内容长度

        total_elapsed_time = 0  # 总处理时间
        total_content_length = 0  # 总内容长度

        with ThreadPoolExecutor(max_workers=1) as executor:  # 创建一个线程池，最大线程数为 1
            futures = {executor.submit(process_file, file, progress_bar, total_files): file for file in files}
            for future in as_completed(futures):
                try:
                    file, elapsed_time, content_length = future.result()
                    if elapsed_time is not None:
                        file_times[file] = elapsed_time
                        total_elapsed_time += elapsed_time
                    if content_length is not None:
                        file_sizes[file] = content_length
                        total_content_length += content_length
                    processed_count += 1
                    update_progress(processed_count)
                except Exception as e:
                    logging.error(f"处理文件时出错：{e}")

        # 输出每个文件的处理时间
        print("\n每个文件的处理时间：")
        for file, elapsed_time in file_times.items():
            print(f"{file}: {elapsed_time:.2f} 秒")

        # 输出每个文件的内容长度
        print("\n每个文件的内容长度：")
        for file, content_length in file_sizes.items():
            print(f"{file}: {content_length} 字节")

        # 输出总的文件处理时间和总的文件内容长度
        print(f"\n总的文件处理时间: {total_elapsed_time:.2f} 秒")
        print(f"总的文件内容长度: {total_content_length} 字节")

        messagebox.showinfo("完成", "文件处理已完成。")
        progress_bar.destroy()  # 关闭进度条
        progress_label.config(text="处理已完成")

    elif process_option == 2:  # 仅进行分割不识别
        try:
            pdf_files = get_files(directory)
            pdf_files = [file for file in pdf_files if file.lower().endswith('.pdf')]
            for pdf_file in pdf_files:
                logging.info(f"开始分割 PDF 文件: {pdf_file}")
                split_pdf_by_layout(pdf_file, directory)
                logging.info(f"完成分割 PDF 文件: {pdf_file}")
            messagebox.showinfo("完成", "仅进行了PDF分割。")
        except Exception as e:
            messagebox.showerror("错误", f"处理 PDF 文件时出错：{e}")

    elif process_option == 3:  # 进行分割和识别
        try:
            pdf_files = get_files(directory)
            pdf_files = [file for file in pdf_files if file.lower().endswith('.pdf')]
            for pdf_file in pdf_files:
                logging.info(f"开始分割 PDF 文件: {pdf_file}")
                split_pdf_by_layout(pdf_file, directory)
                logging.info(f"完成分割 PDF 文件: {pdf_file}")
        except Exception as e:
            messagebox.showerror("错误", f"处理 PDF 文件时出错：{e}")
            return

        files = get_files(directory)

        if not files:
            return

        total_files = len(files)
        progress_bar = Progressbar(root, orient='horizontal', length=300, mode='determinate')
        progress_bar.pack(pady=10)
        progress_bar['maximum'] = total_files
        processed_count = 0

        def update_progress(value):
            percent = int((value / total_files) * 100)
            progress_label.config(text=f"{percent}% 完成")
            progress_bar['value'] = value
            root.update_idletasks()

        file_times = {}  # 用于存储每个文件的处理时间
        file_sizes = {}  # 用于存储每个文件的内容长度

        total_elapsed_time = 0  # 总处理时间
        total_content_length = 0  # 总内容长度

        with ThreadPoolExecutor(max_workers=1) as executor:  # 创建一个线程池，最大线程数为 1
            futures = {executor.submit(process_file, file, progress_bar, total_files): file for file in files}
            for future in as_completed(futures):
                try:
                    file, elapsed_time, content_length = future.result()
                    if elapsed_time is not None:
                        file_times[file] = elapsed_time
                        total_elapsed_time += elapsed_time
                    if content_length is not None:
                        file_sizes[file] = content_length
                        total_content_length += content_length
                    processed_count += 1
                    update_progress(processed_count)
                except Exception as e:
                    logging.error(f"处理文件时出错：{e}")

        # 输出每个文件的处理时间
        print("\n每个文件的处理时间：")
        for file, elapsed_time in file_times.items():
            print(f"{file}: {elapsed_time:.2f} 秒")

        # 输出每个文件的内容长度
        print("\n每个文件的内容长度：")
        for file, content_length in file_sizes.items():
            print(f"{file}: {content_length} 字节")

        # 输出总的文件处理时间和总的文件内容长度
        print(f"\n总的文件处理时间: {total_elapsed_time:.2f} 秒")
        print(f"总的文件内容长度: {total_content_length} 字节")

        messagebox.showinfo("完成", "文件处理已完成。")
        progress_bar.destroy()  # 关闭进度条
        progress_label.config(text="处理已完成")

# 创建主窗口
root = tk.Tk()
root.title("文件批量处理工具")

progress_label = tk.Label(root, text="0% 完成")
progress_label.pack(pady=5)

# 创建一个按钮，点击时调用 process_files 函数
process_button = tk.Button(root, text="选择文件夹并处理文件", command=process_files)
process_button.pack(pady=20)

# 启动主事件循环，使窗口保持显示并响应用户操作
root.mainloop()