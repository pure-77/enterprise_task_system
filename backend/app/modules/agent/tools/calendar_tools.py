"""Agent 工具组 — 日程日历 Tools"""
import json
import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.user import User
from app.modules.calendar.crud import event_crud
from app.modules.calendar.schemas import EventCreate
from app.core.permissions import get_workspace_member

logger = logging.getLogger("agent.tools.calendar")


# ============================================================
# Calendar 模块的 3 个核心 Tool
# ============================================================

def _schema_list_events() -> dict:
    return {
        "name": "list_calendar_events",
        "description": "查询日程/会议列表。可指定 workspace 和时间范围，默认查询当前月到下月。",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {
                    "type": "integer",
                    "description": "workspace ID（可选）",
                },
                "start_date": {
                    "type": "string",
                    "description": "开始日期，格式 YYYY-MM-DD（可选，默认本月第一天）",
                },
                "end_date": {
                    "type": "string",
                    "description": "结束日期，格式 YYYY-MM-DD（可选，默认 42 天后）",
                },
                "keyword": {
                    "type": "string",
                    "description": "按标题/描述搜索（可选）",
                },
            },
            "required": [],
        },
    }


def _handler_list_events(
    workspace_id: int = None,
    start_date: str = None,
    end_date: str = None,
    keyword: str = None,
    context: dict = None,
) -> str:
    """查询日程的 handler"""
    user: User = context["user"]
    db: Session = SessionLocal()

    try:
        # workspace_id 兜底
        if workspace_id is None:
            workspace_id = context.get("workspace_id")

        # 权限收口：必须是该空间成员才能查询空间日程
        if workspace_id:
            get_workspace_member(workspace_id, user.id, db)

        if start_date:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        else:
            start_dt = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        if end_date:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        else:
            end_dt = start_dt + timedelta(days=42)

        events = event_crud.get_events(db, workspace_id, user.id, start_dt, end_dt)

        result_items = []
        for e in events:
            # e 可能是 dict 或 model
            if isinstance(e, dict):
                result_items.append({
                    "id": e.get("id"),
                    "title": e.get("title"),
                    "start_time": e.get("start_time"),
                    "end_time": e.get("end_time"),
                    "location": e.get("location"),
                })
            else:
                result_items.append({
                    "id": e.id,
                    "title": e.title,
                    "start_time": e.start_time.isoformat() if e.start_time else None,
                    "end_time": e.end_time.isoformat() if e.end_time else None,
                    "location": e.location,
                })

        # 如果有关键词，在 Python 层再过滤一次
        if keyword:
            result_items = [
                e for e in result_items
                if keyword.lower() in (e["title"] or "").lower()
                or keyword.lower() in (e.get("location") or "").lower()
            ]

        return json.dumps({
            "success": True,
            "count": len(result_items),
            "range": f"{start_dt.strftime('%Y-%m-%d')} ~ {end_dt.strftime('%Y-%m-%d')}",
            "items": result_items,
        }, ensure_ascii=False)
    except Exception as e:
        logger.exception("查询日程失败")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    finally:
        db.close()


# ------------------------------------------------------------

def _schema_create_event() -> dict:
    return {
        "name": "create_calendar_event",
        "description": "创建日程/会议。只需提供标题和开始时间，其他参数自动补全。",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "日程/会议标题",
                },
                "start_time": {
                    "type": "string",
                    "description": "开始时间，格式 YYYY-MM-DD HH:mm",
                },
                "end_time": {
                    "type": "string",
                    "description": "结束时间，格式 YYYY-MM-DD HH:mm（可选，默认开始时间 +1 小时）",
                },
                "description": {
                    "type": "string",
                    "description": "详细描述（可选）",
                },
                "location": {
                    "type": "string",
                    "description": "地点（可选）",
                },
                "is_all_day": {
                    "type": "boolean",
                    "description": "是否全天事件（可选，默认 false）",
                },
            },
            "required": ["title", "start_time"],
        },
    }


