"""知识库模块 — 运维接口（重建索引 / 状态查询）

BackgroundTasks 无持久化与重试，索引失败（status='pending'/'failed'）的文档
通过 POST /rebuild 全量重新投递补偿；GET /stats 用于观测索引健康度。
"""
import logging

from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user
from app.core.permissions import get_workspace_member
from app.models.user import User
from app.models.workspace import WorkspaceRole
from app.modules.knowledge.models import KnowledgeDocument

router = APIRouter()

logger = logging.getLogger("knowledge.router")

# 全量重建时单次投递的消息数上限（防止超大工作区一次投递过多任务）
_REBUILD_IM_LIMIT = 2000


@router.post("/rebuild")
async def rebuild(
    background_tasks: BackgroundTasks,
    workspace_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """按工作区全量重建知识库索引（仅 owner/admin；BackgroundTasks 异步执行）"""
    member = get_workspace_member(workspace_id, current_user.id, db)
    if member.role not in (WorkspaceRole.OWNER, WorkspaceRole.ADMIN):
        from app.core.exceptions import PermissionDeniedError
        raise PermissionDeniedError(detail="需要管理员权限")

    from app.modules.file.models import File
    from app.modules.announcement.models import Announcement
    from app.modules.im.models import Message, Conversation, MessageType
    from app.modules.knowledge.indexer import index_source

    file_ids = [r[0] for r in db.query(File.id).filter(
        File.workspace_id == workspace_id, File.is_active == True).all()]
    ann_ids = [r[0] for r in db.query(Announcement.id).filter(
        Announcement.workspace_id == workspace_id, Announcement.is_active == True).all()]

    conv_ids = [r[0] for r in db.query(Conversation.id).filter(
        Conversation.workspace_id == workspace_id).all()]
    msg_ids = []
    if conv_ids:
        msg_ids = [r[0] for r in db.query(Message.id).filter(
            Message.conversation_id.in_(conv_ids),
            Message.is_recalled == False,
            Message.msg_type == MessageType.TEXT,
        ).order_by(Message.id.desc()).limit(_REBUILD_IM_LIMIT).all()]

    total = 0
    for fid in file_ids:
        background_tasks.add_task(index_source, "file", fid)
        total += 1
    for aid in ann_ids:
        background_tasks.add_task(index_source, "announcement", aid)
        total += 1
    for mid in msg_ids:
        background_tasks.add_task(index_source, "im", mid)
        total += 1

    logger.info(f"[KB] rebuild 投递 {total} 个索引任务 ws={workspace_id} "
                f"(file={len(file_ids)}, ann={len(ann_ids)}, im={len(msg_ids)})")
    return {"message": f"已投递 {total} 个索引任务，稍后用 GET /stats 查看进度",
            "total": total,
            "detail": {"file": len(file_ids), "announcement": len(ann_ids), "im": len(msg_ids)}}


@router.get("/stats")
async def stats(
    workspace_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """索引状态统计：各来源文档数/分片数/失败数 + 向量库总量"""
    get_workspace_member(workspace_id, current_user.id, db)

    rows = db.query(
        KnowledgeDocument.source_type,
        KnowledgeDocument.status,
        func.count(KnowledgeDocument.id),
        func.coalesce(func.sum(KnowledgeDocument.chunk_count), 0),
    ).filter(
        KnowledgeDocument.workspace_id == workspace_id,
        KnowledgeDocument.is_active == True,
    ).group_by(KnowledgeDocument.source_type, KnowledgeDocument.status).all()

    sources = {}
    for st, status_, cnt, chunks in rows:
        d = sources.setdefault(st, {"documents": 0, "indexed": 0, "failed": 0,
                                    "pending": 0, "unsupported": 0, "chunks": 0})
        d["documents"] += cnt
        if status_ in d:
            d[status_] += cnt
        d["chunks"] += int(chunks or 0)

    vector_total = None
    vector_error = None
    try:
        from app.modules.knowledge.vector_store import get_collection
        vector_total = get_collection().count()
    except Exception as e:
        vector_error = f"{type(e).__name__}: {e}"

    return {
        "workspace_id": workspace_id,
        "sources": sources,
        "vector_count": vector_total,
        "vector_error": vector_error,
    }
