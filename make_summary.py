import os
from openai import OpenAI

# 配置DeepSeek API
client = OpenAI(api_key="sk-d3c3323a507846189cb71d387be22988", base_url="https://api.deepseek.com")

# 文件夹路径配置
percent = 20
input_folder = "霍乱时期的爱情 (加西亚·马尔克斯) (Z-Library)_preprocessed_10000"  # 存放分段文本的文件夹
output_folder = input_folder + '_' + str(percent) # 存放总结结果的文件夹

# 创建输出文件夹（如果不存在）
os.makedirs(output_folder, exist_ok=True)

# 遍历输入文件夹中的所有txt文件
for filename in os.listdir(input_folder):
    if filename.endswith(".txt"):
        input_file_path = os.path.join(input_folder, filename)
        output_file_path = os.path.join(output_folder, filename)

        # 读取当前文件内容
        with open(input_file_path, "r", encoding="utf-8") as file:
            text_content = file.read().strip()  # 去除首尾空白字符

        # 跳过空文件
        if not text_content:
            print(f"跳过空文件: {filename}")
            continue

        # 调用DeepSeek生成总结
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {
                        "role": "system",
                        "content": f"""你是一个专业的文学总结助手，请严格遵循以下要求：
                        1. 总结必须包含原文所有关键情节：主要人物、核心事件、重要转折点
                        2. 总结长度必须控制在原文长度的{percent}%左右（请自行计算比例）"
                        3. 使用简洁的叙述体，避免评价性语言
                        4. 保持情节连贯性，确保逻辑链条完整
                        5. 直接输出总结内容，不要添加任何额外说明或标题"""
                    },
                    {
                        "role": "user",
                        "content": f"""请为以下文本生成精确总结（长度控制在原文的{percent}%以内）：
                        要求：- 识别并保留所有关键情节要素
                        - 确保人物关系和事件发展清晰
                        - 保持原文的核心冲突和转折点
                        文本内容：
                        {text_content}
                        """
                    }
                ],
                stream=False,
                temperature=0.3,  # 降低随机性，确保总结稳定
            )
            summary = response.choices[0].message.content

            # 保存总结到输出文件
            with open(output_file_path, "w", encoding="utf-8") as file:
                file.write(summary)
            print(f"成功处理: {filename}")

        except Exception as e:
            print(f"处理文件 {filename} 时出错: {e}")

print("所有文件处理完成！")