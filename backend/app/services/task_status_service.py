from datetime import datetime
import pytz
from sqlalchemy.orm import Session
from app.models.task import Task, TaskStatus

# 北京时区
BEIJING_TZ = pytz.timezone('Asia/Shanghai')

def get_beijing_time():
    """获取当前北京时区时间"""
    return datetime.now(BEIJING_TZ).replace(tzinfo=None)


class TaskStatusService:
    """任务状态服务 - 处理任务状态更新"""
    
    @staticmethod
    def check_overdue_tasks(db: Session):
        """检查并更新逾期任务状态
        
        检查所有待办或进行中的任务，若截止日期已过，则更新为逾期状态
        """
        now = get_beijing_time()
        
        # 查找所有待办或进行中且截止日期已过的任务
        overdue_tasks = db.query(Task).filter(
            Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS]),
            Task.due_date < now,
            Task.due_date.isnot(None)
        ).all()
        
        # 更新状态为逾期
        for task in overdue_tasks:
            task.status = TaskStatus.OVERDUE
        
        if overdue_tasks:
            db.commit()
        
        return len(overdue_tasks)
    
    @staticmethod
    def get_task_with_status(db: Session, task_id: int, user_id: int):
        """获取任务时检查状态
        
        在获取任务详情时，检查任务是否已逾期，若逾期则更新状态
        """
        task = db.query(Task).filter(
            Task.id == task_id,
            Task.user_id == user_id
        ).first()
        
        if task:
            # 检查是否逾期
            if (task.status in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS] and
                task.due_date and task.due_date < get_beijing_time()):
                task.status = TaskStatus.OVERDUE
                db.commit()
                db.refresh(task)
        
        return task
