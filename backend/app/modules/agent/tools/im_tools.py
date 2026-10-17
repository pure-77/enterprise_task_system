"""Agent 工具组 — 即时通讯 IM Tools"""
import json
import logging

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.user import User
from app.modules.im.crud import conversation_crud, message_crud
from app.modules.im.models import MessageType

logger = logging.getLogger("agent.tools.im")


def _schema_send_message() -> dict:
    return {
        "name": "send_im_message",
        "description": "发送 IM 消息给某个会话。需要会话 ID 和消息内容。",
        "parameters": {
            "type": "object",
            "properties": {
                "conv_id": {"type": "integer", "description": "会话 ID"},
                "content": {"type": "string", "description": "消息文本内容"},
                "type": {"type": "string", "enum": ["text", "image", "file"], "description": "消息类型，默认 text"},
            },
            "required": ["conv_id", "content"],
        },
    }


def _handler_send_im_message(conv_id: int, content: str, type: str = "text", context: dict = None) -> str:
    user: User = context["user"]
    db = SessionLocal()
    try:
        # 权限收口：必须是该会话成员，否则可向任意会话发消息
        conversation_crud.get_member(db, conv_id, user.id)
        msg_type = MessageType(type) if type in MessageType._value2member_map_ else MessageType.TEXT
        msg = message_crud.send(db, conv_id=conv_id, sender_id=user.id, content=content, msg_type=msg_type)
        return json.dumps({"success": True, "message_id": msg.id, "message": f"消息已发送 ✅"}, ensure_ascii=False)
    except Exception as e:
        logger.exception("发送 IM 消息失败")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    finally:
        db.close()


def _schema_list_conversations() -> dict:
    return {
        "name": "list_im_conversations",
        "description": "获取当前用户的 IM 会话列表。",
        "parameters": {"type": "object", "properties": {}},
    }


def _handler_list_conversations(workspace_id: int = None, context: dict = None) -> str:
    user: User = context["user"]
    db = SessionLocal()
    try:
        if workspace_id is None:
            workspace_id = context.get("workspace_id")
        convs = conversation_crud.get_list(db, user_id=user.id, workspace_id=workspace_id)
        items = []
        for c in convs or []:
            if isinstance(c, dict):
                items.append({"id": c.get("id"), "name": c.get("name"), "type": c.get("type")})
            else:
                items.append({"id": c.id, "name": getattr(c, "name", None) or str(c.id), "type": getattr(c, "type", None)})
        return json.dumps({"success": True, "count": len(items), "items": items[:20]}, ensure_ascii=False)
    except Exception as e:
        logger.exception("获取会话列表失败")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    finally:
        db.close()


def _schema_list_messages() -> dict:
    return {
        "name": "list_im_messages",
        "description": "获取某个会话的历史消息。需要会话 ID。",
        "parameters": {
            "type": "object",
            "properties": {
                "conv_id": {"type": "integer", "description": "会话 ID"},
                "limit": {"type": "integer", "description": "消息条数，默认 20", "default": 20},
            },
            "required": ["conv_id"],
        },
    }


def _handler_list_messages(conv_id: int, limit: int = 20, context: dict = None) -> str:
    user: User = context["user"]
    db = SessionLocal()
    try:
        # 权限收口：必须是该会话成员，否则可读任意会话消息
        conversation_crud.get_member(db, conv_id, user.id)
        # CRUD 真实签名: get_messages(db, conv_id, user_id, page, page_size, before_id)
        result = message_crud.get_messages(db, conv_id=conv_id, user_id=user.id, page_size=min(limit, 50))
        raw = result.get("items", []) if isinstance(result, dict) else []
        items = []
        for m in raw:
            items.append({
                "id": m.get("id"),
                "sender_id": m.get("sender_id"),
                "sender": m.get("sender_name"),
                "content": (m.get("content") or "")[:100],
                "time": str(m.get("created_at", ""))[:16],
            })
        return json.dumps({"success": True, "conv_id": conv_id, "count": len(items), "items": items}, ensure_ascii=False)
    except Exception as e:
        logger.exception("获取消息列表失败")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    finally:
        db.close()


def register_im_tools():
    from app.modules.agent.tool_registry import ToolRegistry
    ToolRegistry.register("send_im_message", _schema_send_message(), _handler_send_im_message, group="im")
    ToolRegistry.register("list_im_conversations", _schema_list_conversations(), _handler_list_conversations, group="im")
    ToolRegistry.register("list_im_messages", _schema_list_messages(), _handler_list_messages, group="im")
    logger.info("[Agent] im 模块 3 个工具已注册")
