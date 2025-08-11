import asyncio
import json
import shutil
import tempfile
import threading

from flask import Flask, request, jsonify, send_file
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import time

from config.global_config import Config
from dao.redisDao import RedisDao
from util.author_configuration import get_author_info, get_poetry_author_info
from dao.redisDao import RedisDao
from util.Summarizer import Summarizer
from util.com2imgAndaudio import process_commentary
from util.make_novel_prompt import generate_commentary_prompt, generate_new_commentary
from util.make_poetry_prompt import generate_poetry_commentary
from util.picture_process import create_image_based_video
from util.preprocess import process_single_file

app = Flask(__name__)
app.config.from_object(Config)

redis_dao = RedisDao()
summarizer = Summarizer()

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    storage_uri=f"redis://{Config.REDIS_HOST}:{Config.REDIS_PORT}/{Config.REDIS_DB}",
    storage_options={"password": Config.REDIS_PASSWORD}
)

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


def check_rate_limit(session_id):
    """检查会话级别的速率限制"""
    r = redis_dao.get_connection()
    rate_key = f"ratelimit:{session_id}"

    # 5 requests per second
    current = r.incr(rate_key)
    if current == 1:
        r.expire(rate_key, 1)

    if current > 5:
        return False
    return True


@app.route('/api/testRedis', methods=['GET'])
@limiter.limit(app.config['RATE_LIMIT'])
def test_redis_connection():
    """测试 Redis 连接是否正常"""
    r = redis_dao.get_connection()
    try:
        if r.ping():
            return jsonify({
                'message': '✅ Redis 连接成功'
            }), 201
    except Exception as e:
        return jsonify({
            'message': '✅ Redis 连接失败{e}'
        }), 201


