import json

from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import time
import uuid
import redis
from datetime import timedelta

from config.global_config import Config
from util.preprocess import process_single_file

app = Flask(__name__)
app.config.from_object(Config)

redis_pool = redis.ConnectionPool(
    host=Config.REDIS_HOST,
    port=Config.REDIS_PORT,
    db=Config.REDIS_DB,
    password=Config.REDIS_PASSWORD,
    decode_responses=True
)

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    storage_uri=f"redis://{Config.REDIS_HOST}:{Config.REDIS_PORT}/{Config.REDIS_DB}",
    storage_options={"password": Config.REDIS_PASSWORD}
)

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


def get_redis_conn():
    """获取Redis连接"""
    return redis.Redis(connection_pool=redis_pool)


def generate_session_id():
    """生成唯一会话ID"""
    return f"sess_{uuid.uuid4().hex}"


def cleanup_session(session_id):
    """清理会话数据"""
    r = get_redis_conn()
    keys = [
        f"session:{session_id}:file",
        f"session:{session_id}:segments",
        f"session:{session_id}:meta",
        f"ratelimit:{session_id}"
    ]
    r.delete(*keys)


def check_rate_limit(session_id):
    """检查会话级别的速率限制"""
    r = get_redis_conn()
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
    r = get_redis_conn()
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
        session_id = generate_session_id()
        r = get_redis_conn()

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

    r = get_redis_conn()

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
            'content': file_content,
            'size': len(file_content)
        }

        r.setex(
            f"session:{session_id}:file",
            int(app.config['SESSION_EXPIRE'].total_seconds()),
            json.dumps(file_data)
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
        cleanup_session(session_id)
        return jsonify({'error': 'File upload failed'}), 500


@app.route('/api/novel/process', methods=['POST'])
@limiter.limit(app.config['RATE_LIMIT'])
def process_file():
    """处理文件（示例接口）"""
    session_id = request.form.get('session_id')
    if not session_id:
        return jsonify({'error': 'session_id is required'}), 400

    # 会话级速率限制
    if not check_rate_limit(session_id):
        return jsonify({'error': 'Rate limit exceeded for this session'}), 429

    r = get_redis_conn()
    if not r.exists(f"session:{session_id}:meta"):
        return jsonify({'error': 'Invalid or expired session_id'}), 404
    target_length = int(request.form.get('target_length'))
    try:
        process_single_file(session_id, target_length, r)
        return jsonify({
            'session_id': session_id,
            'status': 'process finished',
            'message': 'File processing initiated'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500





@app.route('/api/session/<session_id>', methods=['GET'])
@limiter.limit(app.config['RATE_LIMIT'])
def get_session_status(session_id):
    """获取会话状态"""
    # 会话级速率限制
    if not check_rate_limit(session_id):
        return jsonify({'error': 'Rate limit exceeded for this session'}), 429

    r = get_redis_conn()
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

    cleanup_session(session_id)
    return jsonify({'message': f'Session {session_id} deleted'}), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
