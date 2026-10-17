"""Agent 工具组 — 任务管理 Tools

每个工具 = 一份 JSON Schema（给 LLM 看的说明书）+ 一个 handler（实际执行函数）
handler 内部直接调用你现有的 CRUD / Service，零重复逻辑。
"""
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.user import User
from app.models.workspace import WorkspaceMember
from app.crud.task import task as task_crud
from app.schemas.task import TaskCreate, TaskUpdate
from app.core.permissions import get_workspace_member
from app.core.exceptions import PermissionDeniedError

logger = logging.getLogger("agent.tools.task")

# 任务计划在 Redis 中的暂存 TTL（30 分钟内待用户确认）
_PLAN_TTL_SECONDS = 1800
# 单次规划允许的最大子任务数
_PLAN_MAX_ITEMS = 15
# 计划在 Redis 中的 key 前缀
_PLAN_REDIS_PREFIX = "agent:plan:"


# ============================================================
# Task 模块的 4 个核心 Tool
# ============================================================

def _schema_create_task() -> dict:
    return {
        "name": "create_task",
        "description": "创建一个新任务。用户说要创建任务时调用。只需提供标题，其他参数自动补全。",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "任务标题，简洁明了",
                },
                "description": {
                    "type": "string",
                    "description": "任务详细描述（可选）",
                },
                "assignee_id": {
                    "type": "integer",
                    "description": "负责人用户 ID（可选，默认是创建者自己）",
                },
                "deadline": {
                    "type": "string",
                    "description": "截止时间，格式 YYYY-MM-DD HH:mm（可选）",
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high", "urgent"],
                    "description": "优先级（可选，默认 medium）",
                },
                "category_id": {
                    "type": "integer",
                    "description": "分类 ID（可选）",
                },
            },
            "required": ["title"],
        },
    }


def _handler_create_task(
    title: str,
    description: str = None,
    assignee_id: int = None,
    deadline: str = None,
    priority: str = "medium",
    category_id: int = None,
    workspace_id: int = None,
    context: dict = None,
) -> str:
    """创建任务的 handler"""
    user: User = context["user"]
    db = SessionLocal()

    try:
        # workspace_id 兜底：参数没传就从 context 里取
        raw_ws = workspace_id if workspace_id is not None else context.get("workspace_id")
        # 个人空间统一为 None：0 代表"个人模式"，落库必须是 NULL（否则列表按 IS NULL 过滤会查不到）
        ws = raw_ws if (raw_ws and raw_ws > 0) else None

        # 权限收口（对齐 HTTP 层 api/v1/task.py 的规则）
        if ws is not None:
            from app.models.workspace import WorkspaceMember, WorkspaceRole
            member = get_workspace_member(ws, user.id, db)
            # 普通成员不能创建工作区任务
            if member.role == WorkspaceRole.MEMBER:
                return json.dumps({"success": False, "error": "普通成员不能创建工作区任务"}, ensure_ascii=False)
            # 被分配人必须是工作区成员
            if assignee_id:
                valid = db.query(WorkspaceMember).filter(
                    WorkspaceMember.workspace_id == ws,
                    WorkspaceMember.user_id == assignee_id,
                    WorkspaceMember.is_active == True,
                ).count()
                if valid == 0:
                    return json.dumps({"success": False, "error": "被分配人必须是工作区成员"}, ensure_ascii=False)

        # 截止时间解析（支持多种常见格式）
        deadline_dt = None
        if deadline:
            for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
                try:
                    deadline_dt = datetime.strptime(deadline, fmt)
                    break
                except ValueError:
                    continue
            if deadline_dt is None:
                # 解析失败必须明确报错，不能静默丢弃（否则用户以为设置了截止时间）
                return json.dumps({
                    "success": False,
                    "error": f"截止时间格式无法识别: {deadline}，请使用 YYYY-MM-DD HH:mm",
                }, ensure_ascii=False)

        task_in = TaskCreate(
            workspace_id=ws,
            title=title,
            description=description,
            assignee_id=assignee_id,
            due_date=deadline_dt,  # TaskCreate schema 里字段叫 due_date
            priority=priority,
            category_id=category_id,
        )
        task = task_crud.create(db, task_in=task_in, user_id=user.id)

        # 副作用联动（与 HTTP 建任务一致）：通知被分配人 + 工作空间动态 + 失效任务缓存
        try:
            from app.api.v1.task import publish_task_status_update, _invalidate_task_caches
            status_val = task.status.value if hasattr(task.status, "value") else str(task.status)
            publish_task_status_update(user.id, task.id, status_val)
            if assignee_id and assignee_id != user.id:
                publish_task_status_update(assignee_id, task.id, "assigned")
            if ws is not None:
                from app.crud.workspace import workspace_activity
                workspace_activity.add(db, ws, user.id, "task_created", "task", task.id)
            _invalidate_task_caches(user.id, task.id, ws)
        except Exception as e:
            logger.warning(f"创建任务后置联动失败（不影响创建结果）: {e}")

        return json.dumps({
            "success": True,
            "task_id": task.id,
            "title": task.title,
            "message": f"任务「{task.title}」已创建（ID={task.id}）",
        }, ensure_ascii=False)
    except PermissionDeniedError as e:
        return json.dumps({"success": False, "error": str(e.detail)}, ensure_ascii=False)
    except Exception as e:
        logger.exception("创建任务失败")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    finally:
        db.close()


