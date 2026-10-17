"""Agent 工具组 — 考勤 Tools"""
import json
import logging
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.user import User
from app.core.permissions import get_workspace_member

logger = logging.getLogger("agent.tools.attendance")


def _get_rule_id(db: Session, workspace_id: int):
    """通过 workspace_id 获取考勤 rule_id（取第一条激活的）"""
    from app.modules.attendance.crud import attendance_crud
    rules = attendance_crud.get_rules(db, workspace_id=workspace_id)
    if not rules:
        return None
    return rules[0].id


def _schema_check_in() -> dict:
    return {
        "name": "attendance_check_in",
        "description": "上班打卡。需 workspace 已配置考勤规则。",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "integer", "description": "workspace ID（可选，从上下文取）"},
                "remark": {"type": "string", "description": "备注（可选）"},
            },
        },
    }


def _handler_check_in(workspace_id: int = None, remark: str = None, context: dict = None) -> str:
    user: User = context["user"]
    db: Session = SessionLocal()
    try:
        if workspace_id is None:
            workspace_id = context.get("workspace_id")
        ws = workspace_id if (workspace_id and workspace_id > 0) else None
        if ws is None:
            return json.dumps({"success": False, "error": "打卡需要在工作空间中进行（个人模式不支持考勤）"}, ensure_ascii=False)
        # 权限收口：必须是该空间成员
        get_workspace_member(ws, user.id, db)
        from app.modules.attendance.crud import attendance_crud
        rule_id = _get_rule_id(db, ws)
        if not rule_id:
            return json.dumps({"success": False, "error": f"workspace {ws} 未配置考勤规则，请先在设置中创建"}, ensure_ascii=False)
        record = attendance_crud.check_in(db, user_id=user.id, rule_id=rule_id, remark=remark)
        return json.dumps({
            "success": True,
            "record_id": record.id,
            "check_in_time": str(record.check_in_time)[:16] if record.check_in_time else None,
            "message": "上班打卡成功 ✅",
        }, ensure_ascii=False)
    except Exception as e:
        logger.exception("上班打卡失败")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    finally:
        db.close()


def _schema_check_out() -> dict:
    return {
        "name": "attendance_check_out",
        "description": "下班打卡。",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "integer", "description": "workspace ID（可选）"},
                "remark": {"type": "string", "description": "备注（可选）"},
            },
        },
    }


def _handler_check_out(workspace_id: int = None, remark: str = None, context: dict = None) -> str:
    user: User = context["user"]
    db: Session = SessionLocal()
    try:
        if workspace_id is None:
            workspace_id = context.get("workspace_id")
        ws = workspace_id if (workspace_id and workspace_id > 0) else None
        if ws is None:
            return json.dumps({"success": False, "error": "打卡需要在工作空间中进行（个人模式不支持考勤）"}, ensure_ascii=False)
        # 权限收口：必须是该空间成员
        get_workspace_member(ws, user.id, db)
        from app.modules.attendance.crud import attendance_crud
        rule_id = _get_rule_id(db, ws)
        if not rule_id:
            return json.dumps({"success": False, "error": f"workspace {ws} 未配置考勤规则"}, ensure_ascii=False)
        record = attendance_crud.check_out(db, user_id=user.id, rule_id=rule_id, remark=remark)
        work_minutes = None
        if record.check_in_time and record.check_out_time:
            work_minutes = int((record.check_out_time - record.check_in_time).total_seconds() / 60)
        return json.dumps({
            "success": True,
            "record_id": record.id,
            "check_out_time": str(record.check_out_time)[:16],
            "work_minutes": work_minutes,
            "message": "下班打卡成功 ✅",
        }, ensure_ascii=False)
    except Exception as e:
        logger.exception("下班打卡失败")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    finally:
        db.close()


def _schema_get_attendance_stats() -> dict:
    return {
        "name": "attendance_stats",
        "description": "查询考勤统计（本月出勤天数、迟到次数等）。",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "integer", "description": "workspace ID（可选）"},
            },
        },
    }


def _handler_attendance_stats(workspace_id: int = None, context: dict = None) -> str:
    user: User = context["user"]
    db: Session = SessionLocal()
    try:
        if workspace_id is None:
            workspace_id = context.get("workspace_id")
        ws = workspace_id if (workspace_id and workspace_id > 0) else None
        from app.modules.attendance.crud import attendance_crud
        rule_id = _get_rule_id(db, ws) if ws else None
        if not rule_id:
            return json.dumps({"success": False, "error": "未找到考勤规则（个人模式或无规则的空间不支持考勤统计）"}, ensure_ascii=False)
        # 权限收口：必须是该空间成员
        get_workspace_member(ws, user.id, db)
        stats = attendance_crud.get_my_stats(db, user_id=user.id, rule_id=rule_id)
        return json.dumps({"success": True, "stats": stats}, ensure_ascii=False, default=str)
    except Exception as e:
        logger.exception("考勤统计失败")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    finally:
        db.close()


def register_attendance_tools():
    from app.modules.agent.tool_registry import ToolRegistry
    ToolRegistry.register("attendance_check_in", _schema_check_in(), _handler_check_in, group="attendance")
    ToolRegistry.register("attendance_check_out", _schema_check_out(), _handler_check_out, group="attendance")
    ToolRegistry.register("attendance_stats", _schema_get_attendance_stats(), _handler_attendance_stats, group="attendance")
    logger.info("[Agent] attendance 模块 3 个工具已注册")
