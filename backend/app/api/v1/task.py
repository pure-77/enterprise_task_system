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
from app.services.cache_service import CacheService
import json

router = APIRouter()


def _invalidate_task_caches(user_id: int, task_id: int = None, workspace_id: int = None):
    """任务变更后失效相关缓存"""
    if task_id:
        CacheService.delete_task_detail(task_id)
    CacheService.invalidate_user_stats(user_id)
    CacheService.delete_user_tasks(user_id)
    CacheService.delete_user_categories(user_id)


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
    """发布任务状态更新：1) Redis Pub/Sub 实时推送 2) Celery 异步写入通知中心"""
    try:
        msg_type = "task_assigned" if status == "assigned" else "task_status_update"
        message = {
            "type": msg_type,
            "user_id": user_id,
            "task_id": task_id,
            "status": status,
            "timestamp": get_beijing_time_str()
        }
        get_redis().publish('task_status_updates', json.dumps(message))
    except Exception:
        pass

    # 异步写入通知中心（不阻塞请求）
    try:
        from app.tasks.notification_tasks import push_notification_to_user
        if status == "assigned":
            title = "新任务分配"
            content = f"有新任务分配给你（任务 ID {task_id}），请及时处理"
        else:
            status_map = {
                "pending": "待处理", "in_progress": "进行中", "completed": "已完成",
                "overdue": "已逾期", "deleted": "已删除", "cancelled": "已取消"
            }
            title = f"任务状态变更：{status_map.get(status, status)}"
            content = f"任务 ID {task_id} 状态已更新为「{status_map.get(status, status)}」"

        if status not in ("deleted", "cancelled"):
            push_notification_to_user.delay(
                user_id,
                "task",
                title,
                content,
                "task",
                task_id
            )
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

    # 🐛 FIX: 同时通知被分配人（assignee_id）
    # 原逻辑只通知创建者 assignee 其他人收不到
    notified = set([user_id])
    if task_in.assignee_id and task_in.assignee_id not in notified:
        publish_task_status_update(task_in.assignee_id, db_task.id, "assigned")
        notified.add(task_in.assignee_id)
    if task_in.assignee_ids:
        for aid in task_in.assignee_ids:
            if aid not in notified:
                publish_task_status_update(aid, db_task.id, "assigned")
                notified.add(aid)

    from app.crud.workspace import workspace_activity
    if task_in.workspace_id:
        workspace_activity.add(db, task_in.workspace_id, user_id, "task_created", "task", db_task.id)

    _invalidate_task_caches(user_id, db_task.id, task_in.workspace_id)

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

    # 团队空间里的所有任务都注入完成追踪数据，便于前端显示进度
    # team_wide → workspace 全员参与；非 team_wide → assignees 列表（单人或多人）
    needs_tracking = db_task.workspace_id is not None
    if needs_tracking and db_task.workspace_id:
        if db_task.is_team_wide:
            # team_wide：目标是 workspace 所有活跃成员
            db_task._total_members_cache = db.query(WorkspaceMember).filter(
                WorkspaceMember.workspace_id == db_task.workspace_id,
                WorkspaceMember.is_active == True
            ).count()
        else:
            # 非 team_wide：目标是被分配人数量（单人也算）
            db_task._total_members_cache = len(db_task.assignees or [])

    # 给 completions 注入 nickname（TaskCompletion ORM 没有直接的 nickname 字段）
    for c in (db_task.completions or []):
        if not hasattr(c, 'nickname') or c.nickname is None:
            user_obj = getattr(c, 'user', None)
            if user_obj:
                object.__setattr__(c, 'nickname', user_obj.nickname or user_obj.email)

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
        # 规则：Owner/Admin 可改所有；被分配人可改；创建者如果没分配给自己不能改
        if member.role in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN]:
            can_edit_all = True
        elif db_task.assignee_id == user_id:
            can_edit_all = True  # 单人分配给自己
        elif any(a.id == user_id for a in db_task.assignees):
            can_edit_all = True  # 多人分配中包含自己

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

    _invalidate_task_caches(user_id, task_id, db_task.workspace_id)

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

    _invalidate_task_caches(user_id, task_id)

    return {"message": "任务删除成功"}


