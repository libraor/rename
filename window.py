# window.py
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QVBoxLayout, 
                            QRadioButton, QButtonGroup, QLabel, QProgressBar, 
                            QMessageBox, QFileDialog, QDialog)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

class Worker(QThread):
    progress = pyqtSignal(int, int)  # 定义一个信号，传递已处理文件数和总文件数
    finished = pyqtSignal()  # 定义一个信号，表示处理完成

    def __init__(self, processor, directory, process_option):
        super().__init__()
        self.processor = processor
        self.directory = directory
        self.process_option = process_option

    def run(self):
        total_files = self.processor.get_total_files(self.directory)
        processed_files = self.processor.process_files_with_options(self.directory, self.process_option)
        total_files = len(processed_files)  # 重新计算总文件数
        for i, file in enumerate(processed_files):
            self.progress.emit(i + 1, total_files)  # 发出信号
        self.finished.emit()  # 发出完成信号

class FileProcessorApp(QWidget):
    def __init__(self, processor):
        super().__init__()
        self.processor = processor
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
        self.show_option_dialog(directory)

    def show_option_dialog(self, directory):
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
        process_option = self.process_option.checkedId()
        self.start_processing(directory, process_option)

    def start_processing(self, directory, process_option):
        total_files = self.processor.get_total_files(directory)
        self.progress_dialog, self.progress_bar = self.show_progress_dialog(total_files)

        self.worker = Worker(self.processor, directory, process_option)
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_processing_finished)  # 添加完成信号连接
        self.worker.start()

    def show_progress_dialog(self, total_files):
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
        percent = int((processed_count / total_files) * 100)
        self.progress_label.setText(f"{percent}% 完成")
        self.progress_bar.setValue(processed_count)

    def on_processing_finished(self):
        self.progress_dialog.accept()
        QMessageBox.information(None, "完成", "文件处理已完成。") 