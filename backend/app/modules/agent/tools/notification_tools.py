"""Agent 工具组 — 通知 + 公告 Tools"""
import json
import logging

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.user import User

logger = logging.getLogger("agent.tools.notification")


# ==================== Notification ====================

def _schema_list_notifications() -> dict:
    return {
        "name": "list_notifications",
        "description": "获取当前用户的通知列表（系统通知、任务提醒、审批通知等）。",
        "parameters": {
            "type": "object",
            "properties": {
                "unread_only": {"type": "boolean", "description": "是否只看未读", "default": False},
                "limit": {"type": "integer", "description": "条数，默认 20", "default": 20},
            },
        },
    }


def _handler_list_notifications(unread_only: bool = False, limit: int = 20, context: dict = None) -> str:
    user: User = context["user"]
    db = SessionLocal()
    try:
        from app.modules.notification.crud import notification_crud
        limit = min(limit, 50)
        page_size = limit
        page = 1
        result = notification_crud.get_list(db, user_id=user.id, is_read=(False if unread_only else None), page=page, page_size=page_size)
        items = result.get("items", []) if isinstance(result, dict) else []
        unread = result.get("unread_count", 0) if isinstance(result, dict) else 0
        return json.dumps({"success": True, "count": len(items), "unread_count": unread, "items": items}, ensure_ascii=False, default=str)
    except Exception as e:
        logger.exception("获取通知失败")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    finally:
        db.close()


def _schema_mark_notification_read() -> dict:
    return {
        "name": "mark_notification_read",
        "description": "将一条通知标记为已读。",
        "parameters": {
            "type": "object",
            "properties": {
                "notification_id": {"type": "integer", "description": "通知 ID"},
            },
            "required": ["notification_id"],
        },
    }


def _handler_mark_read(notification_id: int, context: dict = None) -> str:
    user: User = context["user"]
    db = SessionLocal()
    try:
        from app.modules.notification.crud import notification_crud
        notification_crud.mark_read(db, notif_id=notification_id, user_id=user.id)
        return json.dumps({"success": True, "message": f"通知已标记已读 ✅"}, ensure_ascii=False)
    except Exception as e:
        logger.exception("标记已读失败")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    finally:
        db.close()


# ==================== Announcement ====================

def _schema_list_announcements() -> dict:
    return {
        "name": "list_announcements",
        "description": "获取公告列表（全部/指定 workspace）。",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "integer", "description": "workspace ID（可选）"},
                "limit": {"type": "integer", "description": "条数，默认 10", "default": 10},
            },
        },
    }


def _handler_list_announcements(workspace_id: int = None, limit: int = 10, context: dict = None) -> str:
    db = SessionLocal()
    try:
        from app.modules.announcement.crud import announcement_crud
        limit = min(limit, 30)
        items = announcement_crud.get_list(db, workspace_id=workspace_id, limit=limit)
        result = []
        for a in items or []:
            if isinstance(a, dict):
                result.append({"id": a.get("id"), "title": a.get("title"), "content": (a.get("content") or "")[:100]})
            else:
                result.append({"id": a.id, "title": getattr(a, "title", ""), "content": (getattr(a, "content", "") or "")[:100]})
        return json.dumps({"success": True, "count": len(result), "items": result}, ensure_ascii=False, default=str)
    except Exception as e:
        logger.exception("获取公告失败")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    finally:
        db.close()


def register_notification_tools():
    from app.modules.agent.tool_registry import ToolRegistry
    ToolRegistry.register("list_notifications", _schema_list_notifications(), _handler_list_notifications, group="notification")
    ToolRegistry.register("mark_notification_read", _schema_mark_notification_read(), _handler_mark_read, group="notification")
    logger.info("[Agent] notification 模块 2 个工具已注册")


def register_announcement_tools():
    from app.modules.agent.tool_registry import ToolRegistry
    ToolRegistry.register("list_announcements", _schema_list_announcements(), _handler_list_announcements, group="announcement")
    logger.info("[Agent] announcement 模块 1 个工具已注册")
