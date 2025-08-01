import os
import aiofiles
import asyncio
from openai import AsyncOpenAI

# 配置DeepSeek API
client = AsyncOpenAI(
    api_key="sk-d3c3323a507846189cb71d387be22988",
    base_url="https://api.deepseek.com"
)

# 配置参数
WORD_COUNT = 1200
INPUT_FOLDER = "./data/活着 (余华) (Z-Library)_10000"
OUTPUT_FOLDER = f"{INPUT_FOLDER}_{WORD_COUNT}"
MAX_CONCURRENT_TASKS = 10  # 控制并发量，避免API限制


async def process_single_file(filename):
    """处理单个文件的异步协程"""
    input_path = os.path.join(INPUT_FOLDER, filename)
    output_path = os.path.join(OUTPUT_FOLDER, filename)

    # 异步读取文件
    try:
        async with aiofiles.open(input_path, mode='r', encoding='utf-8') as f:
            content = await f.read()
            content = content.strip()
    except Exception as e:
        print(f"文件读取失败 {filename}: {str(e)}")
        return

    if not content:
        print(f"跳过空文件: {filename}")
        return

    # 调用API
    try:
        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": f"""你是一个专业的文学总结助手，你将为以下文本生成精确总结，请严格遵循以下要求：
                    1. 包含所有关键情节：主要人物、核心事件、重要转折点
                    2. 总结长度严格控制在{WORD_COUNT}字左右
                    3. 总结可适当保留原文佳句，保持情节连贯性和逻辑完整
                    4. 不要出现任何评价性语言(如这个片段展现了什么，为后续埋下伏笔)
                    5. 直接输出总结内容，不要添加任何标题或额外说明"""
                },
                {
                    "role": "user",
                    "content": f"文本内容：{content}"
                }
            ],
            temperature=0.3,
            stream=False
        )

        summary = response.choices[0].message.content

        # 异步写入文件
        async with aiofiles.open(output_path, mode='w', encoding='utf-8') as f:
            await f.write(summary)

        print(f"处理成功: {filename}")

    except Exception as e:
        print(f"API处理失败 {filename}: {str(e)}")


async def process_files(prompt):
    """主处理函数"""
    # 创建输出目录
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    # 获取文件列表
    filenames = [
        f for f in os.listdir(INPUT_FOLDER)
        if f.endswith(".txt")
    ]

    # 创建信号量控制并发
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)

    async def limited_task(filename):
        async with semaphore:
            await process_single_file(filename)

    # 创建并执行所有任务
    tasks = [limited_task(f) for f in filenames]
    await asyncio.gather(*tasks)

    print("全部文件处理完成！")


if __name__ == "__main__":
    asyncio.run(process_files())