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
                        # 增加文本块的位置信息
                        bbox = span["bbox"]
                        layout_features.append((span["size"], span["font"], bbox))
    return layout_features

def calculate_image_similarity(img1, img2):
    # 使用SSIM计算相似度
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)
    similarity_ssim, _ = ssim(gray1, gray2, full=True)

    # 使用特征匹配计算相似度
    sift = cv2.SIFT_create()
    kp1, des1 = sift.detectAndCompute(gray1, None)
    kp2, des2 = sift.detectAndCompute(gray2, None)

    if des1 is None or des2 is None:
        logging.warning("SIFT 特征提取失败，返回默认相似度")
        return similarity_ssim

    if len(kp1) == 0 or len(kp2) == 0:
        logging.warning("关键点数量为零，返回默认相似度")
        return similarity_ssim

    bf = cv2.BFMatcher()
    matches = bf.knnMatch(des1, des2, k=2)
    good_matches = []
    for m, n in matches:
        if m.distance < 0.75 * n.distance:
            good_matches.append(m)
    
    similarity_feature = len(good_matches) / max(len(kp1), len(kp2))
    similarity = (similarity_ssim + similarity_feature) / 2
    return similarity

def split_pdf_by_layout(pdf_path, output_dir):
    try:
        doc = fitz.open(pdf_path)
        
        if doc.page_count == 1:
            # 如果PDF文件仅有一页，直接跳过分割，记录日志
            logging.info(f"PDF 文件 {pdf_path} 仅有一页，跳过分割")
            doc.close()
            return

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

            # 增加文本内容变化的判断
            prev_text = doc[page_num - 1].get_text()
            current_text = page.get_text()
            if prev_text.strip() and current_text.strip():
                text_similarity = len(set(prev_text.split()) & set(current_text.split())) / len(set(prev_text.split()) | set(current_text.split()))
            else:
                text_similarity = 0

            if abs(len(current_layout) - len(prev_layout)) > 10 or text_similarity < 0.8:
                layout_changes.append(page_num)

            if prev_image is not None:
                similarity = calculate_image_similarity(prev_image, img_array)
                if similarity < 0.9:
                    layout_changes.append(page_num)

            prev_layout = current_layout
            prev_image = img_array

        # 使用原始文件所在的目录作为输出目录
        output_dir = os.path.dirname(pdf_path)

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