# ------------------------------------------------------------

def _schema_list_tasks() -> dict:
    return {
        "name": "list_tasks",
        "description": "查询任务列表。可按 workspace、状态、负责人、截止时间等条件筛选。",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {
                    "type": "integer",
                    "description": "按 workspace 筛选",
                },
                "status": {
                    "type": "string",
                    "enum": ["pending", "in_progress", "completed", "overdue", "cancelled"],
                    "description": "按状态筛选",
                },
                "assignee_id": {
                    "type": "integer",
                    "description": "按负责人筛选",
                },
                "keyword": {
                    "type": "string",
                    "description": "按标题/描述模糊搜索",
                },
                "page": {
                    "type": "integer",
                    "description": "页码，默认 1",
                    "default": 1,
                },
                "page_size": {
                    "type": "integer",
                    "description": "每页数量，默认 20，最大 50",
                    "default": 20,
                },
            },
            "required": [],
        },
    }


def _handler_list_tasks(
    workspace_id: int = None,
    status: str = None,
    assignee_id: int = None,
    keyword: str = None,
    page: int = 1,
    page_size: int = 20,
    context: dict = None,
) -> str:
    """查询任务列表的 handler"""
    from app.models.task import TaskStatus

    user: User = context["user"]
    db = SessionLocal()

    try:
        # workspace_id 兜底
        if workspace_id is None:
            workspace_id = context.get("workspace_id")

        # 限制 page_size
        page_size = min(page_size, 50)
        skip = (page - 1) * page_size

        # CRUD 方法签名: get_multi(db, user_id, skip, limit, status, ...)
        status_enum = TaskStatus(status) if status else None
        items, total = task_crud.get_multi(
            db=db,
            user_id=user.id,
            skip=skip,
            limit=page_size,
            status=status_enum,
            workspace_id=workspace_id if workspace_id and workspace_id > 0 else None,
            assignee_id=assignee_id,
            keyword=keyword,
        )
        # 简化返回
        result_items = []
        for t in items:
            result_items.append({
                "id": t.id,
                "title": t.title,
                "status": t.status.value if hasattr(t.status, "value") else str(t.status),
                "priority": t.priority.value if hasattr(t.priority, "value") else str(t.priority) if t.priority else None,
                "deadline": t.due_date.isoformat() if t.due_date else None,
                "assignee_id": t.assignee_id,
            })
        return json.dumps({
            "success": True,
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": result_items,
        }, ensure_ascii=False, default=str)
    except Exception as e:
        logger.exception("查询任务列表失败")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        db.close()


# ------------------------------------------------------------

