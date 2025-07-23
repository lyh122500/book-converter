from nltk import sent_tokenize
import numpy as np


def semantic_split(text, max_tokens=3000):
    """基于语义的分割（无章节结构时使用）"""
    sentences = sent_tokenize(text)
    segments = []
    current_segment = []
    current_length = 0

    for sent in sentences:
        sent_tokens = len(sent.split())  # 简易token估算

        # 达到长度阈值或自然段落结束
        if current_length + sent_tokens > max_tokens or sent.endswith(('。', '！', '？')):
            if current_segment:
                segments.append(" ".join(current_segment))
                current_segment = []
                current_length = 0

        current_segment.append(sent)
        current_length += sent_tokens

    if current_segment:
        segments.append(" ".join(current_segment))

    return segments