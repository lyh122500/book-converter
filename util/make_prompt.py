import random


def generate_commentary_prompt(config: dict) -> str:
    """
    根据配置生成名著解说词的要求（集成UI选项）

    新增算子功能:
    1. 随机开头结尾组合
    2. 动态风格适配

    参数:
        config (dict): 配置字典，包含:
            ▪ "解说词类型": ["内容概要", "详细解说", "分析解读", "戏剧化呈现"]  # 按图3更新
            ▪ "语言风格": ["正式风格", "轻松风格", "幽默风格", "文学风格"]  # 按图2更新
            ▪ "目标受众": ["儿童", "青少年", "成年人", "学术研究"]  # 按图1更新
            ▪ "ex_prompt": str (额外要求)

    返回:
        str: 结构化的prompt
    """
    # 默认值设置（更新为图片选项）
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
        "📚 请根据以下要求生成文学解说词：",
        f"1. 解说类型：{commentary_type} → {_get_commentary_desc(commentary_type)}",
        f"2. 语言风格：{language_style} → {_get_style_desc(language_style)}",
        f"3. 目标读者：{target_audience} → {_get_audience_desc(target_audience)}",
        "4. 结构要求：",
        f"- 开头组合：{selected_openings[0]} + {selected_openings[1]}",
        f"- 结尾组合：{selected_endings[0]} + {selected_endings[1]}",
        "5. 内容要求：",
        "- 情感引导：触发读者情感共鸣",
        "- 文化映射：关联社会文化背景"
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


# 辅助函数：获取UI选项描述（直接引用图片文字）
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