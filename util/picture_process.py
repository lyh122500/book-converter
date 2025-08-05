import subprocess
import os
import tempfile
import shutil
import shlex
from pathlib import Path


def validate_file(file_path):
    """验证文件是否存在且可读"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")
    if not os.access(file_path, os.R_OK):
        raise PermissionError(f"文件不可读: {file_path}")
    return os.path.abspath(file_path)


def convert_to_srt_if_needed(subtitle_path):
    """如果需要，将文本文件转换为SRT格式"""
    if subtitle_path.endswith('.txt'):
        srt_path = subtitle_path.replace('.txt', '.srt')
        try:
            with open(subtitle_path, 'r', encoding='utf-8') as f_in, \
                    open(srt_path, 'w', encoding='utf-8') as f_out:
                content = f_in.read()
                # 简单转换：添加SRT基本格式
                f_out.write(f"1\n00:00:00,000 --> 99:59:59,999\n{content}")
            return srt_path
        except Exception as e:
            print(f"无法转换字幕文件: {e}")
    return subtitle_path


def create_image_based_video(segments, output_file="output.mp4", resolution=(1920, 1080), fps=30):
    """
    从图片和音频创建视频并添加字幕（macOS优化版）

    参数:
    segments - 列表的列表，每个子列表包含: [字幕文件, 图片文件, 音频文件]
    output_file - 输出视频路径
    resolution - 视频分辨率
    fps - 视频帧率

    返回:
    最终视频文件路径
    """
    # 创建临时工作目录（在当前目录下）
    temp_dir = tempfile.mkdtemp(dir=os.getcwd())
    processed_segments = []

    try:
        for i, (subtitle, image, audio) in enumerate(segments):
            print(f"\n处理第 {i + 1}/{len(segments)} 个片段...")

            # 验证并获取绝对路径
            try:
                subtitle = validate_file(subtitle)
                image = validate_file(image)
                audio = validate_file(audio)
            except Exception as e:
                print(f"文件验证失败: {e}")
                raise

            # 尝试转换为SRT格式（如果需要）
            subtitle = convert_to_srt_if_needed(subtitle)

            # 获取音频时长
            try:
                cmd = [
                    'ffprobe', '-v', 'error',
                    '-show_entries', 'format=duration',
                    '-of', 'default=noprint_wrappers=1:nokey=1',
                    audio
                ]
                result = subprocess.run(cmd, capture_output=True, text=True)
                audio_duration = float(result.stdout.strip())
                print(f"音频时长: {audio_duration}秒")
            except Exception as e:
                print(f"获取音频时长失败: {e}")
                raise

            # 生成片段文件名
            segment_file = os.path.join(temp_dir, f"segment_{i}.mp4")

            # 构建FFmpeg命令（修正版）
            scale_filter = f"scale={resolution[0]}:{resolution[1]}:force_original_aspect_ratio=decrease"
            pad_filter = "pad=x=(ow-iw)/2:y=(oh-ih)/2:color=black"

            # 方案1：使用subtitles滤镜
            try:
                subtitle_filter = f"subtitles='{subtitle}':fontsdir=/System/Library/Fonts:force_style='FontName=Arial,FontSize=24,PrimaryColour=&H00FFFFFF'"
                filters = f"{scale_filter},{pad_filter},{subtitle_filter}"

                cmd = [
                    'ffmpeg', '-y',
                    '-loop', '1',
                    '-i', image,
                    '-i', audio,
                    '-vf', filters,
                    '-t', str(audio_duration),
                    '-c:v', 'libx264',
                    '-c:a', 'aac',
                    '-pix_fmt', 'yuv420p',
                    '-r', str(fps),
                    '-shortest',
                    segment_file
                ]

                print("\n执行方案1命令:", " ".join(cmd))
                result = subprocess.run(cmd, capture_output=True, text=True)

                if result.returncode != 0:
                    raise RuntimeError(f"方案1失败: {result.stderr}")

            except Exception as e:
                print(f"方案1失败: {e}")
                # 方案2：使用drawtext滤镜
                try:
                    print("尝试方案2...")
                    text_filter = f"drawtext=textfile='{subtitle}':fontfile=/System/Library/Fonts/Supplemental/Arial.ttf:fontsize=24:fontcolor=white:x=(w-tw)/2:y=h-th-10"
                    filters = f"{scale_filter},{pad_filter},{text_filter}"

                    cmd = [
                        'ffmpeg', '-y',
                        '-loop', '1',
                        '-i', image,
                        '-i', audio,
                        '-vf', filters,
                        '-t', str(audio_duration),
                        '-c:v', 'libx264',
                        '-c:a', 'aac',
                        '-pix_fmt', 'yuv420p',
                        '-r', str(fps),
                        '-shortest',
                        segment_file
                    ]

                    print("\n执行方案2命令:", " ".join(cmd))
                    result = subprocess.run(cmd, capture_output=True, text=True)

                    if result.returncode != 0:
                        raise RuntimeError(f"方案2失败: {result.stderr}")

                except Exception as e:
                    print(f"方案2失败: {e}")
                    # 方案3：不使用字幕
                    print("尝试方案3（无字幕）...")
                    filters = f"{scale_filter},{pad_filter}"

                    cmd = [
                        'ffmpeg', '-y',
                        '-loop', '1',
                        '-i', image,
                        '-i', audio,
                        '-vf', filters,
                        '-t', str(audio_duration),
                        '-c:v', 'libx264',
                        '-c:a', 'aac',
                        '-pix_fmt', 'yuv420p',
                        '-r', str(fps),
                        '-shortest',
                        segment_file
                    ]

                    print("\n执行方案3命令:", " ".join(cmd))
                    result = subprocess.run(cmd, capture_output=True, text=True)

                    if result.returncode != 0:
                        raise RuntimeError(f"所有方案均失败")

            processed_segments.append(segment_file)
            print(f"片段 {i + 1} 处理完成")

        # 拼接所有片段
        print("\n拼接所有片段...")
        list_file = os.path.join(temp_dir, "concat_list.txt")
        with open(list_file, 'w') as f:
            for seg in processed_segments:
                f.write(f"file '{os.path.basename(seg)}'\n")

        concat_cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', list_file,
            '-c', 'copy',
            output_file
        ]
        subprocess.run(concat_cmd, check=True)

        print(f"\n✅ 视频创建完成: {os.path.abspath(output_file)}")
        return output_file

    except Exception as e:
        print(f"\n❌ 处理过程中出错: {e}")
        raise
    finally:
        # 清理临时文件
        shutil.rmtree(temp_dir, ignore_errors=True)
        print("临时文件已清理")


if __name__ == "__main__":
    # 示例使用
    base_path = "garbage/"
    segments = [
        [
            os.path.join(base_path, "1.txt"),
            os.path.join(base_path, "1.jpg"),
            os.path.join(base_path, "1.m4a")
        ],
        [
            os.path.join(base_path, "2.txt"),
            os.path.join(base_path, "2.jpg"),
            os.path.join(base_path, "2.m4a")
        ],
        [
            os.path.join(base_path, "3.txt"),
            os.path.join(base_path, "3.jpg"),
            os.path.join(base_path, "3.m4a")
        ]
    ]

    output = create_image_based_video(
        segments,
        output_file="final_video.mp4",
        resolution=(1280, 853),
        fps=25
    )