def _schema_complete_task() -> dict:
    return {
        "name": "complete_task",
        "description": "将指定任务标记为已完成。需要任务 ID。",
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "integer",
                    "description": "任务 ID",
                },
            },
            "required": ["task_id"],
        },
    }


def _handler_complete_task(
    task_id: int,
    context: dict = None,
) -> str:
    """完成任务的 handler"""
    user: User = context["user"]
    db = SessionLocal()

    try:
        from app.models.task import TaskStatus, TaskAssignee

        # 1. 用 CRUD 加 user_id 过滤（只有可见任务才返回）
        task = task_crud.get_by_id(db, task_id=task_id, user_id=user.id)
        if not task:
            return json.dumps({"success": False, "error": f"任务 ID {task_id} 不存在或你无权操作"}, ensure_ascii=False)

        # 2. 权限：Owner/Admin 全量；普通成员只能操作 assignee 或 created_by 且非 team_wide 的任务
        if task.created_by != user.id and task.assignee_id != user.id:
            from app.models.workspace import WorkspaceMember
            from app.core.permissions import WorkspaceRole
            admin = db.query(WorkspaceMember).filter(
                WorkspaceMember.workspace_id == task.workspace_id,
                WorkspaceMember.user_id == user.id,
                WorkspaceMember.role.in_([WorkspaceRole.OWNER, WorkspaceRole.ADMIN]),
                WorkspaceMember.is_active == True,
            ).first()
            if not admin:
                return json.dumps({"success": False, "error": "你无权操作该任务"}, ensure_ascii=False)

        # 3. 多人完成追踪逻辑
        if task.is_team_wide or db.query(TaskAssignee).filter(TaskAssignee.task_id == task.id).count() > 1:
            # team_wide 或多人 assignee：走多人完成追踪
            from app.models.task_completion import TaskCompletion
            existing = db.query(TaskCompletion).filter(
                TaskCompletion.task_id == task.id,
                TaskCompletion.user_id == user.id,
            ).first()
            if existing:
                return json.dumps({"success": False, "error": "你已标记过完成"}, ensure_ascii=False)
            db.add(TaskCompletion(task_id=task.id, user_id=user.id))
            db.flush()
            # 检查是否所有 assignee 都已完成
            all_assignees = db.query(TaskAssignee.user_id).filter(TaskAssignee.task_id == task.id).all()
            all_user_ids = {a[0] for a in all_assignees}
            if not all_user_ids:
                # is_team_wide 但没有任何 TaskAssignee → 用 assignee_id / 创建者兜底，
                # 否则集合为空将导致任务永远无法置为 completed（死锁）
                fallback = task.assignee_id or task.created_by
                if fallback:
                    all_user_ids = {fallback}
            if not all_user_ids:
                all_user_ids = {user.id}
            # 去重统计已完成人数（同一人重复标记只算一次），与 assignee 集合对齐
            completed_count = db.query(TaskCompletion.user_id).filter(
                TaskCompletion.task_id == task.id
            ).distinct().count()
            if completed_count >= len(all_user_ids):
                task.status = TaskStatus.COMPLETED
            msg = f"你的完成标记已记录（{completed_count}/{len(all_user_ids)} 人已完成）"
        else:
            task.status = TaskStatus.COMPLETED
            msg = f"任务「{task.title}」已标记为完成 ✅"

        db.commit()
        return json.dumps({"success": True, "task_id": task_id, "message": msg}, ensure_ascii=False)
    except Exception as e:
        db.rollback()
        logger.exception("完成任务失败")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    finally:
        db.close()


# ------------------------------------------------------------

def _schema_update_task_status() -> dict:
    return {
        "name": "update_task_status",
        "description": "更新任务状态（进行中/待处理/取消）。需要任务 ID 和目标状态。",
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "integer",
                    "description": "任务 ID",
                },
                "status": {
                    "type": "string",
                    "enum": ["pending", "in_progress", "completed", "cancelled"],
                    "description": "目标状态",
                },
            },
            "required": ["task_id", "status"],
        },
    }


