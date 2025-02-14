# utils.py
import os

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