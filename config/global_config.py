import os
from datetime import timedelta

from openai import OpenAI


class Config:
    # Redis configuration
    REDIS_HOST = os.getenv('REDIS_HOST', '117.72.54.227')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_DB = int(os.getenv('REDIS_DB', 0))
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)

    # Flask application configuration
    UPLOAD_FOLDER = 'temp_uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB limit
    SESSION_EXPIRE = timedelta(hours=1)  # Session expiration time
    RATE_LIMIT = "5 per second"  # Default rate limit

    from openai import AsyncOpenAI

    # 全局 DeepSeek API 客户端
    dsclient = AsyncOpenAI(
        api_key="sk-d3c3323a507846189cb71d387be22988",
        base_url="https://api.deepseek.com"
    )


    ecloudClient = OpenAI(
        api_key="AajlZARHvTpZARPumrdvS1tSuOUBsG1xbWHyznpGsmU",
        base_url="https://zhenze-huhehaote.cmecloud.cn/v1"
    )

    asyncEcloudClient = AsyncOpenAI(
        api_key="AajlZARHvTpZARPumrdvS1tSuOUBsG1xbWHyznpGsmU",
        base_url="https://zhenze-huhehaote.cmecloud.cn/v1"
    )


    seeDreamClient = OpenAI(
        # 此为默认路径，您可根据业务所在地域进行配置
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        # 从环境变量中获取您的 API Key。此为默认方式，您可根据需要进行修改
        api_key="336dc05b-8016-4cc9-a7a5-10e52fb387ac",
    )

    @staticmethod
    def get_summary_prompt(word_count=1500):
        raw_prompt = f"""你是一个专业的文学总结助手，你将为以下文本生成精确总结，请严格遵循以下要求：
                        1. 包含所有关键情节：主要人物、核心事件、重要转折点
                        2. 总结长度严格控制在{word_count}字左右
                        3. 总结可适当保留原文佳句，保持情节连贯性和逻辑完整
                        4. 不要出现任何评价性语言(如这个片段展现了什么，为后续埋下伏笔)
                        5. 直接输出总结内容，不要添加任何标题或额外说明"""

        return raw_prompt
