import redis
from app.core.config import settings

_redis_client = None


def get_redis():
    """获取Redis客户端 — 带重连机制"""
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5
            )
            _redis_client.ping()
            print(f"[Redis] Connected to {settings.REDIS_URL}")
        except Exception as e:
            print(f"[Redis] Connection failed: {e}")
            _redis_client = None
            raise
    return _redis_client
