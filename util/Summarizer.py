import os
from openai import OpenAI
from threading import Semaphore
from concurrent.futures import ThreadPoolExecutor


class Summarizer:
    def __init__(self, api_key="sk-d3c3323a507846189cb71d387be22988", base_url="https://api.deepseek.com",
                 max_workers=10):
        """
        初始化文件处理器
        :param api_key: DeepSeek API密钥
        :param base_url: API基础URL
        :param max_workers: 最大并发工作线程数
        """
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        self.max_workers = max_workers
        self.semaphore = Semaphore(max_workers)

    def process_segment(self, segment, prompt):
        """
        处理单个文本片段
        :param segment: 文本内容
        :param word_count: 目标字数
        :return: 处理后的总结文本
        """
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {
                        "role": "system",
                        "content": f"""{prompt}"""
                    },
                    {
                        "role": "user",
                        "content": f"文本内容：{segment}"
                    }
                ],
                temperature=0.3,
                stream=False
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"API处理失败: {str(e)}")
            return None

    def process_segments(self, segments, prompt):
        """
        批量处理文本片段
        :param segments: 文本片段列表
        :param prompt: 用户prompt
        :return: 处理后的总结列表
        """
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            results = list(executor.map(
                lambda seg: self.process_segment(seg, prompt),
                segments
            ))

        return ' '.join(filter(None, results))
