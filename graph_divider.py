import os
import re


def sentence_tokenize(text):
    """使用正则表达式分句（确保句子完整性）"""
    # 匹配中英文句子结束标点（包括省略号、感叹号等）
    sentence_endings = r'(?<=[。！？.!?…])[\s\n]+'
    sentences = re.split(sentence_endings, text.strip())
    return [s for s in sentences if s.strip()]


def fixed_length_segment(sentences, target_length=3000):
    """将句子列表合并为接近目标长度的段落（不切断句子）"""
    segments = []
    current_segment = []
    current_length = 0

    for sent in sentences:
        sent_length = len(sent)  # 按字符数计算（或按实际token数）

        # 如果当前句子加入后会超出长度，且当前分段不为空
        if current_length + sent_length > target_length and current_segment:
            segments.append("".join(current_segment))
            current_segment = []
            current_length = 0

        current_segment.append(sent)
        current_length += sent_length

    # 添加最后一个分段
    if current_segment:
        segments.append("".join(current_segment))

    return segments


def save_segments(segments, output_dir):
    """保存分段到文件"""
    os.makedirs(output_dir, exist_ok=True)
    for i, seg in enumerate(segments, 1):
        with open(f"{output_dir}/segment_{i:04d}.txt", "w", encoding="utf-8") as f:
            f.write(seg)
    print(f"保存了 {len(segments)} 个分段到 {output_dir}")


if __name__ == "__main__":
    book_title = "霍乱时期的爱情 (加西亚·马尔克斯) (Z-Library)_preprocessed"
    # 示例使用
    target_length = 10000  # 目标长度（字符数）
    input_file = book_title + ".txt"
    output_dir = book_title + '_' + str(target_length)


    with open(input_file, "r", encoding="utf-8") as f:
        text = f.read()

    # 先分句
    sentences = sentence_tokenize(text)

    # 再合并为固定长度段落
    segments = fixed_length_segment(sentences, target_length)

    # 保存结果
    save_segments(segments, output_dir)