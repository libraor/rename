# pdf_processor.py

import os
import fitz  # PyMuPDF
import logging
import cv2
from skimage.metrics import structural_similarity as ssim
from PIL import Image
import numpy as np

def analyze_layout(page):
    layout_features = []
    text_dict = page.get_text("dict")
    if "blocks" in text_dict:
        for block in text_dict["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        layout_features.append((span["size"], span["font"]))
    return layout_features

def calculate_image_similarity(img1, img2):
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    similarity, _ = ssim(gray1, gray2, full=True)
    return similarity

def split_pdf_by_layout(pdf_path, output_dir):
    try:
        doc = fitz.open(pdf_path)
        layout_changes = []
        prev_layout = None
        prev_image = None

        for page_num in range(doc.page_count):
            page = doc[page_num]
            current_layout = analyze_layout(page)
            pix = page.get_pixmap()
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img_array = np.array(img)

            if prev_layout is None:
                prev_layout = current_layout
                prev_image = img_array
                continue

            if abs(len(current_layout) - len(prev_layout)) > 10:
                layout_changes.append(page_num)

            if prev_image is not None:
                similarity = calculate_image_similarity(prev_image, img_array)
                if similarity < 0.9:
                    layout_changes.append(page_num)

            prev_layout = current_layout
            prev_image = img_array

        current_file_pages = []
        file_index = 0
        for i in range(doc.page_count):
            current_file_pages.append(i)
            if i in layout_changes or i == doc.page_count - 1:
                new_doc = fitz.open()
                for num in current_file_pages:
                    new_doc.insert_pdf(doc, from_page=num, to_page=num)
                output_path = os.path.join(output_dir, f'split_{file_index}.pdf')
                new_doc.save(output_path)
                logging.info(f"分割后的 PDF 文件已保存到 {output_path}")
                file_index += 1
                current_file_pages = []

        doc.close()

        try:
            os.remove(pdf_path)
            logging.info(f"原始 PDF 文件 {pdf_path} 已删除")
        except Exception as e:
            logging.error(f"删除原始 PDF 文件 {pdf_path} 时出错：{e}")
    except Exception as e:
        logging.error(f"分割 PDF 文件 {pdf_path} 时出错：{e}")