from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional, Tuple
from app.models.task import Task, TaskStatus, TaskPriority
from app.models.workspace import WorkspaceMember, WorkspaceRole
from app.schemas.task import TaskCreate, TaskUpdate, TaskFilter
from datetime import datetime


class TaskCRUD:
    """任务CRUD操作类 - 面试考点：封装数据库操作"""
    
    def create(self, db: Session, task_in: TaskCreate, user_id: int) -> Task:
        """创建任务"""
        tags = task_in.tags or []
        assignee_ids = task_in.assignee_ids or []
        task_data = task_in.model_dump(exclude={'tags', 'assignee_ids'})

        db_task = Task(**task_data, user_id=user_id)
        db.add(db_task)
        db.commit()
        db.refresh(db_task)

        # 关联标签
        if tags:
            from app.models.tag import Tag
            tag_query = db.query(Tag).filter(Tag.id.in_(tags))
            if task_in.workspace_id:
                tag_query = tag_query.filter(Tag.workspace_id == task_in.workspace_id)
            else:
                tag_query = tag_query.filter(Tag.user_id == user_id, Tag.workspace_id == None)
            db_task.tags = tag_query.all()

        # 关联多人分配
        if assignee_ids:
            from app.models.user import User
            assignee_objs = db.query(User).filter(User.id.in_(assignee_ids)).all()
            db_task.assignees = assignee_objs

        if tags or assignee_ids:
            db.commit()
            db.refresh(db_task)

        return db_task
    
    def get_task_with_permission(self, db: Session, task_id: int, user_id: int) -> Optional[Task]:
        """根据ID获取任务，含完整权限校验

        个人任务：仅创建者可读
        团队任务：需为 workspace 成员
          - OWNER/ADMIN：可读任何团队任务
          - MEMBER：只能读分配给自己的 / 自己创建的 / 团队公开的
        """
        from app.services.task_status_service import get_beijing_time

        task = db.query(Task).filter(Task.id == task_id, Task.is_active == True).first()
        if not task:
            return None

        # 检查逾期状态
        if (task.status in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS] and
            task.due_date and task.due_date < get_beijing_time()):
            task.status = TaskStatus.OVERDUE
            db.commit()
            db.refresh(task)

        # 个人任务 → 仅创建者可读
        if task.workspace_id is None:
            if task.user_id != user_id:
                return None
            self._load_task_relations(db, task)
            return task

        # 团队任务 → 检查 workspace 成员身份
        member = db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == task.workspace_id,
            WorkspaceMember.user_id == user_id,
            WorkspaceMember.is_active == True
        ).first()

        if not member:
            return None

        # OWNER/ADMIN → 可读任何团队任务
        if member.role in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN]:
            self._load_task_relations(db, task)
            return task

        # 普通成员 → 只能读分配给自己的 / 自己创建的 / 团队公开的
        # 多人的 assignees 也检查
        is_assignee = task.assignee_id == user_id or any(
            a.id == user_id for a in task.assignees
        )
        if is_assignee or task.user_id == user_id or task.is_team_wide:
            self._load_task_relations(db, task)
            return task

        return None

    def get_by_id(self, db: Session, task_id: int, user_id: int) -> Optional[Task]:
        """根据ID获取任务 - 委托给 get_task_with_permission"""
        return self.get_task_with_permission(db, task_id, user_id)

    def _load_task_relations(self, db: Session, task: Task):
        """加载任务关联数据：分类、标签、被分配人、完成记录"""
        db.refresh(task, ['category', 'tags', 'assignees'])
    
    def get_multi(
        self,
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 100,
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
        category_id: Optional[int] = None,
        tag_id: Optional[int] = None,
        keyword: Optional[str] = None,
        due_date_start: Optional[datetime] = None,
        due_date_end: Optional[datetime] = None,
        workspace_id: Optional[int] = None,
        assignee_id: Optional[int] = None
    ) -> Tuple[List[Task], int]:
        """获取任务列表 - 支持 workspace 角色权限过滤"""
        from app.services.task_status_service import TaskStatusService

        TaskStatusService.check_overdue_tasks(db)

        query = db.query(Task).filter(Task.is_active == True)

        if workspace_id is not None:
            # 团队空间：先校验成员身份
            member = db.query(WorkspaceMember).filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
                WorkspaceMember.is_active == True
            ).first()
            if not member:
                return [], 0

            query = query.filter(Task.workspace_id == workspace_id)

            if member.role not in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN]:
                # 普通成员 → 分配给自己 + 自己创建的 + 团队公开的 + 多人分配中包含自己
                from app.models.task_assignee import task_assignees
                query = query.outerjoin(
                    task_assignees,
                    Task.id == task_assignees.c.task_id
                ).filter(
                    or_(
                        Task.assignee_id == user_id,
                        Task.user_id == user_id,
                        Task.is_team_wide == True,
                        task_assignees.c.user_id == user_id
                    )
                )
        else:
            # 个人空间 → 只看自己的
            query = query.filter(
                Task.user_id == user_id,
                Task.workspace_id == None
            )

        # 状态筛选
        if status:
            query = query.filter(Task.status == status)

        # 优先级筛选
        if priority:
            query = query.filter(Task.priority == priority)

        # 分类筛选
        if category_id:
            query = query.filter(Task.category_id == category_id)

        # 指派人筛选
        if assignee_id:
            query = query.filter(Task.assignee_id == assignee_id)

        if tag_id:
            from app.models.tag import Tag
            query = query.join(Task.tags).filter(Tag.id == tag_id)

        # 关键词搜索
        if keyword:
            query = query.filter(
                or_(
                    Task.title.like(f"%{keyword}%"),
                    Task.description.like(f"%{keyword}%")
                )
            )

        # 截止日期范围筛选
        if due_date_start:
            query = query.filter(Task.due_date >= due_date_start)
        if due_date_end:
            query = query.filter(Task.due_date <= due_date_end)

        total = query.count()

        tasks = query.order_by(
            Task.due_date.asc(),
            Task.priority.desc()
        ).offset(skip).limit(limit).all()

        return tasks, total
    
    def update(self, db: Session, db_task: Task, task_in: TaskUpdate) -> Task:
        """更新任务"""
        update_data = task_in.model_dump(exclude_unset=True)

        # 处理标签
        if 'tags' in update_data:
            tags = update_data.pop('tags') or []
            from app.models.tag import Tag
            tag_query = db.query(Tag).filter(Tag.id.in_(tags))
            if db_task.workspace_id:
                tag_query = tag_query.filter(Tag.workspace_id == db_task.workspace_id)
            else:
                tag_query = tag_query.filter(Tag.user_id == db_task.user_id, Tag.workspace_id == None)
            db_task.tags = tag_query.all()

        # 处理多人分配
        if 'assignee_ids' in update_data:
            assignee_ids = update_data.pop('assignee_ids') or []
            if assignee_ids:
                from app.models.user import User
                assignee_objs = db.query(User).filter(User.id.in_(assignee_ids)).all()
                db_task.assignees = assignee_objs
            else:
                db_task.assignees = []

        # 更新其他字段
        for field, value in update_data.items():
            setattr(db_task, field, value)

        db.commit()
        db.refresh(db_task)
        return db_task
    
    def delete(self, db: Session, task_id: int, user_id: int) -> Optional[Task]:
        """删除任务 - 面试考点：权限校验"""
        db_task = self.get_by_id(db, task_id, user_id)
        if db_task:
            db.delete(db_task)
            db.commit()
        return db_task
    
    def batch_delete(self, db: Session, task_ids: List[int], user_id: int, workspace_id: int = None) -> int:
        """批量删除任务 - 面试考点：批量操作"""
        filters = [Task.id.in_(task_ids)]
        if workspace_id is not None:
            filters.append(Task.workspace_id == workspace_id)
        else:
            filters.append(and_(Task.user_id == user_id, Task.workspace_id == None))
        count = db.query(Task).filter(and_(*filters)).delete(synchronize_session=False)
        db.commit()
        return count

    def batch_update_status(
        self,
        db: Session,
        task_ids: List[int],
        user_id: int,
        status: TaskStatus,
        workspace_id: int = None
    ) -> int:
        """批量更新任务状态 - 面试考点：一键标记完成"""
        filters = [Task.id.in_(task_ids)]
        if workspace_id is not None:
            filters.append(Task.workspace_id == workspace_id)
        else:
            filters.append(and_(Task.user_id == user_id, Task.workspace_id == None))
        count = db.query(Task).filter(and_(*filters)).update(
            {"status": status}, synchronize_session=False
        )
        db.commit()
        return count

    def batch_update(
        self,
        db: Session,
        task_ids: List[int],
        user_id: int,
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
        category_id: Optional[int] = None,
        workspace_id: int = None
    ) -> int:
        """批量更新任务 - 面试考点：支持多个字段的批量更新"""
        update_data = {}
        if status:
            update_data["status"] = status
        if priority:
            update_data["priority"] = priority
        if category_id:
            update_data["category_id"] = category_id

        if not update_data:
            return 0

        filters = [Task.id.in_(task_ids)]
        if workspace_id is not None:
            filters.append(Task.workspace_id == workspace_id)
        else:
            filters.append(and_(Task.user_id == user_id, Task.workspace_id == None))
        count = db.query(Task).filter(and_(*filters)).update(update_data, synchronize_session=False)
        db.commit()
        return count


task = TaskCRUD()