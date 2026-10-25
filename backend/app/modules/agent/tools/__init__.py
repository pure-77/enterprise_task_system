"""Agent 工具组 — 自动注册入口

所有 tool 模块都用 try-except 包裹，某个模块的 CRUD 签名变化不会导致整个后端启动失败。
"""
import logging

logger = logging.getLogger("agent.tools")


def _safe_register(name: str, func):
    """安全注册：单个模块失败不影响其他"""
    try:
        func()
        logger.info(f"[Agent] ✅ {name} 注册成功")
    except Exception as e:
        logger.warning(f"[Agent] ⚠️ {name} 注册跳过（可能 CRUD 签名不匹配）: {e}")


def register_all_tools():
    """注册所有模块的 tools 到 ToolRegistry"""

    # Phase 1 — 已验证
    from app.modules.agent.tools.task_tools import register_task_tools
    from app.modules.agent.tools.calendar_tools import register_calendar_tools

    _safe_register("task", register_task_tools)
    _safe_register("calendar", register_calendar_tools)

    # Phase 2 — 新增模块
    from app.modules.agent.tools.im_tools import register_im_tools
    from app.modules.agent.tools.notification_tools import register_notification_tools, register_announcement_tools
    from app.modules.agent.tools.attendance_tools import register_attendance_tools
    from app.modules.agent.tools.misc_tools import register_approval_tools, register_statistics_tools, register_org_tools, register_file_tools
    from app.modules.agent.tools.summary_tools import register_summary_tools
    from app.modules.agent.tools.knowledge_tools import register_knowledge_tools

    _safe_register("im", register_im_tools)
    _safe_register("notification", register_notification_tools)
    _safe_register("announcement", register_announcement_tools)
    _safe_register("attendance", register_attendance_tools)
    _safe_register("approval", register_approval_tools)
    _safe_register("statistics", register_statistics_tools)
    _safe_register("org", register_org_tools)
    _safe_register("file", register_file_tools)
    # Phase 3 — 数据洞察（一键总结 + 图表生成）
    _safe_register("summary", register_summary_tools)
    # Phase 4 — 知识库语义检索（RAG）
    _safe_register("knowledge", register_knowledge_tools)

    logger.info("[Agent] 工具注册流程完成 ✅")
