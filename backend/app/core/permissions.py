"""权限验证模块 — 带Redis缓存的高频权限校验"""
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.workspace import WorkspaceMember, WorkspaceRole
from app.services.cache_service import CacheService


def get_workspace_member(workspace_id: int, user_id: int, db: Session):
    """获取用户在空间中的成员记录，非成员返回403。
    优化：先查缓存，缓存未命中再查DB并回填。"""
    if workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="缺少 workspace_id 参数，请先选择一个工作空间"
        )

    # 尝试从缓存读取
    cached = CacheService.get_member_permission(workspace_id, user_id)
    if cached is not None:
        # 缓存命中：必须仍然验证成员在DB中真实存在（防止缓存脏读）
        member = db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
            WorkspaceMember.is_active == True
        ).first()
        if not member:
            # DB中不存在，清除缓存并返回403
            CacheService.delete_member_permission(workspace_id, user_id)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="你不是该空间的成员"
            )
        return member

    # 缓存未命中，查询DB
    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id,
        WorkspaceMember.is_active == True
    ).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="你不是该空间的成员"
        )
    # 回填缓存
    CacheService.set_member_permission(workspace_id, user_id, member.role.value)
    return member


def require_role(workspace_id: int, user_id: int, roles: list, db: Session):
    """要求用户持有指定角色之一，否则返回403"""
    member = get_workspace_member(workspace_id, user_id, db)
    if member.role not in roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="你没有权限执行此操作"
        )
    return member
