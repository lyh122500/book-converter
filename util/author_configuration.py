from distutils.command.config import config

from config.global_config import Config
import json

# 配置DeepSeek API


async def get_author_info(book_title: str) -> dict:
    """
    根据书名获取作者信息的函数

    参数:
        book_title (str): 要查询的书名

    返回:
        dict: 包含作者信息的字典，格式为:
        {
            "作者姓名": str,
            "生卒年份": str,
            "国籍": str,
            "代表作": list,
            "作者背景": str,
            "创作背景": str
        }
    """
    try:
        # 构造提示词，包含明确的JSON格式示例
        prompt = f"""
        请提供关于《{book_title}》这本书的详细作者信息，并严格按照以下JSON格式返回数据：

        {{
            "作者姓名": "作者全名",
            "生卒年份": "约1715年—约1763年",
            "国籍": "作者国籍",
            "代表作": ["作品1", "作品2", "作品3"],
            "作者背景": "100字左右的作者生平背景介绍",
            "创作背景": "100字左右的本书创作背景介绍"
        }}

        要求：
        1. 生卒年份尽可能准确，不确定可加"约"字
        2. 代表作列出3-5部最知名的作品
        3. 作者背景应包括时代背景和重要经历
        4. 创作背景应说明创作时期和动机
        5. 只返回JSON格式数据，不要额外解释
        """

        # 调用API
        response = await Config.dsclient.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )

        # 解析响应
        result = json.loads(response.choices[0].message.content)

        # 验证响应结构
        required_fields = ["作者姓名", "生卒年份", "国籍", "代表作", "作者背景", "创作背景"]
        for field in required_fields:
            if field not in result:
                raise ValueError(f"响应中缺少必要字段: {field}")

        # 验证代表作是否为列表
        if not isinstance(result["代表作"], list):
            raise ValueError("代表作字段应该是列表形式")

        return result

    except Exception as e:
        return {
            "error": str(e),
            "作者姓名": "",
            "生卒年份": "",
            "国籍": "",
            "代表作": [],
            "作者背景": "",
            "创作背景": ""
        }

# 使用示例
# import asyncio
# result = asyncio.run(get_author_info("红楼梦"))
# print(json.dumps(result, ensure_ascii=False, indent=2))