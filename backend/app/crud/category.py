from typing import List, Optional
from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate


class CRUDCategory(CRUDBase[Category, CategoryCreate, CategoryUpdate]):
    """分类CRUD操作 - 面试考点：继承基础CRUD类，扩展特定业务逻辑"""
    
    def get_by_user_id(self, db: Session, user_id: int, workspace_id: Optional[int] = None) -> List[Category]:
        """根据用户ID获取分类列表 - 面试考点：关联查询"""
        query = db.query(self.model).filter(self.model.user_id == user_id)
        if workspace_id is not None:
            query = query.filter(self.model.workspace_id == workspace_id)
        else:
            query = query.filter(self.model.workspace_id == None)
        return query.all()

    def get_by_id_and_user_id(self, db: Session, id: int, user_id: int, workspace_id: Optional[int] = None) -> Optional[Category]:
        """根据ID和用户ID获取分类 - 面试考点：多条件查询"""
        query = db.query(self.model).filter(self.model.id == id, self.model.user_id == user_id)
        if workspace_id is not None:
            query = query.filter(self.model.workspace_id == workspace_id)
        return query.first()

    def create(self, db: Session, obj_in: CategoryCreate, user_id: int, workspace_id: Optional[int] = None) -> Category:
        """创建分类 - 面试考点：关联用户ID"""
        obj_in_data = obj_in.model_dump()
        obj_in_data["user_id"] = user_id
        obj_in_data["workspace_id"] = workspace_id
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int, user_id: int, move_to_category_id: Optional[int] = None, workspace_id: Optional[int] = None) -> Optional[Category]:
        """删除分类 - 面试考点：删除前迁移任务"""
        category = self.get_by_id_and_user_id(db, id, user_id, workspace_id)
        if not category:
            return None

        if move_to_category_id:
            target_category = db.query(self.model).filter(
                self.model.id == move_to_category_id
            ).first()
            if target_category:
                for task in category.tasks:
                    task.category_id = move_to_category_id
                db.commit()

        db.delete(category)
        db.commit()
        return category

    def get_with_task_count(self, db: Session, user_id: int, workspace_id: Optional[int] = None) -> List[dict]:
        """获取分类列表及任务数量 - 面试考点：关联统计"""
        from sqlalchemy import func

        query = db.query(
            self.model.id,
            self.model.name,
            self.model.color,
            self.model.user_id,
            self.model.workspace_id,
            self.model.created_at,
            self.model.updated_at,
            func.count(Category.tasks).label('task_count')
        ).outerjoin(
            self.model.tasks
        ).filter(
            self.model.user_id == user_id
        )
        if workspace_id is not None:
            query = query.filter(self.model.workspace_id == workspace_id)
        else:
            query = query.filter(self.model.workspace_id == None)
        result = query.group_by(self.model.id).all()

        return [
            {
                "id": item.id,
                "name": item.name,
                "color": item.color,
                "user_id": item.user_id,
                "workspace_id": item.workspace_id,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
                "task_count": item.task_count
            }
            for item in result
        ]


category = CRUDCategory(Category)