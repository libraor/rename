# utils.py

import os

def get_files(directory, extension=None):
    """
    获取指定目录下的文件列表，可选指定文件扩展名。

    :param directory: 目录路径
    :param extension: 文件扩展名（可选）
    :return: 文件列表
    """
    files = []
    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            if extension is None or filename.endswith(extension):
                files.append(os.path.join(root, filename))
    return files

def sanitize_filename(filename):
    """
    过滤掉文件名中的非法字符。

    :param filename: 原始文件名
    :return: 过滤后的文件名
    """
    return "".join(x for x in filename if x.isalnum() or x in "._- ")

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