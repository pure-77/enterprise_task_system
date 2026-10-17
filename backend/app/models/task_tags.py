from sqlalchemy import Table, Column, Integer, ForeignKey, Index
from app.db.base import Base

# 任务和标签的多对多关联表 - 面试考点：多对多关系实现
task_tags = Table(
    'task_tags',
    Base.metadata,
    Column('task_id', Integer, ForeignKey('tasks.id'), primary_key=True, comment="任务ID"),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True, comment="标签ID"),
    Index('ix_task_tags_tag_id', 'tag_id'),
)