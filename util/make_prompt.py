def generate_commentary_prompt(config: dict) -> str:
    """
    根据配置生成名著解说词的prompt

    参数:
        config (dict): 配置字典，包含:
            - "解说词类型": ["剧情解说", "人物分析", "主题解析", "写作手法", "历史背景"]
            - "语言风格": ["幽默风趣", "严谨学术", "通俗易懂", "诗意优美"]
            - "目标受众": ["小学生", "中学生", "大学生", "普通读者", "专业研究者"]
            - "ex_prompt": str (额外要求)

    返回:
        str: 结构化的prompt
    """
    # 默认值设置
    commentary_type = config.get("解说词类型", "综合分析")
    language_style = config.get("语言风格", "通俗易懂")
    target_audience = config.get("目标受众", "普通读者")
    extra_prompt = config.get("ex_prompt", "")

    # 构建结构化prompt
    prompt_parts = [
        "请根据以下要求生成文学解说词：",
        f"1. 解说类型：{commentary_type}",
        f"2. 语言风格：{language_style}",
        f"3. 目标读者：{target_audience}",
        "4. 内容要求：",
        "- 准确反映原著内容",
        "- 突出作品的核心价值",
        "- 结构清晰，层次分明"
    ]

    if extra_prompt:
        prompt_parts.append(f"5. 额外要求：{extra_prompt}")

    # 添加专业要求
    if target_audience == "专业研究者":
        prompt_parts.append("- 请包含学术引用和理论分析")
    elif target_audience == "小学生":
        prompt_parts.append("- 使用简单词汇和生动例子")

    return "\n".join(prompt_parts)