@router.patch("/{task_id}/status", response_model=TaskResponse)
async def update_task_status(
    task_id: int,
    status_update: TaskStatusUpdate,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """更新任务状态接口 — 权限规则同 PUT /tasks/{id}：
    - 个人任务：仅创建者
    - 团队公开（is_team_wide）：任何成员可改；标记 completed 仅 Owner/Admin
    - 非公开团队任务：Owner/Admin 可改所有；被分配人（单人/多人）可改；创建者没分配给自己不能改
    """
    from app.models.workspace import WorkspaceRole, WorkspaceMember
    from app.core.permissions import get_workspace_member

    db_task = task_crud.get_task_with_permission(db, task_id, user_id)
    if not db_task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    # --- 修改权限校验（与 PUT /tasks/{id} 保持一致）---
    can_edit_status = False
    if db_task.workspace_id is None:
        # 个人任务：仅创建者
        if db_task.user_id == user_id:
            can_edit_status = True
    elif db_task.is_team_wide:
        # 团队公开：任何 workspace 成员可改
        member = db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == db_task.workspace_id,
            WorkspaceMember.user_id == user_id,
            WorkspaceMember.is_active == True
        ).first()
        if member:
            can_edit_status = True
    else:
        # 非公开团队任务
        member = get_workspace_member(db_task.workspace_id, user_id, db)
        if member.role in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN]:
            can_edit_status = True
        elif db_task.assignee_id == user_id:
            can_edit_status = True  # 单人分配给自己
        elif any(a.id == user_id for a in db_task.assignees):
            can_edit_status = True  # 多人分配中包含自己

    if not can_edit_status:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅任务创建者、Owner/Admin 或被分配人可修改状态"
        )

    # 多人追踪任务：禁止直接把 status 设为 completed，必须所有人都先 POST /complete
    # 无论 Owner/Admin 还是被分配人，都不能绕过"逐个标记"流程
    # 只要是 workspace 里的任务（有 workspace_id）都需要追踪
    needs_tracking = db_task.workspace_id is not None
    if needs_tracking and status_update.status == TaskStatus.COMPLETED:
        from app.models.task_completion import TaskCompletion
        from app.models.workspace import WorkspaceMember

        all_done = False
        if db_task.is_team_wide and db_task.workspace_id:
            target_count = db.query(WorkspaceMember).filter(
                WorkspaceMember.workspace_id == db_task.workspace_id,
                WorkspaceMember.is_active == True
            ).count()
            done_count = db.query(TaskCompletion).filter(
                TaskCompletion.task_id == task_id,
                TaskCompletion.is_active == True
            ).count()
            all_done = target_count > 0 and done_count >= target_count
        else:
            target_ids = {a.id for a in (db_task.assignees or [])}
            if target_ids:
                done_ids = {c.user_id for c in db_task.completions}
                all_done = target_ids.issubset(done_ids)
            else:
                # 没有 assignees 的 workspace 任务 → 视为单人创建，不阻塞
                all_done = True

        if not all_done:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="还有成员未标记完成，无法将任务标记为已完成。请使用「我完成了」按钮逐个标记。"
            )

    old_status = db_task.status
    task_update = TaskUpdate(status=status_update.status)
    updated_task = task_crud.update(db, db_task, task_update)

    if updated_task.status != old_status:
        publish_task_status_update(user_id, updated_task.id, updated_task.status)

    _invalidate_task_caches(user_id, task_id, db_task.workspace_id)

    return updated_task


@router.post("/{task_id}/complete")
async def complete_team_task(
    task_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """成员标记自己完成了多人协作任务
    - is_team_wide=True：workspace 任何活跃成员都可标记
    - 多人 assignees：只有被分配到的人可标记
    - 每个成员只能标记一次（不可重复）
    - 所有人都标记完成后自动把任务 status 改成 COMPLETED
    """
    from app.models.workspace import WorkspaceMember
    from app.models.task_completion import TaskCompletion

    db_task = task_crud.get_task_with_permission(db, task_id, user_id)
    if not db_task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    # 判断类型：团队空间里的所有任务（有 workspace_id）都需要追踪完成
    # team_wide → workspace 全员参与
    # 非 team_wide → 被分配人参与（单人/多人 assignees）
    needs_tracking = db_task.workspace_id is not None
    if not needs_tracking:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="个人任务不需要多人完成标记")

    # 多人 assignees 任务：只有被分配到的人可以标记
    if not db_task.is_team_wide and db_task.assignees:
        if user_id not in (a.id for a in db_task.assignees):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="你不是被分配人，无需标记")

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
    db.flush()  # 刷新以便后续查询 completions

    # 自动推进：判断是否所有目标人都完成了
    all_done = False
    if db_task.is_team_wide and db_task.workspace_id:
        # team_wide：目标是 workspace 所有活跃成员
        target_count = db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == db_task.workspace_id,
            WorkspaceMember.is_active == True
        ).count()
        done_count = db.query(TaskCompletion).filter(
            TaskCompletion.task_id == task_id,
            TaskCompletion.is_active == True
        ).count()
        all_done = target_count > 0 and done_count >= target_count
    else:
        # 非 team_wide：目标是所有被分配人（单人或多人 assignees 列表）
        target_ids = {a.id for a in (db_task.assignees or [])}
        if target_ids:
            done_ids = {c.user_id for c in db_task.completions}
            all_done = target_ids.issubset(done_ids)

    if all_done and db_task.status != TaskStatus.COMPLETED:
        db_task.status = TaskStatus.COMPLETED

    db.commit()

    from app.services.cache_service import cache_service
    cache_service.delete_user_tasks(user_id)

    return {"message": "已完成标记", "task_id": task_id, "user_id": user_id, "all_done": all_done}


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

    for task_id in batch_update.task_ids:
        CacheService.delete_task_detail(task_id)
    _invalidate_task_caches(user_id)

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
        CacheService.delete_task_detail(task_id)
    _invalidate_task_caches(user_id)

    return {"message": f"成功删除{count}个任务", "count": count}