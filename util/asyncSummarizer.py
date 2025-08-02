import os
import aiofiles
import asyncio
from openai import AsyncOpenAI
from typing import List, Optional


class AsyncTextSummarizer:
    def __init__(
            self,
            api_key: str = "sk-d3c3323a507846189cb71d387be22988",
            base_url: str = "https://api.deepseek.com",
            model: str = "deepseek-chat",
            word_count: int = 1200,
            max_concurrent_tasks: int = 10,
            temperature: float = 0.3
    ):
        """
        异步文本总结工具类

        参数:
            api_key: DeepSeek API密钥
            base_url: API基础URL
            model: 使用的模型名称
            word_count: 总结字数目标
            max_concurrent_tasks: 最大并发任务数
            temperature: 生成温度
        """
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.word_count = word_count
        self.max_concurrent_tasks = max_concurrent_tasks
        self.temperature = temperature

        # 验证参数
        if not api_key:
            raise ValueError("API key is required")
        if word_count <= 0:
            raise ValueError("Word count must be positive")
        if max_concurrent_tasks <= 0:
            raise ValueError("Max concurrent tasks must be positive")

    async def _process_single_segment(
            self,
            segment: str,
            segment_id: Optional[int] = None,
            semaphore: Optional[asyncio.Semaphore] = None
    ) -> str:
        """
        处理单个文本片段

        参数:
            segment: 要处理的文本内容
            segment_id: 片段标识(用于日志)
            semaphore: 并发控制信号量

        返回:
            处理后的文本
        """
        if not segment.strip():
            print(f"跳过空片段: {segment_id or '未知'}")
            return ""

        try:
            # 如果有信号量则获取许可
            if semaphore:
                async with semaphore:
                    return await self._call_summarize_api(segment)
            else:
                return await self._call_summarize_api(segment)

        except Exception as e:
            print(f"片段处理失败 {segment_id or '未知'}: {str(e)}")
            return ""

    async def _call_summarize_api(self, text: str) -> str:
        """调用API进行总结"""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": f"""你是一个专业的文学总结助手，你将为以下文本生成精确总结，请严格遵循以下要求：
                    1. 包含所有关键情节：主要人物、核心事件、重要转折点
                    2. 总结长度严格控制在{self.word_count}字左右
                    3. 总结可适当保留原文佳句，保持情节连贯性和逻辑完整
                    4. 不要出现任何评价性语言(如这个片段展现了什么，为后续埋下伏笔)
                    5. 直接输出总结内容，不要添加任何标题或额外说明"""
                },
                {
                    "role": "user",
                    "content": f"文本内容：{text}"
                }
            ],
            temperature=self.temperature,
            stream=False
        )
        return response.choices[0].message.content

    def summarize_segments(
            self,
            segments: List[str],
    ):
        """
        处理多个文本片段
        参数:
            segments: 文本片段列表
        返回:
          合并后的字符串
        """

        # 创建信号量控制并发
        semaphore = asyncio.Semaphore(self.max_concurrent_tasks)

        # 创建并执行所有任务
        tasks = [
            self._process_single_segment(seg, idx, semaphore)
            for idx, seg in enumerate(segments, 1)
        ]
        results = asyncio.gather(*tasks)

        return "\n\n".join(filter(None, results))
