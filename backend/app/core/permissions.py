from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.workspace import WorkspaceMember, WorkspaceRole


def get_workspace_member(workspace_id: int, user_id: int, db: Session):
    """获取用户在空间中的成员记录，非成员返回403"""
    if workspace_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="缺少 workspace_id 参数，请先选择一个工作空间"
        )
    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id
    ).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="你不是该空间的成员"
        )
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
