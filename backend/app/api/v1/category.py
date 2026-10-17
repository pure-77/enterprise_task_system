from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.session import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse, CategoryWithTaskCount
from app.crud.category import category
from app.services.cache_service import cache_service

router = APIRouter()


@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category_in: CategoryCreate,
    workspace_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建分类 — workspace_id 优先从 body 读取（前端 POST JSON），query param 作兼容"""
    # 优先 body 里的，其次 query param
    effective_ws_id = category_in.workspace_id if category_in.workspace_id is not None else workspace_id
    db_category = category.create(db, category_in, current_user.id, effective_ws_id)
    cache_service.delete_user_categories(current_user.id)
    return db_category


@router.get("/", response_model=List[CategoryWithTaskCount])
async def get_categories(
    workspace_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户的分类列表 - 面试考点：缓存优化，用户认证"""
    categories = category.get_with_task_count(db, current_user.id, workspace_id)
    return categories


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: int,
    workspace_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取单个分类 - 面试考点：权限控制"""
    db_category = category.get_by_id_and_user_id(db, category_id, current_user.id, workspace_id)
    if not db_category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分类不存在")
    return db_category


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    category_in: CategoryUpdate,
    workspace_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新分类 - 面试考点：权限控制，数据验证"""
    db_category = category.get_by_id_and_user_id(db, category_id, current_user.id, workspace_id)
    if not db_category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分类不存在")
    db_category = category.update(db, db_category, category_in)
    cache_service.delete_user_categories(current_user.id)
    return db_category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    move_to_category_id: Optional[int] = None,
    workspace_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除分类 - 面试考点：任务迁移，权限控制"""
    deleted_category = category.delete(db, category_id, current_user.id, move_to_category_id, workspace_id)
    if not deleted_category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="分类不存在")
    cache_service.delete_user_categories(current_user.id)
    return None