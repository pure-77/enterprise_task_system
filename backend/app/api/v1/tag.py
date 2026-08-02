from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.session import get_db
from app.schemas.tag import TagCreate, TagUpdate, TagResponse
from app.crud.tag import tag as tag_crud
from app.api.v1.task import get_current_user_id

router = APIRouter()


@router.post("", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
async def create_tag(
    tag_in: TagCreate,
    workspace_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """创建标签 - 面试考点：权限校验"""
    existing_tag = tag_crud.get_by_name(db, tag_in.name, user_id, workspace_id)
    if existing_tag:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="标签名称已存在")
    return tag_crud.create(db, tag_in.model_dump(), user_id, workspace_id)


@router.get("", response_model=List[TagResponse])
async def get_tags(
    skip: int = 0,
    limit: int = 100,
    workspace_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """获取标签列表 - 面试考点：分页查询"""
    return tag_crud.get_multi(db, user_id, skip, limit, workspace_id)


@router.get("/{tag_id}", response_model=TagResponse)
async def get_tag(
    tag_id: int,
    workspace_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """获取单个标签 - 面试考点：权限校验"""
    db_tag = tag_crud.get_by_id(db, tag_id, user_id, workspace_id)
    if not db_tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="标签不存在")
    return db_tag


@router.put("/{tag_id}", response_model=TagResponse)
async def update_tag(
    tag_id: int,
    tag_in: TagUpdate,
    workspace_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """更新标签 - 面试考点：权限校验"""
    db_tag = tag_crud.get_by_id(db, tag_id, user_id, workspace_id)
    if not db_tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="标签不存在")
    if tag_in.name:
        existing_tag = tag_crud.get_by_name(db, tag_in.name, user_id, workspace_id)
        if existing_tag and existing_tag.id != tag_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="标签名称已被使用")
    return tag_crud.update(db, db_tag, tag_in.model_dump(exclude_unset=True))


@router.delete("/{tag_id}")
async def delete_tag(
    tag_id: int,
    workspace_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """删除标签 - 面试考点：权限校验"""
    success = tag_crud.delete(db, tag_id, user_id, workspace_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="标签不存在")
    return {"message": "标签删除成功"}