def generate_commentary_prompt(config: dict) -> str:
    """
    根据配置生成名著解说词的prompt

    参数:
        config (dict): 配置字典，包含以下键:
            - "解说词类型": 如"剧情解说"、"人物分析"等
            - "语言风格": 如"幽默风趣"、"严谨学术"等
            - "目标受众": 如"小学生"、"大学生"等
            - "ex_prompt": 额外的自定义要求

    返回:
        str: 拼接好的完整prompt
    """

    # 解析配置项
    commentary_type = config.get("解说词类型", "")
    language_style = config.get("语言风格", "")
    target_audience = config.get("目标受众", "")
    extra_prompt = config.get("ex_prompt", "")

    # 构建详细要求
    requirements = []

    if commentary_type:
        requirements.append(f"解说词类型：{commentary_type}")

    if language_style:
        requirements.append(f"语言风格：{language_style}")

    if target_audience:
        requirements.append(f"目标受众：{target_audience}")

    if extra_prompt:
        requirements.append(f"额外要求：{extra_prompt}")


    # 拼接完整prompt
    full_prompt = "\n\n具体要求：\n"
    full_prompt += "\n".join(f"- {req}" for req in requirements)


    return full_prompt