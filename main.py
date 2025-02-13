# main.py
import sys
import time
import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from PyQt5.QtWidgets import QApplication, QMessageBox
from openai import OpenAI
from window import FileProcessorApp
from pdf_processor import split_pdf_by_layout  # 引入PDF遍历和分割模块
import file_reader  # 引入文件读取模块

# 设置PaddlePaddle的线程数
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

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
        QMessageBox.critical(None, "错误", error_message)
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

def process_single_file(file, progress_bar, total_files):
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
        QMessageBox.critical(None, "错误", f"处理文件 {file} 时出错：{e}")
        return (file, None, None)

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

class FileProcessor:
    def __init__(self, app):
        self.app = app  # 注入app实例

    def process_files_with_options(self, directory, process_option):
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
            QMessageBox.information(None, "完成", "仅进行了PDF分割。")
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
        progress_dialog, progress_bar = self.app.show_progress_dialog(total_files)  # 获取对话框和进度条

        file_times = {}
        file_sizes = {}
        total_elapsed_time = 0
        total_content_length = 0

        # 使用单线程执行器
        with ThreadPoolExecutor(max_workers=1) as executor:
            futures = {executor.submit(process_single_file, file, progress_bar, total_files): file for file in files}
            for future in as_completed(futures):
                try:
                    file, elapsed_time, content_length = future.result()
                    if elapsed_time is not None:
                        file_times[file] = elapsed_time
                        total_elapsed_time += elapsed_time
                    if content_length is not None:
                        file_sizes[file] = content_length
                        total_content_length += content_length
                    self.app.update_progress(len(file_times), total_files)
                except Exception as e:
                    logging.error(f"处理文件时出错：{e}")

        print_stats(file_times, file_sizes, total_elapsed_time, total_content_length)
        QMessageBox.information(None, "完成", "文件处理已完成。")
        progress_dialog.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    file_processor_app = FileProcessorApp(None)  # 创建FileProcessorApp实例
    processor = FileProcessor(file_processor_app)  # 将FileProcessorApp实例注入到processor中
    file_processor_app.processor = processor  # 将processor实例注入到FileProcessorApp中
    file_processor_app.show()
    sys.exit(app.exec_())