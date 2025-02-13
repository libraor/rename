# window.py
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QVBoxLayout, 
                            QRadioButton, QButtonGroup, QLabel, QProgressBar, 
                            QMessageBox, QFileDialog, QDialog)
from PyQt5.QtCore import Qt

class FileProcessorApp(QWidget):
    def __init__(self, processor):
        super().__init__()
        self.processor = processor  # 注入处理器对象
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
        self.processor.process_files_with_options(directory, process_option)

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
        return dialog, self.progress_bar  # 返回对话框和进度条

    def update_progress(self, processed_count, total_files):
        percent = int((processed_count / total_files) * 100)
        self.progress_label.setText(f"{percent}% 完成")
        self.progress_bar.setValue(processed_count)