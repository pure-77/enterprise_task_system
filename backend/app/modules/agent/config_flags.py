"""Agent 引擎开关读取（迁移方案 §13 灰度与回滚）

AGENT_ENGINE=legacy    → 原自研主循环（legacy/service.py）
AGENT_ENGINE=langgraph → LangGraph 编排（graph/）

回滚 = 改环境变量，无需动数据库（checkpointer 数据与业务表隔离）。
"""
from app.core.config import settings


def get_engine() -> str:
    """返回当前生效的引擎名，非法值安全回退到 legacy"""
    engine = (settings.AGENT_ENGINE or "legacy").strip().lower()
    if engine not in ("legacy", "langgraph"):
        return "legacy"
    return engine
