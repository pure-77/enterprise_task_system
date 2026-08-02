import redis
from app.core.config import settings

_redis_client = None


def get_redis():
    """获取Redis客户端 - 面试考点：懒加载，避免fork时连接损坏"""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5
        )
    return _redis_client
