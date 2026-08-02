from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_, case
from sqlalchemy.orm import Session
from app.models.task import Task, TaskStatus
from app.models.category import Category

class StatisticsCRUD:
    """统计CRUD操作 - 面试考点：分组/聚合查询"""

    def _task_filter(self, user_id: int, workspace_id: Optional[int] = None):
        """构建任务查询过滤条件"""
        if workspace_id is not None:
            return [Task.workspace_id == workspace_id, Task.is_active == True]
        return [Task.user_id == user_id, Task.workspace_id == None, Task.is_active == True]

    def _category_filter(self, user_id: int, workspace_id: Optional[int] = None):
        if workspace_id is not None:
            return [Category.workspace_id == workspace_id, Category.is_active == True]
        return [Category.user_id == user_id, Category.workspace_id == None, Category.is_active == True]

    def get_overview(self, db: Session, user_id: int, workspace_id: Optional[int] = None) -> Dict[str, Any]:
        filters = self._task_filter(user_id, workspace_id)
        total_tasks = db.query(func.count(Task.id)).filter(and_(*filters)).scalar() or 0
        today = datetime.now().date()
        today_tasks = db.query(func.count(Task.id)).filter(
            and_(*filters),
            Task.status == TaskStatus.PENDING,
            func.date(Task.due_date) == today
        ).scalar() or 0
        week_start = today - timedelta(days=today.weekday())
        week_completed = db.query(func.count(Task.id)).filter(
            and_(*filters),
            Task.status == TaskStatus.COMPLETED,
            func.date(Task.updated_at) >= week_start
        ).scalar() or 0
        completed_tasks = db.query(func.count(Task.id)).filter(
            and_(*filters),
            Task.status == TaskStatus.COMPLETED
        ).scalar() or 0
        completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        return {
            "total_tasks": total_tasks,
            "today_tasks": today_tasks,
            "week_completed": week_completed,
            "completion_rate": round(completion_rate, 2)
        }

    def get_category_stats(self, db: Session, user_id: int, workspace_id: Optional[int] = None) -> List[Dict[str, Any]]:
        cat_filters = self._category_filter(user_id, workspace_id)
        stats = db.query(
            Category.name,
            func.count(Task.id).label('task_count'),
            func.sum(case((Task.status == TaskStatus.COMPLETED, 1), else_=0)).label('completed_count')
        ).outerjoin(
            Task, and_(Task.category_id == Category.id, Task.is_active == True)
        ).filter(
            and_(*cat_filters)
        ).group_by(Category.id, Category.name).all()
        result = []
        for stat in stats:
            task_count = stat.task_count or 0
            completed_count = int(stat.completed_count or 0)
            completion_rate = (completed_count / task_count * 100) if task_count > 0 else 0
            result.append({
                "category_name": stat.name,
                "task_count": task_count,
                "completed_count": completed_count,
                "completion_rate": round(completion_rate, 2)
            })
        return result

    def get_status_stats(self, db: Session, user_id: int, workspace_id: Optional[int] = None) -> List[Dict[str, Any]]:
        filters = self._task_filter(user_id, workspace_id)
        stats = db.query(
            Task.status,
            func.count(Task.id).label('task_count')
        ).filter(and_(*filters)).group_by(Task.status).all()
        status_map = {
            TaskStatus.PENDING: "待办", TaskStatus.IN_PROGRESS: "进行中",
            TaskStatus.COMPLETED: "已完成", TaskStatus.CANCELLED: "已取消",
            TaskStatus.OVERDUE: "已逾期"
        }
        return [{"status": stat.status, "status_name": status_map.get(stat.status, stat.status),
                  "task_count": stat.task_count} for stat in stats]

    def get_completion_trend(self, db: Session, user_id: int, days: int = 7, workspace_id: Optional[int] = None) -> List[Dict[str, Any]]:
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days-1)
        filters = self._task_filter(user_id, workspace_id)
        stats = db.query(
            func.date(Task.updated_at).label('date'),
            func.count(Task.id).label('completed_count')
        ).filter(
            and_(*filters),
            Task.status == TaskStatus.COMPLETED,
            func.date(Task.updated_at) >= start_date,
            func.date(Task.updated_at) <= end_date
        ).group_by(func.date(Task.updated_at)).all()
        completion_dict = {str(stat.date): stat.completed_count for stat in stats}
        date_range = []
        current_date = start_date
        while current_date <= end_date:
            date_range.append(current_date)
            current_date += timedelta(days=1)
        return [{"date": str(date), "completed_count": completion_dict.get(str(date), 0)} for date in date_range]

    def get_export_data(self, db: Session, user_id: int, workspace_id: Optional[int] = None) -> List[Dict[str, Any]]:
        filters = self._task_filter(user_id, workspace_id)
        tasks = db.query(
            Task, Category.name.label('category_name')
        ).outerjoin(
            Category, Task.category_id == Category.id
        ).filter(and_(*filters)).all()
        status_map = {
            TaskStatus.PENDING: "待办", TaskStatus.IN_PROGRESS: "进行中",
            TaskStatus.COMPLETED: "已完成", TaskStatus.CANCELLED: "已取消",
            TaskStatus.OVERDUE: "已逾期"
        }
        priority_map = {"low": "低", "medium": "中", "high": "高", "urgent": "紧急"}
        return [{
            "id": task.id, "title": task.title, "description": task.description or "",
            "category": category_name, "status": status_map.get(task.status, task.status),
            "priority": priority_map.get(task.priority, task.priority),
            "due_date": task.due_date.strftime("%Y-%m-%d %H:%M") if task.due_date else "",
            "created_at": task.created_at.strftime("%Y-%m-%d %H:%M"),
            "updated_at": task.updated_at.strftime("%Y-%m-%d %H:%M")
        } for task, category_name in tasks]


statistics = StatisticsCRUD()