"""LangGraph Store 单例

跨会话长期记忆的存储后端：MySQLStore（持久化到 MySQL，重启不丢）。
"""
import logging

from app.modules.agent.store.mysql_store import MySQLStore

logger = logging.getLogger("agent.store")

_store = None


def get_store() -> MySQLStore:
    """返回全局共享的 LangGraph Store 实例"""
    global _store
    if _store is None:
        _store = MySQLStore()
        logger.info("[Store] 已初始化 MySQLStore（长期记忆）")
    return _store
