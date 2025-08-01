import json
import uuid
from typing import Optional, Dict, List, Union
import redis

from config.global_config import Config


class RedisDao:
    def __init__(self):
        """Initialize with a Redis connection pool"""
        redis_pool = redis.ConnectionPool(
            host=Config.REDIS_HOST,
            port=Config.REDIS_PORT,
            db=Config.REDIS_DB,
            password=Config.REDIS_PASSWORD,
            decode_responses=True
        )
        self._conn = redis.Redis(connection_pool=redis_pool)

    def get_connection(self):
        return self._conn

    @staticmethod
    def generate_session_id() -> str:
        """Generate unique session ID"""
        return f"sess_{uuid.uuid4().hex}"

    def cleanup_session(self, session_id: str) -> None:
        """Clean up session data"""
        keys = [
            f"session:{session_id}:file",
            f"session:{session_id}:summary",
            f"session:{session_id}:meta",
            f"session:{session_id}:content",
            f"ratelimit:{session_id}"
        ]
        self._conn.delete(*keys)

    def get_file_metadata(self, session_id: str) -> Optional[Dict]:
        """
        Get file metadata
        Returns: {
            'filename': str,
            'content_type': str,
            'size': int
        }
        """
        file_data =  self._conn.get(f"session:{session_id}:file")
        if not file_data:
            return None
        return json.loads(file_data)

    def get_file_content(self, session_id: str):
        """Get file original content"""
        file_data = self._conn.get(f"session:{session_id}:content")
        if not file_data:
            raise ValueError("FileContent not found in Redis storage")
        return file_data

    def get_processed_result(self, session_id: str) -> Optional[Dict]:
        """
        Get processed complete result
        Returns: {
            'book_title': str,
            'segment_count': int,
            'processed_text': str,
            'segments': List[str]
        }
        """
        result = self._conn.get(f"session:{session_id}:summary")
        return json.loads(result) if result else None

    def get_session_meta(self, session_id: str) -> Dict:
        """Get session metadata"""
        return self._conn.hgetall(f"session:{session_id}:meta")