def _handler_create_event(
    title: str,
    start_time: str,
    end_time: str = None,
    description: str = None,
    location: str = None,
    is_all_day: bool = False,
    workspace_id: int = None,
    context: dict = None,
) -> str:
    """创建日程的 handler"""
    user: User = context["user"]
    db: Session = SessionLocal()

    try:
        # workspace_id 兜底（个人模式 0 不支持日程，必须指定工作空间）
        if workspace_id is None:
            workspace_id = context.get("workspace_id")
        ws = workspace_id if (workspace_id and workspace_id > 0) else None
        if ws is None:
            return json.dumps({"success": False, "error": "创建日程需要指定工作空间（个人模式不支持日程）"}, ensure_ascii=False)

        # 权限收口：必须是该空间成员
        get_workspace_member(ws, user.id, db)

        # 时间解析
        try:
            start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M")
        except ValueError:
            return json.dumps({"success": False, "error": f"开始时间格式错误: {start_time}，应为 YYYY-MM-DD HH:mm"}, ensure_ascii=False)

        if end_time:
            try:
                end_dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M")
            except ValueError:
                end_dt = start_dt + timedelta(hours=1)
        else:
            end_dt = start_dt + timedelta(hours=1)

        event = event_crud.create(
            db, ws, user.id,
            title=title,
            start_time=start_dt,
            end_time=end_dt,
            description=description,
            location=location,
            is_all_day=is_all_day,
        )
        return json.dumps({
            "success": True,
            "event_id": event.id,
            "title": event.title,
            "start": start_dt.strftime("%Y-%m-%d %H:%M"),
            "end": end_dt.strftime("%Y-%m-%d %H:%M"),
            "message": f"日程「{event.title}」已创建 📅",
        }, ensure_ascii=False)
    except Exception as e:
        logger.exception("创建日程失败")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    finally:
        db.close()


# ------------------------------------------------------------

def _schema_delete_event() -> dict:
    return {
        "name": "delete_calendar_event",
        "description": "删除指定日程/会议（只能删除自己创建的）。需要日程 ID。",
        "parameters": {
            "type": "object",
            "properties": {
                "event_id": {
                    "type": "integer",
                    "description": "日程 ID",
                },
            },
            "required": ["event_id"],
        },
    }


def _handler_delete_event(
    event_id: int,
    context: dict = None,
) -> str:
    """删除日程的 handler"""
    user: User = context["user"]
    db: Session = SessionLocal()

    try:
        ev = event_crud.get_by_id(db, event_id)
        if not ev:
            return json.dumps({"success": False, "error": f"日程 ID {event_id} 不存在"}, ensure_ascii=False)

        # 权限收口：必须是该空间成员，且仅创建者可删除
        if ev.workspace_id:
            get_workspace_member(ev.workspace_id, user.id, db)
        if ev.created_by != user.id:
            return json.dumps({"success": False, "error": "只能删除自己创建的日程"}, ensure_ascii=False)

        title = ev.title
        event_crud.delete(db, event_id)
        return json.dumps({
            "success": True,
            "message": f"日程「{title}」已删除",
        }, ensure_ascii=False)
    except Exception as e:
        logger.exception("删除日程失败")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    finally:
        db.close()


# ============================================================
# 自动注册入口
# ============================================================

def register_calendar_tools():
    """将 calendar 模块的所有工具注册到 ToolRegistry"""
    from app.modules.agent.tool_registry import ToolRegistry

    ToolRegistry.register("list_calendar_events", _schema_list_events(), _handler_list_events, group="calendar")
    ToolRegistry.register("create_calendar_event", _schema_create_event(), _handler_create_event, group="calendar")
    ToolRegistry.register("delete_calendar_event", _schema_delete_event(), _handler_delete_event, group="calendar")

    logger.info("[Agent] calendar 模块 3 个工具已注册")