def _handler_update_task_status(
    task_id: int,
    status: str,
    context: dict = None,
) -> str:
    """更新任务状态的 handler"""
    user: User = context["user"]
    db = SessionLocal()

    try:
        from app.models.task import TaskStatus, TaskAssignee

        # 1. 用 CRUD 加 user_id 过滤（只有可见任务才返回）
        task = task_crud.get_by_id(db, task_id=task_id, user_id=user.id)
        if not task:
            return json.dumps({"success": False, "error": f"任务 ID {task_id} 不存在或你无权操作"}, ensure_ascii=False)

        # 2. 权限：Owner/Admin 全量；普通成员只能操作 assignee 或 created_by 且非 team_wide 的任务
        if task.created_by != user.id and task.assignee_id != user.id:
            from app.models.workspace import WorkspaceMember
            from app.core.permissions import WorkspaceRole
            admin = db.query(WorkspaceMember).filter(
                WorkspaceMember.workspace_id == task.workspace_id,
                WorkspaceMember.user_id == user.id,
                WorkspaceMember.role.in_([WorkspaceRole.OWNER, WorkspaceRole.ADMIN]),
                WorkspaceMember.is_active == True,
            ).first()
            if not admin:
                return json.dumps({"success": False, "error": "你无权操作该任务"}, ensure_ascii=False)

        # 3. 禁止直接 PATCH 到 completed —— 必须走 complete_task 的多人追踪逻辑
        target_status = TaskStatus(status)
        if target_status == TaskStatus.COMPLETED and task.status != TaskStatus.COMPLETED:
            if task.is_team_wide or db.query(TaskAssignee).filter(TaskAssignee.task_id == task.id).count() > 1:
                return json.dumps({"success": False, "error": "多人任务需逐个标记完成（用 complete_task），不能直接改状态"}, ensure_ascii=False)

        task.status = target_status
        db.commit()
        status_label = {"pending": "待处理", "in_progress": "进行中", "completed": "已完成", "cancelled": "已取消"}.get(status, status)
        return json.dumps({
            "success": True,
            "task_id": task_id,
            "message": f"任务「{task.title}」状态已更新为「{status_label}」",
        }, ensure_ascii=False)
    except Exception as e:
        db.rollback()
        logger.exception("更新任务状态失败")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    finally:
        db.close()


# ------------------------------------------------------------

def _schema_get_task_detail() -> dict:
    return {
        "name": "get_task_detail",
        "description": "查询单个任务的详细信息（描述、负责人、完成进度、截止日期等）。",
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "integer",
                    "description": "任务 ID",
                },
            },
            "required": ["task_id"],
        },
    }


def _handler_get_task_detail(
    task_id: int,
    context: dict = None,
) -> str:
    """查询任务详情的 handler"""
    user: User = context["user"]
    db = SessionLocal()

    try:
        task = task_crud.get_by_id(db, task_id=task_id, user_id=user.id)
        if not task:
            return json.dumps({"success": False, "error": f"任务 ID {task_id} 不存在或你无权查看"}, ensure_ascii=False)

        def _val(v):
            if v is None:
                return None
            return v.value if hasattr(v, "value") else str(v)

        result = {
            "success": True,
            "id": task.id,
            "title": task.title,
            "description": task.description,
            "status": _val(task.status),
            "priority": _val(task.priority),
            "deadline": task.due_date.isoformat() if task.due_date else None,
            "workspace_id": task.workspace_id,
            "category_id": task.category_id,
            "assignee_id": task.assignee_id,
            "is_team_wide": task.is_team_wide,
            # 模型无 completed_at 字段，这里返回 updated_at 语义键，避免误导模型回答"完成时间"
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
            "created_at": task.created_at.isoformat() if task.created_at else None,
        }
        return json.dumps(result, ensure_ascii=False, default=str)
    finally:
        db.close()


# ============================================================
# plan_tasks — 任务规划（轻量 Plan & Execute，计划待用户确认后才创建）
# ============================================================

