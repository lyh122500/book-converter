import os
import json
import time
import random
from openai import OpenAI

# 初始化DeepSeek客户端
client = OpenAI(
    api_key="sk-d3c3323a507846189cb71d387be22988",  # 替换为你的DeepSeek API密钥
    base_url="https://api.deepseek.com/v1"  # DeepSeek API基础URL
)

# 书籍列表
books = [
    "安娜卡列尼娜", "傲慢与偏见", "百万英镑", "钢铁是怎样炼成的",
     "活着", "霍乱时期的爱情", "面纱", "挪威的森林",
    "漂泊的灵魂", "三体1", "三体2", "三体3",
    "杀死一只知更鸟", "素食者", "堂吉诃德", "围城", "我与地坛",
    "远大前程", "约翰克利斯朵夫"
]

# 配置选项
commentary_types = ["内容概要", "详细解说", "分析解读", "戏剧化呈现"]
language_styles = ["正式风格", "轻松风格", "幽默风格", "文学风格"]
target_audiences = ["儿童", "青少年", "成年人", "学术研究"]

# 书籍信息文件夹
PROMPT_DIR = "book_prompts"


def read_book_prompt(book_name):
    """读取书籍的prompt文件内容"""
    filename = f"prompt_{book_name}.txt"
    filepath = os.path.join(PROMPT_DIR, filename)

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"警告: 未找到{book_name}的prompt文件: {filepath}")
        return f"《{book_name}》是一部经典文学作品，请根据您的知识为其创作解说词。"


def generate_commentary_prompt(config: dict, book_info: str) -> str:
    """
    根据配置和书籍信息生成名著解说词的要求

    参数:
        config (dict): 配置字典
        book_info (str): 从文件读取的书籍信息

    返回:
        str: 结构化的prompt
    """
    # 默认值设置
    commentary_type = config.get("解说词类型", "详细解说")
    language_style = config.get("语言风格", "轻松风格")
    target_audience = config.get("目标受众", "成年人")
    extra_prompt = config.get("ex_prompt", "")

    # 开头结尾算子库
    OPENINGS = [
        "总结式开头：用一句话概括全书核心",
        "评价式开头：直接点明本书的文学地位",
        "高潮开头：从最具冲突性的情节切入",
        "个人感受开头：以读者视角分享初读体验",
        "作者介绍开头：从作者生平以及创作背景切入主题"
    ]

    ENDINGS = [
        "总结式结尾：呼应开头的核心观点",
        "升华式结尾：延伸现实启示",
        "悬念式结尾：提出开放性思考",
        "金句式结尾：引用书中原句收尾",
        "情感式结尾：引发情感共鸣"
    ]

    # 随机选择开头结尾（各选2个组合）
    selected_openings = random.sample(OPENINGS, 2)
    selected_endings = random.sample(ENDINGS, 2)

    # 构建结构化prompt
    prompt_parts = [
        f"请为书籍《{config['book']}》创作一个抖音视频解说词，要求：",
        f"书籍信息：{book_info}",
        f"1. 解说类型：{commentary_type} → {_get_commentary_desc(commentary_type)}",
        f"2. 语言风格：{language_style} → {_get_style_desc(language_style)}",
        f"3. 目标读者：{target_audience} → {_get_audience_desc(target_audience)}",
        "4. 结构要求：",
        f"- 开头组合：{selected_openings[0]} + {selected_openings[1]}",
        f"- 结尾组合：{selected_endings[0]} + {selected_endings[1]}",
        "5. 内容要求：",
        "- 必须包含完整的书籍剧情解说",
        "- 情感引导：触发读者情感共鸣",
        "- 文化映射：关联社会文化背景",
        "- 内容丰富详实，不少于3000字",
        "- 适合短视频平台传播，有吸引人的开头和结尾",
        "- 结合现代视角给出独到见解"
    ]

    # 动态适配要求
    if target_audience == "学术研究":
        prompt_parts.append("- 学术要求：包含理论框架和文献引用")
    elif target_audience == "儿童":
        prompt_parts.append("- 适配要求：使用比喻和拟人化表达")
    elif target_audience == "青少年":
        prompt_parts.append("- 适配要求：联系青春期成长主题")

    if "戏剧化呈现" in commentary_type:
        prompt_parts.append("- 特别要求：添加角色对话和场景描写")

    if extra_prompt:
        prompt_parts.append(f"6. 额外要求：{extra_prompt}")

    return "\n".join(prompt_parts)


