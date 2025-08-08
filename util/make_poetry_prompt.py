import random
from config.global_config import Config


def generate_poetry_commentary_prompt(config: dict) -> str:
    """
    根据配置生成诗词解说词的要求

    参数:
        config (dict): 配置字典，包含:
            ▪ "解说类型": ["意境赏析", "逐句解析", "创作背景", "情感解读"]
            ▪ "语言风格": ["古典雅致", "通俗易懂", "诗意盎然", "学术严谨"]
            ▪ "目标受众": ["初学者", "诗词爱好者", "专业研究者", "学生"]
            ▪ "ex_prompt": str (额外要求)

    返回:
        str: 结构化的prompt
    """
    # 默认值设置
    commentary_type = config.get("解说类型", "意境赏析")
    language_style = config.get("语言风格", "诗意盎然")
    target_audience = config.get("目标受众", "诗词爱好者")
    extra_prompt = config.get("ex_prompt", "")

    # 诗词特有算子库
    OPENINGS = [
        "意象切入：从诗歌中最突出的意象开始解说",
        "情感共鸣：以现代人可能产生的情感共鸣开头",
        "名句引入：直接引用诗中最著名的诗句",
        "历史背景：从创作时的历史背景切入",
        "对比开头：与同类题材诗歌对比引入"
    ]

    ENDINGS = [
        "意境升华：将诗歌意境升华到人生哲理",
        "时代价值：探讨诗歌的现代意义",
        "创作技巧：总结诗歌的艺术特色",
        "情感共鸣：以情感共鸣收尾",
        "名句回味：以诗中名句作结引发思考"
    ]

    ANALYSIS_METHODS = [
        "意象分析法：重点分析诗歌中的意象组合",
        "情感脉络法：梳理诗歌情感发展变化",
        "字词推敲法：赏析关键字的精妙之处",
        "结构分析法：分析诗歌的起承转合",
        "比较文学法：与同类题材诗歌比较"
    ]

    # 随机选择算子组合
    selected_opening = random.choice(OPENINGS)
    selected_ending = random.choice(ENDINGS)
    selected_methods = random.sample(ANALYSIS_METHODS, 2)

    # 构建结构化prompt
    prompt_parts = [
        "🌸 请根据以下要求生成诗词解说词：",
        f"1. 解说类型：{commentary_type} → {_get_poetry_commentary_desc(commentary_type)}",
        f"2. 语言风格：{language_style} → {_get_poetry_style_desc(language_style)}",
        f"3. 目标读者：{target_audience} → {_get_poetry_audience_desc(target_audience)}",
        "4. 结构要求：",
        f"- 开头方式：{selected_opening}",
        f"- 分析方法：{selected_methods[0]} + {selected_methods[1]}",
        f"- 结尾方式：{selected_ending}",
        "5. 核心要素：",
        "- 意境描绘：生动还原诗歌意境",
        "- 情感把握：准确捕捉诗人情感",
        "- 语言赏析：点评诗歌语言艺术"
    ]

    # 动态适配要求
    if target_audience == "专业研究者":
        prompt_parts.append("- 学术要求：包含版本考据和学术观点引用")
    elif target_audience == "学生":
        prompt_parts.append("- 教学要求：包含知识点解析和思考题")

    if "逐句解析" in commentary_type:
        prompt_parts.append("- 特别要求：对每一句进行独立分析")

    if "创作背景" in commentary_type:
        prompt_parts.append("- 特别要求：详细考证创作背景和诗人境遇")

    if extra_prompt:
        prompt_parts.append(f"6. 额外要求：{extra_prompt}")

    return "\n".join(prompt_parts)


# 辅助函数：获取诗词解说选项描述
def _get_poetry_audience_desc(audience: str) -> str:
    desc_map = {
        "初学者": "适合初次接触诗词的读者",
        "诗词爱好者": "适合有一定诗词积累的爱好者",
        "专业研究者": "适合学术研究和深度分析",
        "学生": "适合中小学语文学习需求"
    }
    return desc_map.get(audience, "")


def _get_poetry_style_desc(style: str) -> str:
    desc_map = {
        "古典雅致": "使用文言词汇和传统评点方式",
        "通俗易懂": "使用白话文通俗化讲解",
        "诗意盎然": "语言充满诗意，与原文风格呼应",
        "学术严谨": "使用学术语言和规范引用"
    }
    return desc_map.get(style, "")


def _get_poetry_commentary_desc(c_type: str) -> str:
    desc_map = {
        "意境赏析": "重点赏析诗歌营造的意境",
        "逐句解析": "对诗歌每一句进行详细解析",
        "创作背景": "结合创作背景解读诗歌",
        "情感解读": "深入分析诗歌表达的情感"
    }
    return desc_map.get(c_type, "")


async def generate_poetry_commentary(poetry: str, trans_poetry: str, author_info: dict, config: dict) -> str:
    """
    生成诗词解说词

    参数:
        poetry: 原诗文本
        trans_poetry: 翻译后的现代文
        author_info: 作者信息字典
        config: 解说配置

    返回:
        str: 生成的解说词
    """
    # 生成prompt
    prompt = generate_poetry_commentary_prompt(config)

    # 构建完整提示
    full_prompt = (
        f"请为以下诗词创作解说词：\n\n"
        f"=== 原诗 ===\n{poetry}\n\n"
        f"=== 现代译文 ===\n{trans_poetry}\n\n"
        f"=== 作者信息 ===\n"
        f"姓名：{author_info.get('作者姓名', '未知')}\n"
        f"朝代：{author_info.get('朝代', '未知')}\n"
        f"生平：{author_info.get('作者背景', '暂无信息')}\n"
        f"创作背景：{author_info.get('创作背景', '暂无信息')}\n\n"
        f"=== 解说要求 ===\n{prompt}\n\n"
        "注意事项：\n"
        "1. 保持各段长度均衡，适合制作视频\n"
        "2. 避免使用过于专业的术语（面向大众）\n"
        "3. 适当引用诗句作为例证"
    )

    # 调用API生成解说词
    response = await Config.dsclient.chat.completions.create(
        model="deepseek-reasoner",
        messages=[
            {"role": "system", "content": "你是一位专业的诗词评论家"},
            {"role": "user", "content": full_prompt}
        ],
        temperature=0.7,
        max_tokens=20000
    )

    return response.choices[0].message.content.strip()