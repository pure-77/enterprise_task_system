"""P3: LangGraph checkpointer 工厂

按 AGENT_CHECKPOINTER 选择实现：
- memory（默认/回退）：InMemorySaver 进程内单例。
  开发环境足够；进程重启丢图状态，但 runner 会从 MySQL 历史重新注入，对话不断。
- redis：AsyncRedisSaver（langgraph-checkpoint-redis）。
  **需要 Redis Stack（RediSearch + RedisJSON 模块）**，vanilla Redis 5.0 不可用。
  初始化失败时告警并回退 memory，保证服务可启动。

生命周期：get_checkpointer() 惰性初始化全局单例；close_checkpointer() 在应用关闭时调用。
"""
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger("agent.graph.checkpointer")

_saver = None                    # 全局共享的 checkpointer 实例
_saver_cm = None                 # redis saver 的 async context manager（关闭时用）
_lock = None                     # asyncio.Lock，惰性创建（避免模块导入时绑定事件循环）


def _memory_saver():
    from langgraph.checkpoint.memory import InMemorySaver
    return InMemorySaver()


async def _redis_saver():
    """创建 Redis checkpointer 并完成索引初始化（asetup）；失败抛异常由调用方回退"""
    from langgraph.checkpoint.redis.aio import AsyncRedisSaver

    global _saver_cm
    _saver_cm = AsyncRedisSaver.from_conn_string(settings.REDIS_URL)
    saver = await _saver_cm.__aenter__()
    await saver.asetup()  # 创建 RediSearch 索引；vanilla Redis 在此抛 unknown command
    return saver


async def get_checkpointer():
    """返回共享 checkpointer（惰性初始化，线程/协程安全）"""
    global _saver, _lock
    if _saver is not None:
        return _saver

    import asyncio
    if _lock is None:
        _lock = asyncio.Lock()
    async with _lock:
        if _saver is not None:
            return _saver

        backend = (settings.AGENT_CHECKPOINTER or "memory").lower()
        if backend == "redis":
            try:
                _saver = await _redis_saver()
                logger.info("[Checkpointer] 使用 Redis checkpointer（AsyncRedisSaver）")
            except Exception as e:
                logger.warning(
                    f"[Checkpointer] Redis checkpointer 初始化失败（需要 Redis Stack 模块），"
                    f"回退 memory: {e}"
                )
                _saver = _memory_saver()
        else:
            _saver = _memory_saver()
            logger.info("[Checkpointer] 使用 InMemorySaver（AGENT_CHECKPOINTER=memory）")
    return _saver


async def close_checkpointer() -> None:
    """应用关闭时释放资源（redis saver 的连接）"""
    global _saver, _saver_cm
    if _saver_cm is not None:
        try:
            await _saver_cm.__aexit__(None, None, None)
        except Exception as e:
            logger.warning(f"[Checkpointer] 关闭异常（忽略）: {e}")
        _saver_cm = None
    _saver = None
