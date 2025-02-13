# main.py

import sys
import time
import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from PyQt5.QtWidgets import QApplication, QMessageBox
from openai import OpenAI
from window import FileProcessorApp
from pdf_processor import split_pdf_by_layout, split_pdfs  # 导入 split_pdfs 函数
import file_reader
from utils import get_files, sanitize_filename, print_stats  # 导入 get_files, sanitize_filename 和 print_stats 函数

# 设置PaddlePaddle的线程数
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'

# 从 pw.py 文件中导入配置信息
from pw import API_KEY, BASE_URL, MODEL_NAME

os.environ['LIBPNG_WARNING_LEVEL'] = '2'
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 更改 API 密钥和基础 URL 为火山接口的信息
client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

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

def process_single_file(file, callback, processed_count, total_files):
    """
    处理单个文件
    """
    try:
        start_time = time.time()
        content = file_reader.get_file_content(file)
        if content is None:
            logging.warning(f"读取文件 {file} 失败")
            if callback:
                callback(processed_count + 1, total_files)  # 调用回调函数
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
            if callback:
                callback(processed_count + 1, total_files)  # 调用回调函数
            return (new_file_path, elapsed_time, content_length)
        else:
            logging.warning(f"文件 {file} 处理失败，未获取到时间信息")
            if callback:
                callback(processed_count + 1, total_files)  # 调用回调函数
            return (file, None, content_length)
    except Exception as e:
        logging.error(f"处理文件 {file} 时出错：{e}", exc_info=True)
        QMessageBox.critical(None, "错误", f"处理文件 {file} 时出错：{e}")
        if callback:
            callback(processed_count + 1, total_files)  # 调用回调函数
        return (file, None, None)

class FileProcessor:
    def __init__(self, app):
        self.app = app  # 注入app实例

    def get_total_files(self, directory):
        """
        获取指定目录下的文件总数
        """
        return len(get_files(directory))

    def process_files_with_options(self, directory, process_option, callback=None):
        """
        处理多个文件，根据选项决定是否进行PDF分割以及是否进行文件内容的识别和重命名
        """
        if process_option == 1:  # 仅进行识别不分割
            files = get_files(directory)
        elif process_option == 2:  # 仅进行分割不识别
            pdf_files = get_files(directory, '.pdf')
            split_pdfs(pdf_files, directory)  # 调用 pdf_processor.py 中的 split_pdfs 函数
            QMessageBox.information(None, "完成", "仅进行了PDF分割。")
            return []
        elif process_option == 3:  # 进行分割和识别
            pdf_files = get_files(directory, '.pdf')
            split_pdfs(pdf_files, directory)  # 调用 pdf_processor.py 中的 split_pdfs 函数
            files = get_files(directory)

        if not files:
            return []

        total_files = len(files)  # 重新计算总文件数
        processed_files = self.process_files(files, total_files, callback)
        return processed_files

    def process_files(self, files, total_files, callback=None):
        """
        处理文件
        """
        file_times = {}
        file_sizes = {}
        total_elapsed_time = 0
        total_content_length = 0
        processed_files = []

        # 使用单线程执行器
        with ThreadPoolExecutor(max_workers=1) as executor:
            futures = {executor.submit(process_single_file, file, callback, i, total_files): file for i, file in enumerate(files)}
            for future in as_completed(futures):
                try:
                    processed_file = future.result()
                    processed_files.append(processed_file)
                    file, elapsed_time, content_length = processed_file
                    if elapsed_time is not None:
                        file_times[file] = elapsed_time
                        total_elapsed_time += elapsed_time
                    if content_length is not None:
                        file_sizes[file] = content_length
                        total_content_length += content_length
                except Exception as e:
                    logging.error(f"处理文件时出错：{e}", exc_info=True)
                    QMessageBox.critical(None, "错误", f"处理文件时出错：{e}")

        print_stats(file_times, file_sizes, total_elapsed_time, total_content_length)
        return processed_files

if __name__ == '__main__':
    app = QApplication(sys.argv)
    file_processor_app = FileProcessorApp(None)  # 创建FileProcessorApp实例
    processor = FileProcessor(file_processor_app)  # 将FileProcessorApp实例注入到processor中
    file_processor_app.processor = processor  # 将processor实例注入到FileProcessorApp中
    file_processor_app.show()
    sys.exit(app.exec_())