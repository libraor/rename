# window.py

from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QVBoxLayout, 
                            QRadioButton, QButtonGroup, QLabel, QProgressBar, 
                            QMessageBox, QFileDialog, QDialog)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from utils import get_files  # 导入 get_files 函数
from pdf_processor import split_pdfs  # 导入 split_pdfs 函数

class Worker(QThread):
    # 定义一个信号，传递已处理文件数和总文件数
    progress = pyqtSignal(int, int)  
    # 定义一个信号，表示处理完成
    finished = pyqtSignal()  

    def __init__(self, processor, directory, process_option):
        """
        初始化Worker线程。

        :param processor: 处理器对象，用于执行文件处理逻辑
        :param directory: 需要处理的文件夹路径
        :param process_option: 处理选项（1: 仅识别不分割, 2: 仅分割不识别, 3: 分割和识别）
        """
        super().__init__()
        self.processor = processor
        self.directory = directory
        self.process_option = process_option

    def run(self):
        """
        线程运行时调用的方法。
        获取文件总数并启动文件处理过程，完成后发出完成信号。
        """
        total_files = self.processor.get_total_files(self.directory)
        self.processor.process_files_with_options(self.directory, self.process_option, self.progress_callback)
        self.finished.emit()  # 发出完成信号

    def progress_callback(self, processed, total):
        """
        进度回调函数，将进度信息转发给进度信号。

        :param processed: 已处理文件数
        :param total: 总文件数
        """
        self.progress.emit(processed, total)  # 将回调转发给进度信号

class FileProcessorApp(QWidget):
    def __init__(self, processor):
        """
        初始化主窗口。

        :param processor: 处理器对象，用于执行文件处理逻辑
        """
        super().__init__()
        self.processor = processor
        self.initUI()

    def initUI(self):
        """初始化用户界面"""
        self.setWindowTitle('文件批量处理工具')
        self.setGeometry(100, 100, 400, 300)
        layout = QVBoxLayout()
        self.process_button = QPushButton('选择文件夹并处理文件', self)
        self.process_button.clicked.connect(self.process_files)
        layout.addWidget(self.process_button)
        self.setLayout(layout)

    def process_files(self):
        """选择文件夹并启动文件处理流程"""
        directory = str(QFileDialog.getExistingDirectory(self, "选择文件夹"))
        if not directory:
            return
        self.show_option_dialog(directory)

    def show_option_dialog(self, directory):
        """
        显示选项对话框，让用户选择处理方式。

        :param directory: 需要处理的文件夹路径
        """
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
        """
        用户确认选项后启动文件处理。

        :param dialog: 选项对话框
        :param directory: 需要处理的文件夹路径
        """
        dialog.accept()
        process_option = self.process_option.checkedId()
        self.start_processing(directory, process_option)

    def start_processing(self, directory, process_option):
        """
        启动文件处理线程，并显示进度对话框。

        :param directory: 需要处理的文件夹路径
        :param process_option: 处理选项（1: 仅识别不分割, 2: 仅分割不识别, 3: 分割和识别）
        """
        # 先进行PDF分割
        if process_option == 2 or process_option == 3:
            pdf_files = get_files(directory, '.pdf')
            split_pdfs(pdf_files, directory)  # 直接调用 pdf_processor.py 中的 split_pdfs 函数

        # 重新计算总文件数
        total_files = self.processor.get_total_files(directory)
        self.progress_dialog, self.progress_bar = self.show_progress_dialog(total_files)

        self.worker = Worker(self.processor, directory, process_option)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_processing_finished)  # 添加完成信号连接
        self.worker.start()

    def show_progress_dialog(self, total_files):
        """
        显示进度对话框。

        :param total_files: 总文件数
        :return: 进度对话框和进度条对象
        """
        dialog = QDialog(self)
        dialog.setWindowTitle("进度")
        dialog.setGeometry(100, 100, 300, 150)

        self.progress_label = QLabel("0% 完成", dialog)
        self.progress_label.setAlignment(Qt.AlignCenter)

        self.progress_bar = QProgressBar(dialog)
        self.progress_bar.setRange(0, total_files)
        self.progress_bar.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout()
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)

        dialog.setLayout(layout)
        dialog.show()
        return dialog, self.progress_bar

    def update_progress(self, processed_count, total_files):
        """
        更新进度条和标签。

        :param processed_count: 已处理文件数
        :param total_files: 总文件数
        """
        percent = int((processed_count / total_files) * 100)
        self.progress_label.setText(f"{percent}% 完成")
        self.progress_bar.setValue(processed_count)

    def on_processing_finished(self):
        """处理完成后关闭进度对话框并显示完成消息"""
        self.progress_dialog.accept()
        QMessageBox.information(None, "完成", "文件处理已完成。")