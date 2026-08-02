from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.tag import Tag


class TagCRUD:
    """标签CRUD操作 - 面试考点：基础CRUD操作"""
    
    def get_by_id(self, db: Session, tag_id: int, user_id: int, workspace_id: Optional[int] = None) -> Optional[Tag]:
        """根据ID获取标签 - 面试考点：权限校验"""
        query = db.query(Tag).filter(Tag.id == tag_id, Tag.is_active == True)
        if workspace_id is not None:
            query = query.filter(Tag.workspace_id == workspace_id)
        else:
            query = query.filter(Tag.user_id == user_id, Tag.workspace_id == None)
        return query.first()

    def get_multi(self, db: Session, user_id: int, skip: int = 0, limit: int = 100, workspace_id: Optional[int] = None) -> List[Tag]:
        """获取用户标签列表 - 面试考点：分页查询"""
        query = db.query(Tag).filter(Tag.is_active == True)
        if workspace_id is not None:
            query = query.filter(Tag.workspace_id == workspace_id)
        else:
            query = query.filter(Tag.user_id == user_id, Tag.workspace_id == None)
        return query.order_by(Tag.created_at.desc()).offset(skip).limit(limit).all()

    def create(self, db: Session, tag_in: dict, user_id: int, workspace_id: Optional[int] = None) -> Tag:
        """创建标签 - 面试考点：数据验证"""
        db_tag = Tag(
            name=tag_in.get("name"),
            color=tag_in.get("color", "#409EFF"),
            user_id=user_id,
            workspace_id=workspace_id
        )
        db.add(db_tag)
        db.commit()
        db.refresh(db_tag)
        return db_tag
    
    def update(self, db: Session, db_tag: Tag, tag_in: dict) -> Tag:
        """更新标签 - 面试考点：部分更新"""
        if "name" in tag_in:
            db_tag.name = tag_in["name"]
        if "color" in tag_in:
            db_tag.color = tag_in["color"]
        db.commit()
        db.refresh(db_tag)
        return db_tag
    
    def delete(self, db: Session, tag_id: int, user_id: int, workspace_id: Optional[int] = None) -> bool:
        """删除标签 - 面试考点：软删除"""
        db_tag = self.get_by_id(db, tag_id, user_id, workspace_id)
        if db_tag:
            db_tag.is_active = False
            db.commit()
            return True
        return False
    
    def get_by_name(self, db: Session, name: str, user_id: int, workspace_id: Optional[int] = None) -> Optional[Tag]:
        """根据名称获取标签 - 面试考点：唯一性校验"""
        query = db.query(Tag).filter(Tag.name == name, Tag.is_active == True)
        if workspace_id is not None:
            query = query.filter(Tag.workspace_id == workspace_id)
        else:
            query = query.filter(Tag.user_id == user_id, Tag.workspace_id == None)
        return query.first()


tag = TagCRUD()