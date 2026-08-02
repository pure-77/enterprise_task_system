from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import pytz
from app.db.session import get_db

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def get_beijing_time_str():
    """获取当前北京时区时间的ISO字符串"""
    return datetime.now(BEIJING_TZ).replace(tzinfo=None).isoformat()
from app.schemas.task import (
    TaskCreate, TaskUpdate, TaskResponse, TaskListResponse,
    TaskStatusUpdate, TaskBatchUpdate, TaskFilter
)
from app.crud.task import task as task_crud
from app.models.task import TaskStatus, TaskPriority
from app.core.security import decode_token
from fastapi import Header
from app.db.redis_client import get_redis
import json

router = APIRouter()


def get_current_user_id(authorization: str = Header(None, alias="Authorization")) -> int:
    """获取当前用户ID - 面试考点：从JWT token中提取用户信息"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证令牌"
        )

    try:
        token = authorization.replace("Bearer ", "")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌格式"
        )

    from app.core.security import decode_token
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌"
        )

    # 禁止刷新令牌用于业务接口访问
    if payload.get("type") == "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌"
        )

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌"
        )

    return user_id


def publish_task_status_update(user_id: int, task_id: int, status: str):
    """发布任务状态更新到 Redis（Redis 不可用时静默跳过）"""
    try:
        message = {
            "type": "task_status_update",
            "user_id": user_id,
            "task_id": task_id,
            "status": status,
            "timestamp": get_beijing_time_str()
        }
        get_redis().publish('task_status_updates', json.dumps(message))
    except Exception:
        pass


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_in: TaskCreate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """创建任务接口 — 团队空间中普通成员不能创建"""
    from app.crud.category import category as category_crud
    from app.core.permissions import get_workspace_member
    from app.models.workspace import WorkspaceRole, WorkspaceMember

    # 验证空间权限
    if task_in.workspace_id:
        member = get_workspace_member(task_in.workspace_id, user_id, db)
        # 普通成员不能在工作区创建任务
        if member.role == WorkspaceRole.MEMBER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="普通成员不能创建工作区任务"
            )
        category = category_crud.get_by_id_and_user_id(db, task_in.category_id, user_id, task_in.workspace_id)

        # 校验被分配人是 workspace 成员
        assignee_ids_to_check = task_in.assignee_ids or []
        if task_in.assignee_id:
            assignee_ids_to_check.append(task_in.assignee_id)
        if assignee_ids_to_check:
            valid_count = db.query(WorkspaceMember).filter(
                WorkspaceMember.workspace_id == task_in.workspace_id,
                WorkspaceMember.user_id.in_(assignee_ids_to_check),
                WorkspaceMember.is_active == True
            ).count()
            if valid_count != len(set(assignee_ids_to_check)):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="被分配人必须是工作区成员"
                )
    else:
        category = category_crud.get_by_id_and_user_id(db, task_in.category_id, user_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分类不存在")

    db_task = task_crud.create(db, task_in, user_id)
    publish_task_status_update(user_id, db_task.id, db_task.status)

    from app.crud.workspace import workspace_activity
    if task_in.workspace_id:
        workspace_activity.add(db, task_in.workspace_id, user_id, "task_created", "task", db_task.id)

    from app.services.cache_service import cache_service
    cache_service.delete_user_tasks(user_id)

    return db_task


@router.get("", response_model=TaskListResponse)
async def get_tasks(
    status: Optional[TaskStatus] = None,
    priority: Optional[TaskPriority] = None,
    category_id: Optional[int] = None,
    tag_id: Optional[int] = None,
    keyword: Optional[str] = None,
    due_date_start: Optional[datetime] = None,
    due_date_end: Optional[datetime] = None,
    workspace_id: Optional[int] = None,
    assignee_id: Optional[int] = None,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """获取任务列表接口 - 面试考点：支持多条件筛选和分页"""
    skip = (page - 1) * page_size

    tasks, total = task_crud.get_multi(
        db=db,
        user_id=user_id,
        skip=skip,
        limit=page_size,
        status=status,
        priority=priority,
        category_id=category_id,
        tag_id=tag_id,
        keyword=keyword,
        due_date_start=due_date_start,
        due_date_end=due_date_end,
        workspace_id=workspace_id,
        assignee_id=assignee_id
    )

    return TaskListResponse(
        tasks=tasks,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """获取单个任务接口 - 含完成追踪数据"""
    from app.models.workspace import WorkspaceMember
    from app.models.task_completion import TaskCompletion

    db_task = task_crud.get_by_id(db, task_id, user_id)
    if not db_task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    # 团队公开任务 → 注入完成追踪数据
    if db_task.is_team_wide and db_task.workspace_id:
        db_task._total_members_cache = db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == db_task.workspace_id,
            WorkspaceMember.is_active == True
        ).count()

    return db_task


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_in: TaskUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """更新任务接口 - 角色权限：
    - 个人任务：仅创建者可编辑
    - 团队任务 + is_team_wide=True：任何成员可编辑所有字段
    - 团队任务 + is_team_wide=False：
        OWNER/ADMIN/创建者 → 可编辑所有字段
        被分配人（assignee_id 或 assignee_ids 中） → 可编辑所有字段
    """
    from app.models.workspace import WorkspaceRole, WorkspaceMember
    from app.core.permissions import get_workspace_member

    db_task = task_crud.get_task_with_permission(db, task_id, user_id)
    if not db_task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    can_edit_all = False

    if db_task.workspace_id is None:
        if db_task.user_id == user_id:
            can_edit_all = True
    elif db_task.is_team_wide:
        # 团队公开任务：任何成员可编辑
        member = db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == db_task.workspace_id,
            WorkspaceMember.user_id == user_id,
            WorkspaceMember.is_active == True
        ).first()
        if member:
            can_edit_all = True
    else:
        # 非公开团队任务
        member = get_workspace_member(db_task.workspace_id, user_id, db)
        if member.role in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN] or db_task.user_id == user_id:
            can_edit_all = True
        elif db_task.assignee_id == user_id:
            can_edit_all = True  # 被分配人可编辑全部字段
        elif any(a.id == user_id for a in db_task.assignees):
            can_edit_all = True  # 多人分配中的被分配人也可编辑全部

    if not can_edit_all:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="你没有编辑此任务的权限")

    # 验证分类
    if task_in.category_id:
        from app.crud.category import category as category_crud
        if db_task.workspace_id:
            category = category_crud.get_by_id_and_user_id(db, task_in.category_id, user_id, db_task.workspace_id)
        else:
            category = category_crud.get_by_id_and_user_id(db, task_in.category_id, user_id)
        if not category:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分类不存在")

    old_status = db_task.status
    updated_task = task_crud.update(db, db_task, task_in)

    if updated_task.status != old_status:
        publish_task_status_update(user_id, updated_task.id, updated_task.status)
        if db_task.workspace_id:
            from app.crud.workspace import workspace_activity
            workspace_activity.add(db, db_task.workspace_id, user_id, "task_status_changed", "task", task_id,
                                   '{"from": "' + old_status.value + '", "to": "' + updated_task.status.value + '"}')

    from app.services.cache_service import cache_service
    cache_service.delete_user_tasks(user_id)

    return updated_task


@router.delete("/{task_id}")
async def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """删除任务接口 - 权限：
    - 个人任务：仅创建者可删
    - 团队任务：仅 OWNER/ADMIN/创建者可删
    """
    from app.models.workspace import WorkspaceRole, WorkspaceMember

    db_task = task_crud.get_task_with_permission(db, task_id, user_id)
    if not db_task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    # 删除权限检查
    can_delete = False
    if db_task.workspace_id is None:
        if db_task.user_id == user_id:
            can_delete = True
    else:
        member = db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == db_task.workspace_id,
            WorkspaceMember.user_id == user_id,
            WorkspaceMember.is_active == True
        ).first()
        if member and (member.role in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN] or db_task.user_id == user_id):
            can_delete = True

    if not can_delete:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="你没有删除此任务的权限")

    db_task = task_crud.delete(db, task_id, user_id)

    publish_task_status_update(user_id, task_id, "deleted")

    from app.services.cache_service import cache_service
    cache_service.delete_user_tasks(user_id)

    return {"message": "任务删除成功"}


@router.patch("/{task_id}/status", response_model=TaskResponse)
async def update_task_status(
    task_id: int,
    status_update: TaskStatusUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """更新任务状态接口
    - 团队公开任务：只有 OWNER/ADMIN 可以标记为 completed
    - 其他状态（in_progress/cancelled/pending）：创建者/被分配人/任何成员可操作
    """
    from app.models.workspace import WorkspaceRole, WorkspaceMember

    db_task = task_crud.get_task_with_permission(db, task_id, user_id)
    if not db_task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    # 团队公开任务 → completed 仅 OWNER/ADMIN 可操作
    if db_task.is_team_wide and status_update.status == TaskStatus.COMPLETED:
        member = db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == db_task.workspace_id,
            WorkspaceMember.user_id == user_id,
            WorkspaceMember.is_active == True
        ).first()
        if not member or member.role not in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="需要全部成员完成后，由管理员标记为已完成"
            )

    old_status = db_task.status
    task_update = TaskUpdate(status=status_update.status)
    updated_task = task_crud.update(db, db_task, task_update)

    if updated_task.status != old_status:
        publish_task_status_update(user_id, updated_task.id, updated_task.status)

    from app.services.cache_service import cache_service
    cache_service.delete_user_tasks(user_id)

    return updated_task


@router.post("/{task_id}/complete")
async def complete_team_task(
    task_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """成员标记自己完成了团队公开任务
    - 仅 is_team_wide=True 的任务可用
    - 每个成员只能标记一次（不可重复）
    """
    from app.models.workspace import WorkspaceMember
    from app.models.task_completion import TaskCompletion

    db_task = task_crud.get_task_with_permission(db, task_id, user_id)
    if not db_task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    if not db_task.is_team_wide:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="只有团队公开任务支持此操作")

    # 检查是否已完成过
    existing = db.query(TaskCompletion).filter(
        TaskCompletion.task_id == task_id,
        TaskCompletion.user_id == user_id,
        TaskCompletion.is_active == True
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="你已经标记完成过了")

    completion = TaskCompletion(task_id=task_id, user_id=user_id)
    db.add(completion)
    db.commit()

    from app.services.cache_service import cache_service
    cache_service.delete_user_tasks(user_id)

    return {"message": "已完成标记", "task_id": task_id, "user_id": user_id}


@router.post("/batch/update")
async def batch_update_tasks(
    batch_update: TaskBatchUpdate,
    workspace_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """批量更新任务接口"""
    # workspace 成员校验
    if workspace_id:
        from app.core.permissions import get_workspace_member
        get_workspace_member(workspace_id, user_id, db)

    count = task_crud.batch_update(
        db=db,
        task_ids=batch_update.task_ids,
        user_id=user_id,
        status=batch_update.status,
        priority=batch_update.priority,
        category_id=batch_update.category_id,
        workspace_id=workspace_id
    )

    if batch_update.status:
        for task_id in batch_update.task_ids:
            publish_task_status_update(user_id, task_id, batch_update.status)

    from app.services.cache_service import cache_service
    cache_service.delete_user_tasks(user_id)

    return {"message": f"成功更新{count}个任务", "count": count}


@router.post("/batch/delete")
async def batch_delete_tasks(
    task_ids: list[int],
    workspace_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """批量删除任务接口"""
    if workspace_id:
        from app.core.permissions import get_workspace_member
        get_workspace_member(workspace_id, user_id, db)

    count = task_crud.batch_delete(db, task_ids, user_id, workspace_id)

    for task_id in task_ids:
        publish_task_status_update(user_id, task_id, "deleted")

    from app.services.cache_service import cache_service
    cache_service.delete_user_tasks(user_id)

    return {"message": f"成功删除{count}个任务", "count": count}