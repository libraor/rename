# main.py
import time
import os
import tkinter as tk
from tkinter import filedialog, messagebox, Radiobutton, Toplevel
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
            model=MODEL_NAME,
            messages=[{
                "role": "user",
                "content": f"假设你是文件重命名助手，分析文件生成时间与主要内容，以 “yyyymmdd_标题” 格式返回。若无法识别时间，以 “00000000_标题” 格式输出，标题简洁，不超 20 字。不需要任何解释。不需要解析过程。{text}"
            }]
        )
        logging.info("成功调用火山接口 API")
        return response.choices[0].message.content.strip()
    except Exception as e:
        error_message = f"调用火山接口 API 时出错：{e}"
        logging.error(error_message, exc_info=True)
        messagebox.showerror("错误", error_message)
        return None

def get_files(directory, ext=None):
    """
    返回指定目录下的所有文件路径列表，可选地根据扩展名过滤
    """
    if not directory:
        return []

    file_list = []
    for root, _, files in os.walk(directory):
        for file in files:
            if ext is None or file.lower().endswith(ext):
                file_list.append(os.path.join(root, file))
    return file_list

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
        start_time = time.time()
        content = file_reader.get_file_content(file)
        if content is None:
            logging.warning(f"读取文件 {file} 失败")
            return (file, None, None)

        content_length = len(content)
        time_info = extract_time_openai(content)
        if time_info:
            file_dir = os.path.dirname(file)
            file_ext = os.path.splitext(file)[1]
            new_file_name = sanitize_filename(f"{time_info}{file_ext}")
            new_file_path = os.path.join(file_dir, new_file_name)
            os.rename(file, new_file_path)
            elapsed_time = time.time() - start_time
            logging.info(f"文件 {file} 已重命名为 {new_file_path}")
            return (file, elapsed_time, content_length)
        else:
            logging.warning(f"文件 {file} 处理失败，未获取到时间信息")
            return (file, None, content_length)
    except Exception as e:
        logging.error(f"处理文件 {file} 时出错：{e}", exc_info=True)
        messagebox.showerror("错误", f"处理文件 {file} 时出错：{e}")
        return (file, None, None)

def update_progress(progress_label, progress_bar, processed_count, total_files):
    """
    更新进度条和标签
    """
    percent = int((processed_count / total_files) * 100)
    progress_label.config(text=f"{percent}% 完成")
    progress_bar['value'] = processed_count
    progress_bar.after(100, lambda: None)  # 异步更新进度条
    progress_bar.update_idletasks()

def process_files_with_options(directory, process_option):
    """
    处理多个文件，根据选项决定是否进行PDF分割以及是否进行文件内容的识别和重命名
    """
    if process_option == 1:  # 仅进行识别不分割
        files = get_files(directory)
    elif process_option == 2:  # 仅进行分割不识别
        files = get_files(directory, '.pdf')
        for pdf_file in files:
            logging.info(f"开始分割 PDF 文件: {pdf_file}")
            split_pdf_by_layout(pdf_file, directory)
            logging.info(f"完成分割 PDF 文件: {pdf_file}")
        messagebox.showinfo("完成", "仅进行了PDF分割。")
        return
    elif process_option == 3:  # 进行分割和识别
        pdf_files = get_files(directory, '.pdf')
        for pdf_file in pdf_files:
            logging.info(f"开始分割 PDF 文件: {pdf_file}")
            split_pdf_by_layout(pdf_file, directory)
            logging.info(f"完成分割 PDF 文件: {pdf_file}")
        files = get_files(directory)

    if not files:
        return

    total_files = len(files)
    progress_bar = Progressbar(root, orient='horizontal', length=300, mode='determinate')
    progress_bar.pack(pady=10)
    progress_bar['maximum'] = total_files
    progress_label = tk.Label(root, text="0% 完成")
    progress_label.pack(pady=5)

    file_times = {}
    file_sizes = {}
    total_elapsed_time = 0
    total_content_length = 0

    with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
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
                update_progress(progress_label, progress_bar, len(file_times), total_files)
            except Exception as e:
                logging.error(f"处理文件时出错：{e}")

    print_stats(file_times, file_sizes, total_elapsed_time, total_content_length)
    messagebox.showinfo("完成", "文件处理已完成。")
    progress_bar.destroy()
    progress_label.config(text="处理已完成")

def print_stats(file_times, file_sizes, total_elapsed_time, total_content_length):
    """
    打印统计信息
    """
    print("\n每个文件的处理时间：")
    for file, elapsed_time in file_times.items():
        print(f"{file}: {elapsed_time:.2f} 秒")

    print("\n每个文件的内容长度：")
    for file, content_length in file_sizes.items():
        print(f"{file}: {content_length} 字节")

    print(f"\n总的文件处理时间: {total_elapsed_time:.2f} 秒")
    print(f"总的文件内容长度: {total_content_length} 字节")

def process_files():
    """
    处理多个文件
    """
    directory = filedialog.askdirectory()
    if not directory:
        return

    option_window = Toplevel(root)
    option_window.title("选项")
    option_window.geometry("300x150")

    process_option = tk.IntVar(value=3)

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

# 创建主窗口
root = tk.Tk()
root.title("文件批量处理工具")

process_button = tk.Button(root, text="选择文件夹并处理文件", command=process_files)
process_button.pack(pady=20)

root.mainloop()