@app.route('/api/create_session', methods=['POST'])
@limiter.limit(app.config['RATE_LIMIT'])
def create_session():
    """创建新会话并返回session_id"""
    try:
        session_id = redis_dao.generate_session_id()
        r = redis_dao.get_connection()

        # 初始化会话元数据
        r.hset(
            f"session:{session_id}:meta",
            mapping={
                'created': time.time(),
                'status': 'created',
                'last_active': time.time()
            }
        )
        r.expire(f"session:{session_id}:meta", int(app.config['SESSION_EXPIRE'].total_seconds()))

        return jsonify({
            'session_id': session_id,
            'expires_in': int(app.config['SESSION_EXPIRE'].total_seconds()),
            'message': 'Session created successfully'
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/novel/upload', methods=['POST'])
@limiter.limit(app.config['RATE_LIMIT'])
def upload_file():
    """上传文件到指定会话"""
    # 检查会话ID
    session_id = request.form.get('session_id')
    if not session_id:
        return jsonify({'error': 'session_id is required'}), 400

    # 会话级速率限制
    if not check_rate_limit(session_id):
        return jsonify({'error': 'Rate limit exceeded for this session'}), 429

    r = redis_dao.get_connection()

    # 检查会话是否存在
    if not r.exists(f"session:{session_id}:meta"):
        return jsonify({'error': 'Invalid or expired session_id'}), 404

    # 检查文件上传
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    filename = file.filename
    # 检查文件是否选择
    if filename == '':
        return jsonify({'error': 'No selected file'}), 400

    try:
        # 获取文件内容类型
        content_type = file.content_type or 'application/octet-stream'

        # 根据内容类型决定处理方式
        if content_type.startswith('text/'):
            # 文本文件直接读取内容
            file_content = file.read().decode('utf-8')
        else:
            # 二进制文件保存到临时文件
            temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_{session_id}_{filename}")
            file.save(temp_path)
            with open(temp_path, 'rb') as f:
                file_content = f.read().hex()  # 二进制转为十六进制字符串存储
            os.remove(temp_path)

        # 存储到Redis
        file_data = {
            'filename': filename,
            'content_type': content_type,
            'size': len(file_content)
        }

        r.setex(
            f"session:{session_id}:file",
            int(app.config['SESSION_EXPIRE'].total_seconds()),
            json.dumps(file_data)
        )

        r.setex(
            f"session:{session_id}:content",
            int(app.config['SESSION_EXPIRE'].total_seconds()),
            file_content
        )

        # 更新会话状态
        r.hset(f"session:{session_id}:meta", 'status', 'file_uploaded')
        r.hset(f"session:{session_id}:meta", 'last_active', time.time())

        return jsonify({
            'session_id': session_id,
            'filename': filename,
            'content_type': content_type,
            'size': len(file_content),
            'message': 'File uploaded successfully'
        }), 200

    except UnicodeDecodeError:
        return jsonify({'error': 'File encoding error (only UTF-8 text files supported)'}), 400
    except Exception as e:
        app.logger.error(f"Upload error: {str(e)}")
        return jsonify({'error': 'File upload failed'}), 500


@app.route('/api/novel/raw_prompt', methods=['GET'])
@limiter.limit(app.config['RATE_LIMIT'])
def get_raw_prompt():
    session_id = request.form.get('session_id')
    word_count = request.form.get('word_count')
    return jsonify({
        'session_id': session_id,
        'prompt': Config.get_summary_prompt(word_count)
    }), 200


@app.route('/api/novel/summarize', methods=['POST'])
@limiter.limit(app.config['RATE_LIMIT'])
def process_file():
    """处理文件（示例接口）"""
    session_id = request.form.get('session_id')
    prompt = request.form.get('prompt')
    if not session_id:
        return jsonify({'error': 'session_id is required'}), 400

    # 会话级速率限制
    if not check_rate_limit(session_id):
        return jsonify({'error': 'Rate limit exceeded for this session'}), 429

    r = redis_dao.get_connection()
    if not r.exists(f"session:{session_id}:meta"):
        return jsonify({'error': 'Invalid or expired session_id'}), 404
    target_length = int(request.form.get('target_length'))
    try:
        segments = process_single_file(session_id, redis_dao, target_length)

        summary = summarizer.process_segments(segments, prompt)  # 60秒超时
        r.setex(
            f"session:{session_id}:summary",
            int(app.config['SESSION_EXPIRE'].total_seconds()),
            summary
        )
        return jsonify({
            'session_id': session_id,
            'message': 'summarize finished'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/novel/get_author_info', methods=['GET'])
@limiter.limit(app.config['RATE_LIMIT'])
def get_author_info_endpoint():
    """根据session_id获取作者信息"""
    # 获取session_id参数
    session_id = request.form.get('session_id')
    if not session_id:
        return jsonify({"error": "缺少session_id参数"}), 400

    try:
        # 1. 从Redis获取文件元数据
        file_metadata = redis_dao.get_file_metadata(session_id)
        if not file_metadata:
            return jsonify({"error": "找不到文件元数据，session_id可能已过期"}), 404

        # 2. 从元数据中提取文件名（即书名）
        filename = file_metadata.get('filename')
        if not filename:
            return jsonify({"error": "文件元数据中缺少文件名"}), 400

        # 3. 从文件名中提取书名（去掉扩展名）
        book_title = filename.rsplit('.', 1)[0] if '.' in filename else filename

        # 4. 异步调用获取作者信息
        async def async_wrapper():
            return await get_author_info(book_title)

        # 在同步环境中运行异步函数
        author_info = asyncio.run(async_wrapper())

        # 5. 处理可能的错误
        if 'error' in author_info and author_info['error']:
            return jsonify({
                "error": "获取作者信息失败",
                "details": author_info['error']
            }), 500

        # 6. 返回作者信息
        return jsonify({
            "session_id": session_id,
            "book_title": book_title,
            "author_info": author_info
        })

    except Exception as e:
        return jsonify({"error": "服务器内部错误", "details": str(e)}), 500


@app.route('/api/novel/store_author_info', methods=['POST'])
@limiter.limit(app.config['RATE_LIMIT'])
def store_author_info():
    """
    将作者信息存储到Redis的接口
    请求体格式:
    {
      "session_id": "sess_abc123",
      "book_title": "红楼梦",
      "author_info": {
        "作者姓名": "曹雪芹",
        "生卒年份": "约1715年—约1763年",
        "国籍": "中国",
        "代表作": ["红楼梦", "废艺斋集稿", "南鹞北鸢考工志"],
        "作者背景": "曹雪芹出身清代内务府正白旗包衣世家，是江宁织造曹寅之孙...",
        "创作背景": "《红楼梦》创作于曹雪芹晚年贫困时期..."
      }
    }
    """
    try:
        # 获取请求数据
        data = request.get_json()
        if not data:
            return jsonify({"error": "请求体必须为JSON格式"}), 400

        # 验证必要字段
        required_fields = ["session_id", "book_title", "author_info"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"缺少必要字段: {field}"}), 400

        session_id = data["session_id"]
        # book_title = data["book_title"]
        author_info = data["author_info"]

        # 获取Redis连接
        conn = redis_dao.get_connection()

        expire_seconds = int(app.config['SESSION_EXPIRE'].total_seconds())

        # 存储作者信息内容（使用相同的过期时间）
        conn.setex(
            f"session:{session_id}:author",
            expire_seconds,
            json.dumps(author_info, ensure_ascii=False))

        return jsonify({
            "status": "success",
            "session_id": session_id,
            "expire_seconds": expire_seconds
        })

    except Exception as e:
        return jsonify({
            "error": "服务器内部错误",
            "details": str(e)
        }), 500


@app.route('/api/novel/create_commentary', methods=['POST'])
@limiter.limit(app.config['RATE_LIMIT'])
def create_commentary():
    """
    生成名著解说词接口
    请求格式:
    {
        "session_id": "当前会话ID",
        "config": {
            "解说词类型": "剧情解说|人物分析|主题解析...",
            "语言风格": "幽默风趣|严谨学术...",
            "目标受众": "小学生|中学生|大学生...",
            "ex_prompt": "额外的自定义要求..."
        }
    }
    """
    # 获取请求数据
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid JSON data'}), 400

    session_id = data.get('session_id')
    if not session_id:
        return jsonify({'error': 'session_id is required'}), 400

    config = data.get('config', {})
    if not config:
        return jsonify({'error': 'config is required'}), 400

    # 会话级速率限制
    if not check_rate_limit(session_id):
        return jsonify({'error': 'Rate limit exceeded for this session'}), 429

    r = redis_dao.get_connection()

    try:
        author_info_json = r.get(f"session:{session_id}:author")
        summary = r.get(f"session:{session_id}:summary")
        # 解析作者信息
        author_info = json.loads(author_info_json)

        # 2. 生成解说词prompt
        commentary_prompt = generate_commentary_prompt(config)

        # 3. 准备发送给DeepSeek的完整提示
        author_background = (
            f"作者姓名：{author_info.get('作者姓名', '未知')}\n"
            f"生卒年份：{author_info.get('生卒年份', '不详')}\n"
            f"国籍：{author_info.get('国籍', '未知')}\n"
            f"代表作：{', '.join(author_info.get('代表作', []))}\n"
            f"作者背景：{author_info.get('作者背景', '暂无信息')}\n"
            f"创作背景：{author_info.get('创作背景', '暂无信息')}"
        )

        full_prompt = (
            f"=== 作者信息 ===\n{author_background}\n\n"
            f"=== 作品内容摘要 ===\n{summary}\n\n"
            f"=== 解说要求 ===\n{commentary_prompt}\n"
            "根据内容分段返回解说词，每个分段会用于制作十秒的视频\n"
            "中间正文是剧情讲解，且解说词数量不少于一万字\n"
            "注意只输出解说词即可，不要任何额外输出\n"
        )
        print(full_prompt)

        # 4. 调用DeepSeek API (同步调用)
        client = Config.dsclient

        async def async_wrapper():
            response = await client.chat.completions.create(
                model="deepseek-reasoner",
                messages=[
                    {"role": "system", "content": "你是一位专业的文学评论家，请根据提供的信息为作品生成解说词。\n\n"},
                    {"role": "user", "content": full_prompt}
                ],
                temperature=0.7,
                max_tokens=30000
            )
            return response.choices[0].message.content

        # 在同步环境中运行异步函数
        commentary = asyncio.run(async_wrapper())

        # 更新会话元数据
        r.hset(f"session:{session_id}:meta", 'last_active', time.time())
        r.hset(f"session:{session_id}:meta", 'has_commentary', 1)

        return jsonify({
            'session_id': session_id,
            'commentary': commentary,
            'message': 'Commentary generated successfully'
        }), 200

    except Exception as e:
        app.logger.error(f"生成解说词失败: {str(e)}")
        return jsonify({
            'error': 'Failed to generate commentary',
            'details': str(e)
        }), 500


@app.route('/api/novel/remake_commentary', methods=['POST'])
@limiter.limit(app.config['RATE_LIMIT'])
def remake_commentary():
    """根据现有解说词和需求生成新的解说词"""
    # 获取请求参数
    commentary = request.form.get('commentary', '')
    requirement = request.form.get('requirement', '')

    async def async_wrapper():
        return await generate_new_commentary(commentary, requirement)

    # 验证必要参数
    if not commentary and not requirement:
        return jsonify({"error": "至少需要提供解说词或修改要求"}), 400

    try:
        # 调用DeepSeek API生成新的解说词
        new_commentary = asyncio.run(async_wrapper())
        return jsonify({
            "commentary": new_commentary,
            "status": "success",
            "model": "deepseek-chat"
        })

    except Exception as e:
        app.logger.error(f"解说词生成失败: {str(e)}")
        return jsonify({
            "error": "解说词生成失败",
            "details": str(e)
        }), 500


@app.route('/api/novel/post_commentary', methods=['POST'])
@limiter.limit(app.config['RATE_LIMIT'])
def update_commentary():
    """
    更新解说词接口
    请求格式:
    {
        "session_id": "当前会话ID",
        "9": "用户修改后的解说词内容",
    }
    """
    # 获取请求数据
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid JSON data'}), 400

    session_id = data.get('session_id')
    if not session_id:
        return jsonify({'error': 'session_id is required'}), 400

    new_commentary = data.get('commentary')
    if not new_commentary:
        return jsonify({'error': 'commentary content is required'}), 400

    # 会话级速率限制
    if not check_rate_limit(session_id):
        return jsonify({'error': 'Rate limit exceeded for this session'}), 429

    r = redis_dao.get_connection()

    try:
        # 检查会话是否存在
        if not r.exists(f"session:{session_id}:meta"):
            return jsonify({'error': 'Session not found or expired'}), 404

        # 保存新解说词
        r.setex(
            f"session:{session_id}:commentary",
            int(app.config['SESSION_EXPIRE'].total_seconds()),
            new_commentary
        )

        # 更新会话元数据
        r.hset(f"session:{session_id}:meta", 'last_active', time.time())
        r.hset(f"session:{session_id}:meta", 'is_edited', 1)

        return jsonify({
            'session_id': session_id,
            'message': 'Commentary updated successfully',
        }), 200

    except Exception as e:
        app.logger.error(f"更新解说词失败: {str(e)}")
        return jsonify({
            'error': 'Failed to update commentary',
            'details': str(e)
        }), 500


@app.route('/api/novel/create_video', methods=['POST'])
@limiter.limit(app.config['RATE_LIMIT'])
def generate_video():
    """
    生成解说视频接口
    请求格式:
    {
        "session_id": "会话ID",
        "解说语种": "中文",
        "解说声音": "zh_female_yuanqinvyou_moon_bigtts",
        "视频风格": "卡通",
        "resolution_x": 1280,
        "resolution_y": 720
    }
    文件上传:
    - background_music: 背景音乐文件
    """
    # 获取请求数据
    data = request.form.to_dict()
    if not data:
        return jsonify({'error': 'Invalid data'}), 400

    session_id = data.get('session_id')
    if not session_id:
        return jsonify({'error': 'session_id is required'}), 400

    # 会话级速率限制
    if not check_rate_limit(session_id):
        return jsonify({'error': 'Rate limit exceeded for this session'}), 429

    # 获取背景音乐文件
    bg_music_file = request.files.get('background_music')
    bg_music_path = None

    r = redis_dao.get_connection()
    try:
        # 1. 从Redis获取解说词
        commentary = r.get(f"session:{session_id}:commentary")
        if not commentary:
            return jsonify({'error': 'No commentary found for this session'}), 404

        # 处理背景音乐文件
        if bg_music_file:
            # 创建临时目录
            temp_dir = tempfile.mkdtemp()
            bg_music_path = os.path.join(temp_dir, "background_music.mp3")
            bg_music_file.save(bg_music_path)

        save_path = ""
        try:
            # 3. 处理解说词生成音频和素材
            voice_type = data.get('解说声音', "zh_male_jieshuoxiaoming_moon_bigtts")
            video_type = data.get('视频风格', "写实风格")

            # 获取分辨率，默认1280x720
            resolution_x = int(data.get('resolution_x', 1280))
            resolution_y = int(data.get('resolution_y', 720))

            save_path, elements = process_commentary(
                commentary,
                video_type,
                voice_type,
                resolution=(resolution_x, resolution_y)
            )

            # 4. 生成视频
            output_file = os.path.join(save_path, "final_video.mp4")
            video_path = create_image_based_video(
                segments=elements,
                output_file=output_file,
                resolution=(resolution_x, resolution_y),
                fps=25,
                bg_music_path=bg_music_path
            )

            # 5. 返回生成的视频文件
            response = send_file(
                video_path,
                mimetype='video/mp4',
                as_attachment=False,
                download_name=f"commentary_{session_id}.mp4"
            )

            # 6. 添加自定义头部信息
            response.headers['X-Session-ID'] = session_id
            response.headers['X-Video-Size'] = os.path.getsize(video_path)
            response.headers['X-Resolution'] = f"{resolution_x}x{resolution_y}"

            return response

        finally:
            # 7. 清理临时文件
            try:
                if os.path.exists(save_path):
                    shutil.rmtree(save_path)
                if bg_music_path and os.path.exists(bg_music_path):
                    os.remove(bg_music_path)
                    # Remove the temp directory if empty
                    temp_dir = os.path.dirname(bg_music_path)
                    if os.path.exists(temp_dir) and not os.listdir(temp_dir):
                        os.rmdir(temp_dir)
            except Exception as cleanup_error:
                app.logger.error(f"清理临时文件失败: {str(cleanup_error)}")

    except json.JSONDecodeError:
        return jsonify({'error': 'Failed to parse commentary data'}), 500
    except ValueError as ve:
        return jsonify({'error': f'Invalid resolution value: {str(ve)}'}), 400
    except Exception as e:
        app.logger.error(f"生成视频失败: {str(e)}")
        return jsonify({
            'error': 'Failed to generate video',
            'details': str(e)
        }), 500


# 新增诗歌相关接口
@app.route('/api/poetry/upload', methods=['POST'])
@limiter.limit(app.config['RATE_LIMIT'])
def upload_poetry():
    """上传诗歌并获取作者信息和翻译"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        poetry = data.get('poetry')

        if not session_id or not poetry:
            return jsonify({'error': 'session_id and poetry are required'}), 400

        # 会话级速率限制
        if not check_rate_limit(session_id):
            return jsonify({'error': 'Rate limit exceeded for this session'}), 429

        redis_dao.get_connection().setex(
            f"session:{session_id}:poetry",
            int(app.config['SESSION_EXPIRE'].total_seconds()),
            poetry
        )

        # 获取作者信息
        async def get_author_info_async(insPoetry):
            return await get_poetry_author_info(insPoetry)

        author_info = asyncio.run(get_author_info_async(poetry))

        # 获取诗歌翻译
        async def poeTranslate(text):
            client = Config.dsclient
            response = await client.chat.completions.create(
                model="deepseek-reasoner",
                messages=[
                    {"role": "system", "content": "你是一个专业的诗歌翻译家，请将以下诗歌翻译成现代白话文，清晰直白易于理解，不要出现复杂的用词"},
                    {"role": "user", "content": text}
                ],
                temperature=0.3
            )
            return response.choices[0].message.content

        trans_poetry = asyncio.run(poeTranslate(poetry))
        return jsonify({
            'session_id': session_id,
            'author_info': author_info,
            'trans_poetry': trans_poetry,
            'message': 'Poetry uploaded and processed successfully'
        }), 200

    except Exception as e:
        app.logger.error(f"Poetry upload error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/poetry/create_commentary', methods=['POST'])
@limiter.limit(app.config['RATE_LIMIT'])
def create_poetry_commentary():
    """生成诗歌解说词"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        trans_poetry = data.get('trans_poetry')
        author_info = data.get('author_info', {})
        commentary = data.get('video_config', {})
        if not all([session_id, trans_poetry, author_info]):
            return jsonify({'error': 'session_id, trans_poetry and author_info are required'}), 400

        # 会话级速率限制
        if not check_rate_limit(session_id):
            return jsonify({'error': 'Rate limit exceeded for this session'}), 429
        poetry = redis_dao.get_connection().get(f"session:{session_id}:poetry")
        # 生成解说词prompt

        commentary = asyncio.run(generate_poetry_commentary(poetry, trans_poetry, author_info, commentary))

        return jsonify({
            'session_id': session_id,
            'commentary': commentary,
            'message': 'Poetry commentary generated successfully'
        }), 200

    except Exception as e:
        app.logger.error(f"Poetry commentary error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/poetry/create_video', methods=['POST'])
@limiter.limit(app.config['RATE_LIMIT'])
def create_poetry_video():
    """生成诗歌解说视频"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        commentary = data.get('commentary')
        video_config = data.get('video_config', {})

        if not all([session_id, commentary]):
            return jsonify({'error': 'session_id and commentary are required'}), 400

        # 会话级速率限制
        if not check_rate_limit(session_id):
            return jsonify({'error': 'Rate limit exceeded for this session'}), 429

        # 处理视频配置
        voice_type = video_config.get('voice_type', 'zh_female_poetic_moon_bigtts')
        style = video_config.get('style', '水墨风格')
        bgm = video_config.get('bgm', '古典')

        # 创建临时目录
        temp_dir = os.path.join(app.config['UPLOAD_FOLDER'], f"temp_poetry_{session_id}")
        os.makedirs(temp_dir, exist_ok=True)

        try:
            # 处理解说词生成素材
            save_path, elements = process_commentary(
                commentary,
                video_type=style,
                voice_type=voice_type,
                bgm_type=bgm
            )

            # 生成视频
            output_file = os.path.join(temp_dir, "poetry_video.mp4")
            video_path = create_image_based_video(
                segments=elements,
                output_file=output_file,
                resolution=(1280, 720),
                fps=25,
            )

            # 返回视频文件
            response = send_file(
                video_path,
                mimetype='video/mp4',
                as_attachment=True,
                download_name=f"poetry_{session_id}.mp4"
            )

            response.headers['X-Session-ID'] = session_id
            response.headers['X-Video-Size'] = os.path.getsize(video_path)

            return response

        finally:
            # 清理临时文件
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
            except Exception as e:
                app.logger.error(f"Cleanup error: {str(e)}")

    except Exception as e:
        app.logger.error(f"Video generation error: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/session/<session_id>', methods=['GET'])
@limiter.limit(app.config['RATE_LIMIT'])
def get_session_status(session_id):
    """获取会话状态"""
    # 会话级速率限制
    if not check_rate_limit(session_id):
        return jsonify({'error': 'Rate limit exceeded for this session'}), 429

    r = redis_dao.get_connection()
    meta = r.hgetall(f"session:{session_id}:meta")

    if not meta:
        return jsonify({'error': 'Session not found'}), 404

    # 计算剩余时间
    ttl = r.ttl(f"session:{session_id}:meta")

    return jsonify({
        'session_id': session_id,
        'status': meta.get('status', 'unknown'),
        'created': meta.get('created'),
        'last_active': meta.get('last_active'),
        'size': meta.get('size'),
        'expires_in': ttl
    }), 200


@app.route('/api/session/<session_id>', methods=['DELETE'])
@limiter.limit(app.config['RATE_LIMIT'])
def delete_session(session_id):
    """删除会话"""
    # 会话级速率限制
    if not check_rate_limit(session_id):
        return jsonify({'error': 'Rate limit exceeded for this session'}), 429

    redis_dao.cleanup_session(session_id)
    return jsonify({'message': f'Session {session_id} deleted'}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
