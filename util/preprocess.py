import re
import time
import unicodedata
import json
from pathlib import Path

import jieba
import os
from opencc import OpenCC

from config.global_config import Config
from util import graph_divider


def preprocess_text(text, book_title):
    """
    名著文本预处理流水线
    :param text: 原始文本字符串
    :param book_title: 书籍标题（用于特定处理）
    :return: 预处理后的文本
    """
    # 1. 编码标准化
    text = normalize_encoding(text)

    # 2. 基础清理
    text = basic_cleaning(text)

    # 3. 特殊格式处理
    text = handle_special_formats(text)

    # 4. 结构规范化
    text = normalize_structure(text, book_title)

    # 5. 语言特定处理（中文）
    text = chinese_specific_processing(text)

    # 6. 分词优化（可选）
    # if needs_tokenization(text):
    #     text = optimize_tokenization(text)

    return text


def normalize_encoding(text):
    """统一文本编码格式"""
    # 转换为NFKC规范化形式（兼容字符标准化）
    text = unicodedata.normalize('NFKC', text)

    # 移除BOM头
    if text.startswith('\ufeff'):
        text = text[1:]

    # 替换特殊空格
    text = text.replace('\u3000', ' ')  # 全角空格
    text = text.replace('\xa0', ' ')  # 不间断空格

    return text


def basic_cleaning(text):
    """基础文本清理"""
    # 移除非法字符（保留常见中文、英文、标点）
    text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s，。？；：‘’"！（）【】《》%、.?:;\'"!()\[\]<>%-]', '', text)

    # 标准化空白字符
    text = re.sub(r'\s+', ' ', text)  # 多个空白字符替换为单个空格
    text = re.sub(r'^\s+|\s+$', '', text)  # 移除首尾空白

    # 移除PDF转换常见的乱码
    text = re.sub(r'�+', '', text)

    return text


def handle_special_formats(text):
    """处理特殊文本格式"""
    # 处理注释（脚注、尾注）
    text = re.sub(r'\[注\d+\].*?(\[注\d+\]|$)', '', text)  # 移除注释内容

    # 处理对话引号（统一为中文引号）
    text = text.replace('"', '“').replace("'", "‘")

    # 处理数字格式（全角转半角）
    fullwidth_nums = '０１２３４５６７８９'
    halfwidth_nums = '0123456789'
    for fw, hw in zip(fullwidth_nums, halfwidth_nums):
        text = text.replace(fw, hw)

    return text


def normalize_structure(text, book_title):
    """规范化文本结构"""
    # 统一换行符
    text = text.replace('\r\n', '\n').replace('\r', '\n')

    # 移除页眉页脚（基于书名识别）
    header_footer_pattern = re.compile(
        r'^\s*({title})[\s\d-]*$|^\s*\d+\s*$'.format(title=re.escape(book_title)),
        re.MULTILINE
    )
    text = header_footer_pattern.sub('', text)

    # 合并短行
    lines = text.split('\n')
    processed_lines = []
    current_line = ''

    for line in lines:
        stripped = line.strip()
        # 跳过空行
        if not stripped:
            if current_line:
                processed_lines.append(current_line)
                current_line = ''
            processed_lines.append('')  # 保留空行分隔
            continue

        # 合并逻辑
        if len(stripped) < 30:  # 短行合并阈值
            current_line += stripped + ' '
        else:
            if current_line:
                processed_lines.append(current_line.strip())
            current_line = stripped + ' '

    if current_line:
        processed_lines.append(current_line.strip())

    return '\n'.join(processed_lines)


def chinese_specific_processing(text):
    """中文文本特殊处理"""
    # 繁体转简体
    cc = OpenCC('t2s')  # 繁体转简体
    text = cc.convert(text)

    # 统一异体字
    variant_mapping = {
        '裏': '里', '穀': '谷', '峯': '峰', '羣': '群',
        '爲': '为', '於': '于', '纔': '才', '牀': '床'
    }
    for variant, standard in variant_mapping.items():
        text = text.replace(variant, standard)

    # 处理古籍特有标点
    text = text.replace('「', '“').replace('」', '”')
    text = text.replace('『', '‘').replace('』', '’')

    # 移除多余空格（中文字符间）
    text = re.sub(r'([\u4e00-\u9fa5])\s+([\u4e00-\u9fa5])', r'\1\2', text)

    return text


def needs_tokenization(text):
    """检查是否需要分词"""
    # 如果中文比例超过80%，可能需要分词
    chinese_chars = re.findall(r'[\u4e00-\u9fa5]', text)
    return len(chinese_chars) / max(len(text), 1) > 0.8  # 避免除以零


def optimize_tokenization(text):
    """优化分词（用于后续处理）"""
    # 加载自定义词典（针对名著）
    jieba.load_userdict('classic_dict.txt')

    # 分词处理（保留原文结构）
    paragraphs = text.split('\n')
    processed_paragraphs = []

    for para in paragraphs:
        # 跳过空行
        if not para.strip():
            processed_paragraphs.append(para)
            continue

        # 分词并保留空格
        words = jieba.cut(para, cut_all=False)
        processed_paragraphs.append(' '.join(words))

    return '\n'.join(processed_paragraphs)


def process_single_file(session_id: str, target_length: int = 10000, redis_conn=None):
    """
    处理存储在Redis中的单个文件

    参数:
        session_id: 会话ID
        target_length: 目标分段长度
        redis_conn: Redis连接对象

    返回:
        {
            'book_title': str,
            'segment_count': int,
            'processed_text': str,
            'segments': List[str]
        }
    """
    # 从Redis获取文件数据
    file_data = redis_conn.get(f"session:{session_id}:file")
    if not file_data:
        raise ValueError("File not found in Redis storage")

    file_data = json.loads(file_data)
    content = file_data['content']
    filename = file_data.get('filename', 'unnamed_file')

    # 获取不带扩展名的文件名作为标题
    book_title = Path(filename).stem
    print(f"正在处理: {book_title}")

    # 预处理文本
    processed_text = preprocess_text(content, book_title)
    # 分句并分割为固定长度段落
    sentences = graph_divider.sentence_tokenize(processed_text)
    segments = graph_divider.fixed_length_segment(sentences, target_length)
    # 单独存储分段以便快速访问
    for i, seg in enumerate(segments):
        redis_conn.hset(f"session:{session_id}:segments", str(i), seg)
    redis_conn.expire(
        f"session:{session_id}:segments",
        Config.SESSION_EXPIRE
    )

    # 更新会话元数据
    redis_conn.hset(
        f"session:{session_id}:meta",
        mapping={
            'status': 'processed',
            'last_active': time.time()
        }
    )
    return f"完成处理: {book_title}, 生成 {len(segments)} 个分段"


def process_directory(directory_path, target_length=10000):
    """处理目录下的所有txt文件"""
    # 确保目录存在
    if not os.path.isdir(directory_path):
        print(f"错误: 目录 {directory_path} 不存在")
        return

    # 遍历目录下的所有文件
    for filename in os.listdir(directory_path):
        if filename.endswith(".txt"):
            file_path = os.path.join(directory_path, filename)
            try:
                process_single_file(file_path, target_length)
            except Exception as e:
                print(f"处理文件 {filename} 时出错: {str(e)}")
