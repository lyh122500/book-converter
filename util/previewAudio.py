import uuid
import requests
import os
import base64

# 定义音色列表
VOICES = [
    {'id': 'zh_female_tianmeitaozi_mars_bigtts', 'name': '甜美桃子', 'description': '甜美可爱的女声',
     'language': '中文', 'platforms': '通用', 'category': 'female'},
    {'id': 'zh_female_vv_mars_bigtts', 'name': 'Vivi', 'description': '清新自然的女声', 'language': '中文',
     'platforms': '通用', 'category': 'female'},
    {'id': 'zh_male_wennuanahu_moon_bigtts', 'name': '温暖阿虎/Alvin', 'description': '温暖亲切的男声',
     'language': '中文, 美式英语', 'platforms': '豆包, Cici', 'category': 'male'},
    {'id': 'zh_male_shaonianzixin_moon_bigtts', 'name': '少年梓辛/Brayan', 'description': '青春活力的男声',
     'language': '中文, 美式英语', 'platforms': '豆包, Cici, 剪映', 'category': 'male'}
]


def _generate_and_download_audio(text: str, voice_type: str) -> bytes:
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

        # 获取base64编码的音频数据
        audio_base64 = resp.json()['data']

        # 解码base64数据为二进制
        audio_data = base64.b64decode(audio_base64)

        return audio_data
    except Exception as e:
        print(f"语音生成失败: {e}")
        raise


def save_audio_to_file(audio_data: bytes, filename: str):
    """将音频数据保存为文件"""
    try:
        with open(filename, 'wb') as f:
            f.write(audio_data)
        print(f"音频已保存: {filename}")
    except Exception as e:
        print(f"保存音频文件失败: {e}")
        raise


def generate_and_save_introductions():
    """为每种音色生成并保存自我介绍音频"""
    results = []
    for voice in VOICES:
        try:
            # 为每种音色生成特定的自我介绍文本
            introduction_text = f"你好，我是{voice['name']}"

            # 生成音频数据
            audio_data = _generate_and_download_audio(introduction_text, voice['id'])

            # 创建文件名
            filename = f"{voice['name']}_自我介绍.mp3"
            filename = "".join(c for c in filename if c not in '<>:"/\\|?*').replace(' ', '_')

            # 保存音频文件
            save_audio_to_file(audio_data, filename)

            results.append({
                'voice': voice['name'],
                'filename': filename,
                'status': 'success'
            })
        except Exception as e:
            results.append({
                'voice': voice['name'],
                'filename': None,
                'status': f'failed: {str(e)}'
            })
    return results


# 使用示例
if __name__ == "__main__":
    results = generate_and_save_introductions()

    print("\n生成结果:")
    for result in results:
        print(f"{result['voice']}: {result['status']}")