def _schema_plan_tasks() -> dict:
    return {
        "name": "plan_tasks",
        "description": (
            "当用户要求规划/拆解/安排/排期【一批任务或一个大目标】时调用（如"
            "“帮我规划下周五的上线准备”、“把这件事拆成几个任务”）。"
            "本工具只生成待确认的任务计划，不会创建任何任务；用户确认后由系统批量创建。"
            "注意：单个明确的任务创建请直接用 create_task，不要用本工具。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string",
                    "description": "规划目标的一句话描述",
                },
                "tasks": {
                    "type": "array",
                    "description": f"拆解后的子任务清单，最多 {_PLAN_MAX_ITEMS} 个",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "子任务标题，简洁明确"},
                            "description": {"type": "string", "description": "子任务详细说明（可选）"},
                            "priority": {
                                "type": "string",
                                "enum": ["low", "medium", "high", "urgent"],
                                "description": "优先级（可选，默认 medium）",
                            },
                            "deadline": {
                                "type": "string",
                                "description": "截止时间，格式 YYYY-MM-DD HH:mm（可选，需结合当前时间推算成具体时间）",
                            },
                            "assignee_name": {
                                "type": "string",
                                "description": "负责人姓名/昵称/邮箱（可选，仅用户明确提及时填写；留空表示负责人为用户自己）",
                            },
                        },
                        "required": ["title"],
                    },
                },
            },
            "required": ["goal", "tasks"],
        },
    }


def _resolve_workspace_member(db: Session, ws: int, name: str) -> Optional[User]:
    """在工作区成员中按 邮箱/昵称/真实姓名 精确匹配，失败再做模糊匹配"""
    base = db.query(User).join(
        WorkspaceMember, WorkspaceMember.user_id == User.id
    ).filter(
        WorkspaceMember.workspace_id == ws,
        WorkspaceMember.is_active == True,
    )
    user = base.filter(
        or_(User.email == name, User.nickname == name, User.real_name == name)
    ).first()
    if user:
        return user
    keyword = f"%{name}%"
    return base.filter(
        or_(User.nickname.ilike(keyword), User.real_name.ilike(keyword), User.email.ilike(keyword))
    ).first()


def _parse_plan_deadline(deadline: str, index: int) -> Optional[datetime]:
    """校验计划项截止时间格式，无法识别时抛 ValueError 让整份计划返回修正提示"""
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(deadline, fmt)
        except ValueError:
            continue
    raise ValueError(f"第 {index + 1} 个任务的截止时间格式无法识别: {deadline}，请使用 YYYY-MM-DD HH:mm")


