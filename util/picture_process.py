import subprocess
import os
import tempfile
import shutil
import logging
import sys
import platform

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)


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
                # 添加序号和时间轴
                f_out.write(f"{content}")
            logging.info(f"转换字幕文件: {subtitle_path} -> {srt_path}")
            return srt_path
        except Exception as e:
            logging.error(f"字幕转换失败: {e}", exc_info=True)
    return subtitle_path


def get_media_duration(media_path):
    """获取音视频文件时长（秒）"""
    cmd = [
        'ffprobe', '-v', 'error',
        '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1',
        media_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except subprocess.CalledProcessError as e:
        logging.error(f"获取时长失败: {e.stderr}")
        raise RuntimeError(f"无法获取 {media_path} 的时长") from e


def find_system_fonts():
    """获取系统字体目录"""
    system = platform.system()
    if system == 'Darwin':  # macOS
        return [
            '/System/Library/Fonts'

        ]
    elif system == 'Windows':  # Windows
        return [
            os.path.join(os.environ['WINDIR'], 'Fonts')
        ]
    else:  # Linux及其他
        return [
            '/usr/share/fonts',
            '/usr/local/share/fonts',
            os.path.expanduser('~/.fonts')
        ]


def create_image_based_video(
        segments1,
        output_file="output.mp4",
        resolution=(1920, 1080),
        fps=30,
        bg_music_path=None,
        bg_volume=0.3
):
    print(segments1)
    """
    从图片和音频创建视频并添加字幕和背景音乐

    参数:
    segments - 列表的列表，每个子列表包含: [字幕文件, 图片文件, 音频文件]
    output_file - 输出视频路径
    resolution - 视频分辨率
    fps - 视频帧率
    bg_music_path - 背景音乐文件路径（可选）
    bg_volume - 背景音乐音量（0.0-1.0，默认0.3）

    返回:
    最终视频文件路径
    """
    # 创建临时工作目录
    temp_dir = tempfile.mkdtemp(prefix="video_creator_")
    logging.info(f"创建临时目录: {temp_dir}")
    processed_segments = []
    intermediate_output = os.path.join(temp_dir, "intermediate.mp4")

    try:
        # 获取系统字体路径
        font_dirs = find_system_fonts()
        font_paths = ":".join([d for d in font_dirs if os.path.isdir(d)])
        logging.info(f"检测到的字体目录: {font_paths or '无'}")

        # 处理每个片段
        for i, (subtitle, image, audio) in enumerate(segments1):
            logging.info(f"处理第 {i + 1}/{len(segments1)} 个片段...")
            try:
                subtitle = validate_file(subtitle)
                image = validate_file(image)
                audio = validate_file(audio)
            except Exception as e:
                logging.error(f"文件验证失败: {e}")
                raise

            subtitle = convert_to_srt_if_needed(subtitle)
            audio_duration = get_media_duration(audio)
            logging.info(f"音频时长: {audio_duration:.2f}秒")

            segment_file = os.path.join(temp_dir, f"segment_{i}.mp4")
            scale_filter = f"scale={resolution[0]}:{resolution[1]}:force_original_aspect_ratio=decrease"
            pad_filter = "pad=x=(ow-iw)/2:y=(oh-ih)/2:color=black"

            # 尝试多种字幕方案
            success = False
            for attempt in range(1, 4):
                try:
                    if attempt == 1:  # 方案1: subtitles滤镜
                        subtitle_filter = (
                            f"subtitles='{subtitle}':fontsdir='{font_paths}':"
                            f"force_style='FontName=ArialHB,FontSize=24,PrimaryColour=&H00FFFFFF'"
                        )
                        filters = f"{scale_filter},{pad_filter},{subtitle_filter}"
                    elif attempt == 2:  # 方案2: drawtext滤镜
                        text_filter = (
                            f"drawtext=textfile='{subtitle}':fontfile=ArialHB.ttc:"
                            f"fontsize=24:fontcolor=white:x=(w-tw)/2:y=h-th-10"
                        )
                        filters = f"{scale_filter},{pad_filter},{text_filter}"
                    else:  # 方案3: 无字幕
                        filters = f"{scale_filter},{pad_filter}"
                        logging.warning(f"片段 {i + 1} 使用无字幕方案")

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
                    logging.info(f"执行方案{attempt}命令: {' '.join(cmd)}")
                    subprocess.run(cmd, check=True, capture_output=True)
                    success = True
                    break
                except Exception as e:
                    logging.warning(f"方案{attempt}失败: {str(e)[:100]}")

            if not success:
                raise RuntimeError(f"所有方案均失败，无法处理片段 {i + 1}")
            processed_segments.append(segment_file)
            logging.info(f"片段 {i + 1} 处理完成")

        # 拼接所有片段
        logging.info(f"拼接 {len(processed_segments)} 个片段...")
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
            intermediate_output
        ]
        subprocess.run(concat_cmd, check=True)

        # 添加背景音乐（带循环和截断）
        if bg_music_path:
            try:
                logging.info("添加背景音乐...")
                bg_music_path = validate_file(bg_music_path)
                video_duration = get_media_duration(intermediate_output)
                bg_duration = get_media_duration(bg_music_path)

                logging.info(f"视频时长: {video_duration:.2f}秒, BGM时长: {bg_duration:.2f}秒")

                # 构建音频混合滤镜（自动循环短BGM）
                filter_complex = (
                    f"[0:a]volume=1.0[voice];"
                    f"[1:a]aloop=loop=-1:size=1e9,atrim=0:{video_duration},"
                    f"asetpts=PTS-STARTPTS,volume={bg_volume}[bg];"
                    f"[voice][bg]amix=inputs=2:duration=first[a]"
                )

                mix_cmd = [
                    'ffmpeg', '-y',
                    '-i', intermediate_output,
                    '-i', bg_music_path,
                    '-filter_complex', filter_complex,
                    '-map', '0:v',
                    '-map', '[a]',
                    '-c:v', 'copy',
                    '-c:a', 'aac',
                    '-b:a', '192k',
                    output_file
                ]
                logging.info(f"执行音频混合命令: {' '.join(mix_cmd)}")
                subprocess.run(mix_cmd, check=True)
                logging.info("背景音乐添加成功")
            except Exception as e:
                logging.error(f"添加背景音乐失败: {e}, 使用原始音频", exc_info=True)
                shutil.copy(intermediate_output, output_file)
        else:
            shutil.copy(intermediate_output, output_file)

        logging.info(f"✅ 视频创建完成: {os.path.abspath(output_file)}")
        return output_file

    except Exception as e:
        logging.exception("❌ 处理过程中出错")
        raise
    finally:
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
            logging.info(f"临时目录已清理: {temp_dir}")
        except Exception as e:
            logging.warning(f"清理临时目录失败: {e}")


if __name__ == "__main__":
    # 示例使用
    base_path = "output/result_20250806_221904/"
    segments = [
        [
            os.path.join(base_path, "text_1.txt"),
            os.path.join(base_path, "image_1.jpg"),
            os.path.join(base_path, "audio_1.mp3")
        ],
        [
            os.path.join(base_path, "text_2.txt"),
            os.path.join(base_path, "image_2.jpg"),
            os.path.join(base_path, "audio_2.mp3")
        ],
        [
            os.path.join(base_path, "text_3.txt"),
            os.path.join(base_path, "image_3.jpg"),
            os.path.join(base_path, "audio_3.mp3")
        ]
    ]

    output = create_image_based_video(
        segments,
        output_file="final_videolyh5.mp4",
        resolution=(1080, 720),
        fps=25,
        bg_music_path="../garbage/bgm1.mp3",  # 背景音乐
        bg_volume=0.1  # 背景音乐音量
    )