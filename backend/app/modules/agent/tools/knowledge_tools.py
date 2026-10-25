"""Agent 工具组 — 知识库语义检索（RAG，方案 7）

search_knowledge：从 Chroma 语义检索工作区文件 / 公告 / 当前用户参与的聊天记录，
返回带来源引用（citation）的片段，由 LLM 在自然语言回答中标注引用。

权限与隔离：
- 个人空间（workspace_id=0）→ 文件/公告/会话均不存在，直接返回友好提示
- 团队空间 → get_workspace_member 校验成员资格（非成员抛权限异常）
- IM 越权收口点 = conversation_members（user_id + is_active）关联 conversations.workspace_id
  得到当前用户在该空间参与的所有会话 ID，Chroma where 过滤 conversation_id ∈ conv_ids
"""
import json
import logging

from app.core.config import settings
from app.db.session import SessionLocal

logger = logging.getLogger("agent.tools.knowledge")

_SOURCE_NAMES = {"file": "文件", "announcement": "公告", "im": "聊天记录"}


def _schema_search_knowledge() -> dict:
    return {
        "name": "search_knowledge",
        "description": ("从知识库语义检索资料（工作区文件、公告、当前用户参与的聊天记录），"
                        "返回带来源引用的片段。"
                        "用户问「文档里/公告里/聊天里提到过什么」「有没有相关规定」「帮我查一下资料」"
                        "等非结构化内容问题时调用；结构化的任务/日程/统计查询不要用本工具。"),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "检索问题或关键词"},
                "top_k": {"type": "integer", "description": "返回片段数，默认 6，最大 10"},
                "source_types": {"type": "array",
                                 "items": {"type": "string", "enum": ["file", "announcement", "im"]},
                                 "description": "限定来源类型，缺省为全部"},
            },
            "required": ["query"],
        },
    }


def _get_conv_ids(db, ws: int, user_id: int) -> list:
    """当前用户在该空间参与的所有会话 ID（IM 越权的唯一收口点）"""
    from app.modules.im.models import ConversationMember, Conversation
    rows = db.query(ConversationMember.conversation_id).join(
        Conversation, Conversation.id == ConversationMember.conversation_id
    ).filter(
        ConversationMember.user_id == user_id,
        ConversationMember.is_active == True,
        Conversation.workspace_id == ws,
    ).all()
    return [r[0] for r in rows]


def _build_where(ws: int, conv_ids: list, source_types):
    """构造 Chroma where 过滤（注意：$or 列表不能为空）"""
    clauses = [
        {"workspace_id": {"$eq": int(ws)}},
        {"is_active": {"$eq": True}},
    ]

    types = [s for s in (source_types or []) if s in _SOURCE_NAMES]

    if not types:
        # 全部来源：文件/公告 + 用户参与的 IM 会话
        if conv_ids:
            clauses.append({"$or": [
                {"source_type": {"$in": ["file", "announcement"]}},
                {"$and": [{"source_type": {"$eq": "im"}},
                          {"conversation_id": {"$in": conv_ids}}]},
            ]})
        else:
            clauses.append({"source_type": {"$in": ["file", "announcement"]}})
    elif "im" in types:
        # 指定来源含 im：im 部分仍必须限定在用户参与的会话内
        others = [s for s in types if s != "im"]
        or_branch = [{"source_type": {"$in": others}}] if others else []
        if conv_ids:
            or_branch.append({"$and": [{"source_type": {"$eq": "im"}},
                                       {"conversation_id": {"$in": conv_ids}}]})
        if not or_branch:
            return None  # 只选了 im 且无参与会话 → 无可查内容
        clauses.append({"$or": or_branch})
    else:
        # 仅文件/公告
        clauses.append({"source_type": {"$in": types}})

    return {"$and": clauses}


def _handler_search_knowledge(query: str, top_k: int = None, source_types: list = None,
                              context: dict = None) -> str:
    db = SessionLocal()
    try:
        ctx = context or {}
        user = ctx.get("user")
        user_id = getattr(user, "id", None)
        ws = ctx.get("workspace_id")
        ws = ws if (ws and int(ws) > 0) else None

        # 个人空间：无文件/公告/会话（三者的 workspace_id 均 nullable=False）
        if ws is None or not user_id:
            return json.dumps({"success": True, "count": 0, "items": [],
                               "message": "个人空间暂无知识库内容，请切换到团队空间后再检索资料"},
                              ensure_ascii=False)

        # 成员资格校验（非成员直接抛权限异常，由 ToolRegistry 包装为失败结果）
        from app.core.permissions import get_workspace_member
        get_workspace_member(int(ws), user_id, db)

        conv_ids = _get_conv_ids(db, int(ws), user_id)
        where = _build_where(int(ws), conv_ids, source_types)
        if where is None:
            return json.dumps({"success": True, "count": 0, "items": [],
                               "message": "你没有参与该空间的任何聊天会话，无可检索的聊天记录"},
                              ensure_ascii=False)

        try:
            from app.modules.knowledge.vector_store import get_collection
            k = min(max(1, int(top_k or settings.KB_TOP_K)), 10)
            try:
                res = get_collection().query(
                    query_texts=[query], n_results=k, where=where,
                    include=["documents", "metadatas", "distances"])
            except Exception:
                # n_results 大于命中集时的兜底重试
                res = get_collection().query(
                    query_texts=[query], n_results=min(k, 3), where=where,
                    include=["documents", "metadatas", "distances"])
        except Exception as e:
            logger.error(f"[KB] 检索失败 ws={ws}: {e}")
            return json.dumps({"success": False, "count": 0, "items": [],
                               "error": f"知识库检索失败: {type(e).__name__}: {e}"},
                              ensure_ascii=False)

        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]

        items = []
        for doc_, meta, dist in zip(docs, metas, dists):
            meta = meta or {}
            st = meta.get("source_type", "")
            title = meta.get("title") or ""
            items.append({
                "text": (doc_ or "")[:settings.KB_SNIPPET_LEN],
                "title": title,
                "source_type": st,
                "source_id": meta.get("source_id"),
                "conversation_id": meta.get("conversation_id"),
                # cosine 距离 → 相似度（越大越相关）
                "score": round(1 - (dist if dist is not None else 1.0), 4),
                "citation": f"〔{_SOURCE_NAMES.get(st, st)}《{title}》#{meta.get('source_id')}〕",
            })

        msg = (f"知识库命中 {len(items)} 条相关片段" if items
               else "知识库中没有找到相关内容")
        return json.dumps({"success": True, "count": len(items), "items": items,
                           "message": msg}, ensure_ascii=False)
    finally:
        db.close()


def register_knowledge_tools():
    from app.modules.agent.tool_registry import ToolRegistry

    ToolRegistry.register("search_knowledge", _schema_search_knowledge(),
                          _handler_search_knowledge, group="knowledge")
