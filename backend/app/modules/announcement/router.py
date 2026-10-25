"""企业公告模块 — API 路由"""
import logging

from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import get_current_user
from app.core.permissions import get_workspace_member
from app.models.user import User
from app.models.workspace import WorkspaceRole
from app.modules.announcement.crud import announcement_crud
from app.modules.announcement.schemas import AnnouncementCreate

router = APIRouter()

logger = logging.getLogger(__name__)


def _require_admin(workspace_id: int, user_id: int, db: Session):
    member = get_workspace_member(workspace_id, user_id, db)
    if member.role not in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN]:
        from app.core.exceptions import PermissionDeniedError
        raise PermissionDeniedError(detail="需要管理员权限")


@router.get("")
async def get_list(
    workspace_id: int = Query(None),
    type: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_workspace_member(workspace_id, current_user.id, db)
    return announcement_crud.get_list(db, workspace_id, type, page, page_size)


@router.get("/{ann_id}")
async def get_detail(
    ann_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    a = announcement_crud.get_by_id(db, ann_id)
    get_workspace_member(a.workspace_id, current_user.id, db)
    announcement_crud.mark_read(db, ann_id, current_user.id)
    return announcement_crud._format(a)


@router.post("", status_code=201)
async def create(
    body: AnnouncementCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _require_admin(body.workspace_id, current_user.id, db)
    a = announcement_crud.create(db, body.workspace_id, current_user.id,
                                 body.title, body.content, body.type,
                                 body.is_pinned, body.is_must_read,
                                 body.publish_at, body.expire_at)

    # RAG：后台异步索引公告内容（失败不影响发布公告）
    try:
        from app.modules.knowledge.indexer import index_source
        background_tasks.add_task(index_source, "announcement", a.id)
    except Exception as e:
        logger.warning(f"公告索引进队失败（不影响发布）: {e}")

    return announcement_crud._format(a)


@router.delete("/{ann_id}")
async def delete(
    ann_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    a = announcement_crud.get_by_id(db, ann_id)
    _require_admin(a.workspace_id, current_user.id, db)
    announcement_crud.delete(db, ann_id)

    # RAG：后台异步清理该公告的向量与分片元数据
    try:
        from app.modules.knowledge.indexer import delete_source_index
        background_tasks.add_task(delete_source_index, "announcement", ann_id)
    except Exception as e:
        logger.warning(f"公告索引清理入队失败（不影响删除）: {e}")

    return {"message": "公告已删除"}


@router.get("/{ann_id}/read-status")
async def read_status(
    ann_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    a = announcement_crud.get_by_id(db, ann_id)
    get_workspace_member(a.workspace_id, current_user.id, db)
    return announcement_crud.get_read_status(db, ann_id)