# 辅助函数：获取UI选项描述
def _get_audience_desc(audience: str) -> str:
    desc_map = {
        "儿童": "适合6-12岁儿童理解",
        "青少年": "适合13-18岁青少年理解",
        "成年人": "适合成年人理解",
        "学术研究": "适合学术研究和深入分析"
    }
    return desc_map.get(audience, "")


def _get_style_desc(style: str) -> str:
    desc_map = {
        "正式风格": "使用正式、学术化的语言",
        "轻松风格": "使用轻松、易懂的语言",
        "幽默风格": "加入幽默元素，轻松有趣",
        "文学风格": "使用富有文学性的语言"
    }
    return desc_map.get(style, "")


def _get_commentary_desc(c_type: str) -> str:
    desc_map = {
        "内容概要": "简要概述书籍主要内容",
        "详细解说": "详细解说书籍内容和情节",
        "分析解读": "深入分析书籍主题和文学价值",
        "戏剧化呈现": "以戏剧化方式呈现关键情节"
    }
    return desc_map.get(c_type, "")


def generate_script(config, book_info):
    """生成书籍解说词"""

    prompt = generate_commentary_prompt(config, book_info)

    try:
        response = client.chat.completions.create(
            model="deepseek-reasoner",  # 使用DeepSeek的模型
            messages=[
                {"role": "system",
                 "content": "你是一位专业的文学评论家和短视频内容创作者，擅长创作生动有趣的书籍解说内容。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8  # 控制创造性
        )

        return prompt, response.choices[0].message.content.strip()
    except Exception as e:
        print(f"生成{config['book']}的解说词时出错: {e}")
        return None, None


def main():
    # 创建输出目录
    os.makedirs("fine_tuning_data", exist_ok=True)

    # 检查书籍信息目录是否存在
    if not os.path.exists(PROMPT_DIR):
        print(f"错误: 未找到书籍信息目录 '{PROMPT_DIR}'")
        print("请创建该目录并添加每本书的prompt文件，格式为: prompt_书名.txt")
        return

    # 生成200个不同配置的问答对
    data_count = 0
    all_data = []  # 存储所有问答对

    while data_count < 1:
        # 随机选择一本书
        book = random.choice(books)

        # 读取书籍信息
        book_info = read_book_prompt(book)

        # 随机生成配置
        config = {
            "book": book,
            "解说词类型": random.choice(commentary_types),
            "语言风格": random.choice(language_styles),
            "目标受众": random.choice(target_audiences),
            "ex_prompt": "必须包含完整的书籍剧情解说，根据作品内容摘要以及解说要求返回解说词\n"
            "解说词字数不少于一万字\n"
            "注意只输出解说词内容即可，不要任何额外输出\n"
        }

        print(
            f"正在为《{book}》生成{config['解说词类型']}类型的解说词，风格为{config['语言风格']}，面向{config['目标受众']}...")

        # 生成问答对
        prompt, script = generate_script(config, book_info)
        if script is None:
            continue

        # 创建问答对数据（用于大模型微调）
        qa_pair = {
            "instruction": "你是一位专业的文学评论家和短视频内容创作者，擅长创作生动有趣的书籍解说内容。",
            "input": prompt,
            "output": script,
            "config": config,
            "book_info": book_info
        }

        # 添加到总数据列表
        all_data.append(qa_pair)

        # 同时保存为单独的文件
        filename = f"fine_tuning_data/{book}_{config['解说词类型']}_{config['语言风格']}_{config['目标受众']}_{data_count}.json"
        filename = filename.replace(" ", "_").replace("-", "_")

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(qa_pair, f, ensure_ascii=False, indent=2)

        print(f"已保存: {filename}")
        data_count += 1

        # 添加延迟避免API限制
        time.sleep(2)

    # 保存所有数据到一个文件中（便于批量处理）
    combined_filename = f"fine_tuning_data/all_qa_pairs_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(combined_filename, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    print(f"完成! 共生成{data_count}个问答对文件。")
    print(f"所有数据已保存到: {combined_filename}")


if __name__ == "__main__":
    main()