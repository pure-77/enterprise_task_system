"""组织架构模块 — API 路由"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import get_current_user
from app.core.permissions import get_workspace_member
from app.core.exceptions import ResourceNotFoundError, PermissionDeniedError
from app.models.workspace import WorkspaceRole, WorkspaceMember
from app.models.user import User
from app.modules.org.crud import department_crud, position_crud
from app.modules.org.schemas import (
    DepartmentCreate, DepartmentUpdate,
    PositionCreate, PositionUpdate, PositionResponse,
    MemberUpdate, MemberResponse,
)

router = APIRouter()


def _require_admin(workspace_id: int, user_id: int, db: Session) -> WorkspaceMember:
    """要求 OWNER 或 ADMIN 权限"""
    member = get_workspace_member(workspace_id, user_id, db)
    if member.role not in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN]:
        raise PermissionDeniedError(detail="需要管理员权限")
    return member


# ==================== 部门管理 ====================

@router.get("/departments")
async def get_department_tree(
    workspace_id: int = Query(None, description="工作空间ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取部门树 — 空间成员即可查看"""
    get_workspace_member(workspace_id, current_user.id, db)
    tree = department_crud.get_tree(db, workspace_id)
    return tree


@router.post("/departments", status_code=201)
async def create_department(
    dept_in: DepartmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建部门 — 需要 OWNER 或 ADMIN 权限"""
    _require_admin(dept_in.workspace_id, current_user.id, db)
    dept = department_crud.create(
        db,
        workspace_id=dept_in.workspace_id,
        name=dept_in.name,
        parent_id=dept_in.parent_id,
        leader_id=dept_in.leader_id,
        sort_order=dept_in.sort_order
    )
    return {
        "id": dept.id,
        "name": dept.name,
        "parent_id": dept.parent_id,
        "path": dept.path,
        "sort_order": dept.sort_order
    }


@router.put("/departments/{dept_id}")
async def update_department(
    dept_id: int,
    dept_in: DepartmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新部门"""
    dept = department_crud.get_by_id(db, dept_id)
    _require_admin(dept.workspace_id, current_user.id, db)
    updated = department_crud.update(db, dept_id, **dept_in.model_dump(exclude_none=True))
    return {
        "id": updated.id,
        "name": updated.name,
        "parent_id": updated.parent_id,
        "path": updated.path,
        "sort_order": updated.sort_order
    }


@router.delete("/departments/{dept_id}")
async def delete_department(
    dept_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除部门（级联软删除子部门）"""
    dept = department_crud.get_by_id(db, dept_id)
    _require_admin(dept.workspace_id, current_user.id, db)
    department_crud.delete(db, dept_id)
    return {"message": "部门已删除"}


# ==================== 职位管理 ====================

@router.get("/positions")
async def get_positions(
    workspace_id: int = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取职位列表"""
    get_workspace_member(workspace_id, current_user.id, db)
    positions = position_crud.get_list(db, workspace_id)
    return [PositionResponse.model_validate(p).model_dump() for p in positions]


@router.post("/positions", status_code=201)
async def create_position(
    pos_in: PositionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建职位"""
    _require_admin(pos_in.workspace_id, current_user.id, db)
    pos = position_crud.create(db, pos_in.workspace_id, pos_in.name, pos_in.sort_order)
    return PositionResponse.model_validate(pos).model_dump()


@router.put("/positions/{pos_id}")
async def update_position(
    pos_id: int,
    pos_in: PositionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新职位"""
    pos = position_crud.get_by_id(db, pos_id)
    _require_admin(pos.workspace_id, current_user.id, db)
    updated = position_crud.update(db, pos_id, **pos_in.model_dump(exclude_none=True))
    return PositionResponse.model_validate(updated).model_dump()


@router.delete("/positions/{pos_id}")
async def delete_position(
    pos_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除职位"""
    pos = position_crud.get_by_id(db, pos_id)
    _require_admin(pos.workspace_id, current_user.id, db)
    position_crud.delete(db, pos_id)
    return {"message": "职位已删除"}


# ==================== 成员管理 ====================

@router.get("/members")
async def get_members(
    workspace_id: int = Query(None),
    department_id: int = Query(None, description="按部门筛选"),
    keyword: str = Query(None, description="姓名/邮箱/工号搜索"),
    status: str = Query(None, description="成员状态: active/leave/suspended"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取成员花名册"""
    get_workspace_member(workspace_id, current_user.id, db)

    query = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.is_active == True
    )

    if department_id:
        query = query.filter(WorkspaceMember.department_id == department_id)
    if status:
        query = query.filter(WorkspaceMember.status == status)
    if keyword:
        query = query.filter(
            (WorkspaceMember.real_name.ilike(f"%{keyword}%")) |
            (WorkspaceMember.employee_no.ilike(f"%{keyword}%"))
        )

    total = query.count()
    members = query.offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for m in members:
        item = MemberResponse.model_validate(m)
        if m.user:
            item.email = m.user.email
            item.nickname = m.user.nickname
            item.avatar = m.user.avatar
        if m.department:
            item.department_name = m.department.name
        if m.position:
            item.position_name = m.position.name
        items.append(item.model_dump())

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0
    }


@router.put("/members/{member_id}")
async def update_member(
    member_id: int,
    member_in: MemberUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新成员信息 — OWNER 或 ADMIN"""
    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.id == member_id,
        WorkspaceMember.is_active == True
    ).first()
    if not member:
        raise ResourceNotFoundError(resource="成员")

    _require_admin(member.workspace_id, current_user.id, db)

    for key, value in member_in.model_dump(exclude_none=True).items():
        setattr(member, key, value)

    db.commit()
    db.refresh(member)
    return {"message": "成员信息已更新"}
