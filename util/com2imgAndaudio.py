import concurrent.futures
import json
import os
import re
import time
import uuid
from datetime import datetime

import requests
import io
from typing import List, Tuple
from flask import current_app

from config.global_config import Config
from util.picture_process import create_image_based_video


def process_commentary(commentary: str, video_type: str, voice_type: str, resolution=(1920, 1080)) -> Tuple[List[str], List[bytes], List[bytes]]:
    """
    处理解说词并返回: (分段文本, 图片二进制数组, 音频二进制数组)
    """
    # 1. 分段处理（保留句号）
    raw_sentences = re.split(r'(?<=[。？！.?!])', commentary.strip())
    sentences = [s + f"[{video_type}]" for s in raw_sentences if s.strip()]
    # 2. 线程池配置（建议根据API限制调整max_workers）
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        # 3. 提交所有任务
        future_to_index = {}
        for idx, sentence in enumerate(sentences):
            # 图片任务
            future_to_index[executor.submit(_generate_and_download_image, sentence)] = (idx, 'image')
            # 音频任务
            future_to_index[executor.submit(_generate_and_download_audio, sentence, voice_type)] = (idx, 'audio')

        # 4. 初始化结果容器
        image_data = [None] * len(sentences)
        audio_data = [None] * len(sentences)

        # 5. 同步等待所有任务完成
        for future in concurrent.futures.as_completed(future_to_index):
            idx, task_type = future_to_index[future]
            try:
                result = future.result()
                if task_type == 'image':
                    image_data[idx] = result
                else:
                    audio_data[idx] = result
            except Exception as e:
                print(f"{task_type} 处理失败: {e}")
                # 失败时存入空字节（或自定义错误标识）
                if task_type == 'image':
                    image_data[idx] = b''
                else:
                    audio_data[idx] = b''

    return save_and_return_results(sentences, image_data, audio_data)


def _generate_and_download_image(prompt: str, max_retries: int = 2,resolution=(1920, 1080)) -> bytes:
    """生成并下载图片（自动重试敏感内容错误）"""
    retry_count = 0
    last_error = None
    size = str(resolution[0])+str(resolution[1])
    while retry_count <= max_retries:
        try:
            # 1. 生成图片URL（添加安全提示）
            response = Config.seeDreamClient.images.generate(
                model="doubao-seedream-3-0-t2i-250415",
                prompt=f"安全合规的图片，无敏感内容。{prompt}",
                size=size,
            )

            # 2. 下载图片
            resp = requests.get(response.data[0].url, timeout=10)
            resp.raise_for_status()
            return resp.content

        except Exception as e:
            last_error = e
            if hasattr(e, 'response') and getattr(e.response, 'text', ''):
                error_data = json.loads(e.response.text)
                if error_data.get('error', {}).get('code') == 'OutputImageSensitiveContentDetected':
                    retry_count += 1
                    if retry_count <= max_retries:
                        time.sleep(1)  # 添加延迟
                        continue
            break

    raise Exception(f"图片生成失败（重试{retry_count}次）: {str(last_error)}")


def _generate_and_download_audio(text: str,  voice_type: str) -> bytes:
    """生成并下载语音（返回二进制MP3）"""
    try:
        # 1. 获取音频URL
        payload = {
            "app": {
                "appid": 9877711930,
                "token": "RRtmH1szggQxfs3u9_wpz3Dmlil187Xh",
                "cluster": "volcano_tts",
            },
            "user": {"uid": str(uuid.uuid4())},
            "audio": {
                "voice_type": voice_type,
                "encoding": "mp3",
            },
            "request": {
                "reqid": str(uuid.uuid4()),
                "text": text,
                "operation": "query",
            }
        }
        headers = {
            "Authorization": "Bearer;RRtmH1szggQxfs3u9_wpz3Dmlil187Xh",  # 注意空格
        }
        resp = requests.post(
            "https://openspeech.bytedance.com/api/v1/tts",
            headers=headers,
            json=payload,
            timeout=10
        )
        resp.raise_for_status()
        print(resp)
        audio = resp.json()['data']
        return audio
    except Exception as e:
        print(f"语音下载失败: {e}")
        raise

def save_and_return_results(
        sentences: List[str],
        images: List[bytes],
        audios: List[bytes],
        output_dir: str = "output"
) -> Tuple[str, List[List[str]]]:
    """
    保存结果到本地并返回文件路径和双层链表结构
    返回: (保存目录路径, 双层链表[
        [文本路径1, 图片路径1, 音频路径1],
        [文本路径2, 图片路径2, 音频路径2],
        ...
    ])
    """
    # 1. 创建输出目录（按时间戳命名）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_dir = os.path.join(output_dir, f"result_{timestamp}")
    os.makedirs(save_dir, exist_ok=True)

    # 初始化双层链表结构
    result_linked_list = []

    # 2. 保存文本文件
    text_paths = []
    with open(os.path.join(save_dir, "full_text.txt"), "w", encoding="utf-8") as f:
        for i, sentence in enumerate(sentences):
            f.write(f"Segment {i + 1}: {sentence}\n\n")
            text_path = os.path.join(save_dir, f"text_{i + 1}.txt")
            text_paths.append(text_path)
            with open(text_path, "w", encoding="utf-8") as seg_f:
                seg_f.write(sentence)

    # 3. 保存图片（确保是bytes）
    image_paths = []
    for i, img_data in enumerate(images):
        path = os.path.join(save_dir, f"image_{i + 1}.jpg")
        if isinstance(img_data, bytes) and img_data:  # 确保是有效的二进制数据
            with open(path, "wb") as f:
                f.write(img_data)
            image_paths.append(path)
        else:
            print(f"⚠️ 图片{i + 1}数据无效（类型：{type(img_data)}）")
            image_paths.append("")

    # 4. 保存音频（确保是bytes）
    audio_paths = []
    for i, audio_data in enumerate(audios):
        path = os.path.join(save_dir, f"audio_{i + 1}.mp3")
        if isinstance(audio_data, bytes) and audio_data:  # 确保是有效的二进制数据
            with open(path, "wb") as f:
                f.write(audio_data)
            audio_paths.append(path)
        elif isinstance(audio_data, str):  # 如果是base64字符串
            try:
                import base64
                with open(path, "wb") as f:
                    f.write(base64.b64decode(audio_data))
                audio_paths.append(path)
            except Exception as e:
                print(f"⚠️ 音频{i + 1}解码失败: {e}")
                audio_paths.append("")
        else:
            print(f"⚠️ 音频{i + 1}数据无效（类型：{type(audio_data)}）")
            audio_paths.append("")

    # 构建双层链表结构
    for i in range(len(sentences)):
        # 每个分镜对应一个包含三个路径的列表
        scene_data = [
            text_paths[i] if i < len(text_paths) else "",
            image_paths[i] if i < len(image_paths) else "",
            audio_paths[i] if i < len(audio_paths) else ""
        ]
        result_linked_list.append(scene_data)

    print(f"✅ 结果已保存到目录: {save_dir}")
    return save_dir, result_linked_list


if __name__ == "__main__":
    save, path = process_commentary("初次翻开余华的《活着》，一股沉重的悲凉便扑面而来。福贵的命运像一把钝刀，缓缓割开心灵的茧，让我在深夜的宿舍里久久不能平静。这部小说，作为中国当代文学的里程碑，不仅以冷峻的笔触刻画出生命的荒诞与坚韧，更在全球文坛上树立了不朽的典范——它让我们在个体的悲剧中，窥见一个民族的历史伤痕。")
    dir = create_image_based_video(path,output_file="final_video.mp4",resolution=(1280, 720),fps=25)
