from util import graph_divider
from util.preprocess import preprocess_text

book_title = '活着'
target_length = 10000
try:
    with open('./活着 (余华) (Z-Library).txt', 'r', encoding='utf-8') as file:
        content = file.read()

        # 预处理文本
        processed_text = preprocess_text(content, book_title)

        # 分句并分割为固定长度段落
        sentences = graph_divider.sentence_tokenize(processed_text)
        print("分句结果:", sentences)

        segments = graph_divider.fixed_length_segment(sentences, target_length)
        print("\n分段结果:", len(segments))

        segment_data = {str(i): seg for i, seg in enumerate(segments)}
        print(len(segment_data))

except FileNotFoundError:
    print(f"错误: 文件不存在")