import sys
import time
import os
import logging
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QRadioButton, QButtonGroup, QLabel, QProgressBar, QMessageBox, QFileDialog, QDialog
from PyQt5.QtCore import Qt
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

def update_progress(progress_label, progress_bar, processed_count, total_files):
    """
    更新进度条和标签
    """
    percent = int((processed_count / total_files) * 100)
    progress_label.setText(f"{percent}% 完成")
    progress_bar.setValue(processed_count)

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
    progress_bar = QProgressBar()
    progress_bar.setRange(0, total_files)
    progress_bar.setAlignment(Qt.AlignCenter)

    progress_label = QLabel("0% 完成")
    progress_label.setAlignment(Qt.AlignCenter)

    layout = QVBoxLayout()
    layout.addWidget(progress_label)
    layout.addWidget(progress_bar)

    dialog = QDialog()
    dialog.setWindowTitle("进度")
    dialog.setLayout(layout)
    dialog.show()

    file_times = {}
    file_sizes = {}
    total_elapsed_time = 0
    total_content_length = 0

    with ThreadPoolExecutor(max_workers=min(32, os.cpu_count())) as executor:
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
                update_progress(progress_label, progress_bar, len(file_times), total_files)
            except Exception as e:
                logging.error(f"处理文件时出错：{e}")

    print_stats(file_times, file_sizes, total_elapsed_time, total_content_length)
    QMessageBox.information(None, "完成", "文件处理已完成。")
    dialog.accept()

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

class FileProcessorApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('文件批量处理工具')
        self.setGeometry(100, 100, 400, 300)

        layout = QVBoxLayout()

        self.process_button = QPushButton('选择文件夹并处理文件', self)
        self.process_button.clicked.connect(self.process_files)
        layout.addWidget(self.process_button)

        self.setLayout(layout)

    def process_files(self):
        directory = str(QFileDialog.getExistingDirectory(self, "选择文件夹"))
        if not directory:
            return

        option_dialog = QDialog(self)
        option_dialog.setWindowTitle("选项")
        option_dialog.setGeometry(100, 100, 300, 150)

        layout = QVBoxLayout()

        self.process_option = QButtonGroup()

        only_recognize_radio = QRadioButton("仅进行识别不分割", option_dialog)
        self.process_option.addButton(only_recognize_radio, 1)
        layout.addWidget(only_recognize_radio)

        only_split_radio = QRadioButton("仅进行分割不识别", option_dialog)
        self.process_option.addButton(only_split_radio, 2)
        layout.addWidget(only_split_radio)

        both_radio = QRadioButton("进行分割和识别", option_dialog)
        self.process_option.addButton(both_radio, 3)
        both_radio.setChecked(True)
        layout.addWidget(both_radio)

        confirm_button = QPushButton("确认", option_dialog)
        confirm_button.clicked.connect(lambda: self.on_confirm(option_dialog, directory))
        layout.addWidget(confirm_button)

        option_dialog.setLayout(layout)
        option_dialog.exec_()

    def on_confirm(self, dialog, directory):
        dialog.accept()
        process_files_with_options(directory, self.process_option.checkedId())

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = FileProcessorApp()
    ex.show()
    sys.exit(app.exec_())