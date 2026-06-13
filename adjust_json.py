import os
import json
import sys


def process_json_files(folder_path, output_file):
    """
    处理文件夹中的所有JSON文件，删除指定键后合并为一个JSON数组

    Args:
        folder_path (str): 包含JSON文件的文件夹路径
        output_file (str): 输出文件的路径
    """
    # 存储所有处理后的JSON对象
    result = []

    # 检查文件夹是否存在
    if not os.path.exists(folder_path):
        print(f"错误：文件夹 '{folder_path}' 不存在")
        return False

    # 获取文件夹中的所有JSON文件
    json_files = [f for f in os.listdir(folder_path) if f.endswith('.json')]

    if not json_files:
        print(f"在文件夹 '{folder_path}' 中未找到JSON文件")
        return False

    print(f"找到 {len(json_files)} 个JSON文件")

    # 处理每个JSON文件
    for filename in json_files:
        file_path = os.path.join(folder_path, filename)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 删除指定的键（如果存在）
            if 'config' in data:
                del data['config']
            if 'book_info' in data:
                del data['book_info']

            # 将处理后的对象添加到结果列表
            result.append(data)

            print(f"已处理: {filename}")

        except Exception as e:
            print(f"处理文件 {filename} 时出错: {str(e)}")

    # 将结果写入输出文件
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)

        print(f"成功合并所有JSON文件到: {output_file}")
        return True

    except Exception as e:
        print(f"写入输出文件时出错: {str(e)}")
        return False


if __name__ == "__main__":
    # 设置默认的文件夹路径和输出文件名
    folder_path = "/Users/yonghaoliu/Desktop/fine_tuning_data"
    output_file = 'merged_output.json'

    if not output_file:
        output_file = "merged_output.json"

    # 处理JSON文件
    success = process_json_files(folder_path, output_file)

    if not success:
        sys.exit(1)