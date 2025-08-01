import os
from pdf2image import convert_from_path
import pytesseract
from PyPDF2 import PdfReader


def pdf_to_text_with_ocr(pdf_path, output_path=None, lang='chi_sim+eng'):
    """
    使用 OCR 提取图片型 PDF 的文本

    参数:
        pdf_path (str): PDF 文件路径
        output_path (str, optional): 输出的 TXT 文件路径（默认：PDF 同目录同名.txt）
        lang (str): Tesseract 语言（默认：中文+英文）

    返回:
        str: 生成的 TXT 文件路径
    """
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"PDF 文件不存在: {pdf_path}")

    # 默认输出路径（同目录同名.txt）
    if output_path is None:
        output_path = os.path.splitext(pdf_path)[0] + ".txt"

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

    # 1. 尝试用 PyPDF2 提取文本（如果是可选中文本的 PDF）
    try:
        with open(pdf_path, 'rb') as f:
            reader = PdfReader(f)
            text = "\n".join(page.extract_text() for page in reader.pages)
            if text.strip():  # 如果有文本，直接保存
                with open(output_path, 'w', encoding='utf-8') as f_out:
                    f_out.write(text)
                return output_path
    except:
        pass  # 如果失败，继续用 OCR

    # 2. 如果是图片型 PDF，使用 OCR 提取
    images = convert_from_path(pdf_path)  # 将 PDF 转为图片
    text = ""

    for i, img in enumerate(images):
        text += pytesseract.image_to_string(img, lang=lang) + "\n"

    # 保存文本
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(text)

    return output_path

if __name__ == "__main__":
    txt_file = pdf_to_text_with_ocr('../downloaded_books/活着 (余华) (Z-Library).pdf')  # 自动生成input.txt