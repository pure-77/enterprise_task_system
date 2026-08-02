from typing import Optional
from sqlalchemy.orm import Session
from app.crud.base import CRUDBase
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    """用户CRUD操作 - 面试考点：继承基础CRUD类，扩展特定业务逻辑"""
    
    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        """根据邮箱获取用户 - 面试考点：查询唯一索引字段"""
        return db.query(User).filter(User.email == email).first()
    
    def create(self, db: Session, obj_in: UserCreate) -> User:
        """创建用户 - 面试考点：密码加密后再存储"""
        from app.core.security import get_password_hash
        
        obj_in_data = obj_in.model_dump()
        obj_in_data["hashed_password"] = get_password_hash(obj_in_data.pop("password"))
        obj_in_data.pop("verify_code", None)
        db_obj = User(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def is_email_exists(self, db: Session, email: str) -> bool:
        """检查邮箱是否存在 - 面试考点：用于注册时校验邮箱唯一性"""
        return db.query(User).filter(User.email == email).first() is not None


user = CRUDUser(User)