def _handler_plan_tasks(
    goal: str,
    tasks: list,
    workspace_id: int = None,
    context: dict = None,
) -> str:
    """生成任务计划：校验 + 解析负责人 → 暂存 Redis（status=pending），等待用户确认"""
    user: User = context["user"]

    # ---- 入参结构校验（LLM 传错格式时给出明确修正提示）----
    goal = (goal or "").strip()
    if not goal:
        return json.dumps({"success": False, "error": "缺少规划目标 goal"}, ensure_ascii=False)
    if not isinstance(tasks, list) or not tasks:
        return json.dumps({"success": False, "error": "任务清单 tasks 不能为空"}, ensure_ascii=False)
    if len(tasks) > _PLAN_MAX_ITEMS:
        return json.dumps({
            "success": False,
            "error": f"一次最多规划 {_PLAN_MAX_ITEMS} 个任务，当前 {len(tasks)} 个，请精简后重试",
        }, ensure_ascii=False)

    raw_ws = workspace_id if workspace_id is not None else context.get("workspace_id")
    ws = raw_ws if (raw_ws and raw_ws > 0) else None

    db = SessionLocal()
    try:
        # ---- 权限前置校验：与 create_task 同规则，避免用户确认后才发现无权创建 ----
        if ws is not None:
            from app.models.workspace import WorkspaceRole
            member = get_workspace_member(ws, user.id, db)
            if member.role == WorkspaceRole.MEMBER:
                return json.dumps({
                    "success": False,
                    "error": "你在当前团队空间是普通成员，不能创建工作区任务，因此无法生成计划",
                }, ensure_ascii=False)

        enriched: list[dict] = []
        for i, item in enumerate(tasks):
            if not isinstance(item, dict):
                return json.dumps({
                    "success": False,
                    "error": f"第 {i + 1} 个任务格式错误：应为对象",
                }, ensure_ascii=False)
            title = str(item.get("title") or "").strip()
            if not title:
                return json.dumps({
                    "success": False,
                    "error": f"第 {i + 1} 个任务缺少标题 title",
                }, ensure_ascii=False)

            priority = item.get("priority") or "medium"
            if priority not in ("low", "medium", "high", "urgent"):
                priority = "medium"

            deadline_dt = None
            deadline_raw = item.get("deadline")
            if deadline_raw:
                try:
                    deadline_dt = _parse_plan_deadline(str(deadline_raw), i)
                except ValueError as e:
                    return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)

            # ---- 解析负责人 ----
            assignee_id = None
            assignee_name = None
            warning = None
            raw_assignee = str(item.get("assignee_name") or "").strip()
            if raw_assignee:
                if ws is None:
                    warning = "个人空间任务仅能分配给自己，已忽略指定负责人"
                else:
                    target = _resolve_workspace_member(db, ws, raw_assignee)
                    if target:
                        assignee_id = target.id
                        assignee_name = target.nickname or target.real_name or target.email
                    else:
                        warning = f"未在当前空间找到成员「{raw_assignee}」，该任务将默认分配给你自己，确认后可手动改派"

            enriched.append({
                "index": i,
                "title": title,
                "description": str(item.get("description") or "").strip() or None,
                "priority": priority,
                "deadline": deadline_dt.strftime("%Y-%m-%d %H:%M") if deadline_dt else None,
                "assignee_id": assignee_id,
                "assignee_name": assignee_name,
                "warning": warning,
            })

        # ---- 暂存 Redis ----
        try:
            from app.db.redis_client import get_redis
            r = get_redis()
        except Exception as e:
            logger.warning(f"[plan_tasks] Redis 不可用: {e}")
            return json.dumps({
                "success": False,
                "error": "任务规划暂存服务暂不可用（Redis 未连接），请稍后重试",
            }, ensure_ascii=False)

        plan_id = uuid.uuid4().hex
        plan_payload = {
            "plan_id": plan_id,
            "user_id": user.id,
            "workspace_id": ws,
            "goal": goal,
            "tasks": enriched,
            "status": "pending",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        r.setex(f"{_PLAN_REDIS_PREFIX}{plan_id}", _PLAN_TTL_SECONDS,
                json.dumps(plan_payload, ensure_ascii=False))

        return json.dumps({
            "success": True,
            "requires_confirmation": True,
            "status": "pending",
            "plan_id": plan_id,
            "goal": goal,
            "task_count": len(enriched),
            "tasks": enriched,
            "expires_in_seconds": _PLAN_TTL_SECONDS,
            "message": f"已生成包含 {len(enriched)} 个任务的计划，等待用户确认",
        }, ensure_ascii=False)
    except Exception as e:
        logger.exception("生成任务计划失败")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    finally:
        db.close()


# ============================================================
# 自动注册入口
# ============================================================

def register_task_tools():
    """将 task 模块的所有工具注册到 ToolRegistry"""
    from app.modules.agent.tool_registry import ToolRegistry

    ToolRegistry.register("create_task", _schema_create_task(), _handler_create_task, group="task")
    ToolRegistry.register("plan_tasks", _schema_plan_tasks(), _handler_plan_tasks, group="task")
    ToolRegistry.register("list_tasks", _schema_list_tasks(), _handler_list_tasks, group="task")
    ToolRegistry.register("complete_task", _schema_complete_task(), _handler_complete_task, group="task")
    ToolRegistry.register("update_task_status", _schema_update_task_status(), _handler_update_task_status, group="task")
    ToolRegistry.register("get_task_detail", _schema_get_task_detail(), _handler_get_task_detail, group="task")

    logger.info("[Agent] task 模块 6 个工具已注册")
