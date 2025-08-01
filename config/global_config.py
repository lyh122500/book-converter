import os
from datetime import timedelta


class Config:
    # Redis configuration
    REDIS_HOST = os.getenv('REDIS_HOST', '117.72.54.227')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_DB = int(os.getenv('REDIS_DB', 0))
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)

    # Flask application configuration
    UPLOAD_FOLDER = 'temp_uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB limit
    SESSION_EXPIRE = timedelta(hours=1)  # Session expiration time
    RATE_LIMIT = "5 per second"  # Default rate limit