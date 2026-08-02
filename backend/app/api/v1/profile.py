from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from app.db.session import get_db
from app.models.user import User
from app.core.security import get_password_hash, verify_password
from app.api.v1.task import get_current_user_id
import os
import uuid

router = APIRouter()


class UpdateNickname(BaseModel):
    """更新昵称模型 - 面试考点：数据验证"""
    nickname: str = Field(..., min_length=1, max_length=100, description="昵称")


class UpdatePassword(BaseModel):
    """更新密码模型 - 面试考点：密码验证"""
    old_password: str = Field(..., min_length=6, description="旧密码")
    new_password: str = Field(..., min_length=6, max_length=50, description="新密码")


class UpdateEmail(BaseModel):
    """更新邮箱模型 - 面试考点：邮箱验证"""
    email: EmailStr = Field(..., description="新邮箱")
    password: str = Field(..., min_length=6, description="当前密码")


@router.put("/nickname")
async def update_nickname(
    nickname_in: UpdateNickname,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """更新昵称 - 面试考点：个人信息修改"""
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    db_user.nickname = nickname_in.nickname
    db.commit()
    db.refresh(db_user)
    
    # 删除用户缓存 - 面试考点：保持缓存一致性
    from app.services.cache_service import cache_service
    cache_service.delete_user_info(user_id)
    
    return {"message": "昵称修改成功", "nickname": db_user.nickname}


@router.put("/password")
async def update_password(
    password_in: UpdatePassword,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """更新密码 - 面试考点：密码验证"""
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 验证旧密码
    if not verify_password(password_in.old_password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码错误"
        )
    
    # 更新密码
    db_user.hashed_password = get_password_hash(password_in.new_password)
    db.commit()
    
    # 删除用户缓存 - 面试考点：保持缓存一致性
    from app.services.cache_service import cache_service
    cache_service.delete_user_info(user_id)
    
    return {"message": "密码修改成功"}


@router.put("/email")
async def update_email(
    email_in: UpdateEmail,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """更新邮箱 - 面试考点：邮箱修改需验证"""
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 验证当前密码
    if not verify_password(email_in.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密码错误"
        )
    
    # 检查邮箱是否已被使用
    existing_user = db.query(User).filter(
        User.email == email_in.email,
        User.id != user_id
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已被使用"
        )
    
    # 发送验证码
    from app.services.email_service import email_service
    code = await email_service.send_verification_code(email_in.email)
    
    # 临时存储新邮箱和验证码
    from app.services.cache_service import cache_service
    cache_service.set_email_change(user_id, email_in.email, code)
    
    return {"message": "验证码已发送到新邮箱，请查收"}


class VerifyEmailChange(BaseModel):
    """验证邮箱修改模型 - 面试考点：数据验证"""
    email: str = Field(..., description="邮箱")
    code: str = Field(..., description="验证码")


@router.post("/email/verify")
async def verify_email_change(
    data: VerifyEmailChange,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """验证邮箱修改 - 面试考点：验证码验证"""
    from app.services.cache_service import cache_service
    
    # 获取缓存的邮箱信息
    email_info = cache_service.get_email_change(user_id)
    if not email_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码已过期，请重新发送"
        )
    
    # 验证验证码
    if email_info["code"] != data.code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码错误"
        )
    
    # 更新邮箱
    db_user = db.query(User).filter(User.id == user_id).first()
    db_user.email = email_info["email"]
    db.commit()
    
    # 删除缓存
    cache_service.delete_email_change(user_id)
    cache_service.delete_user_info(user_id)
    
    return {"message": "邮箱修改成功"}


class RequestPasswordReset(BaseModel):
    """请求重置密码模型 - 面试考点：数据验证"""
    email: str = Field(..., description="邮箱")


@router.post("/reset-password/request")
async def request_password_reset(
    data: RequestPasswordReset,
    db: Session = Depends(get_db)
):
    """请求重置密码 - 面试考点：忘记密码功能"""
    # 检查邮箱是否存在
    db_user = db.query(User).filter(User.email == data.email).first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="邮箱不存在"
        )
    
    # 发送验证码
    from app.services.email_service import email_service
    code = await email_service.send_verification_code(data.email)
    
    # 存储验证码
    from app.services.cache_service import cache_service
    cache_service.set_password_reset(data.email, code, db_user.id)
    
    return {"message": "验证码已发送到邮箱"}


class VerifyPasswordReset(BaseModel):
    """验证重置密码模型 - 面试考点：数据验证"""
    email: str = Field(..., description="邮箱")
    code: str = Field(..., description="验证码")
    new_password: str = Field(..., min_length=6, max_length=50, description="新密码")


@router.post("/reset-password/verify")
async def verify_password_reset(
    data: VerifyPasswordReset,
    db: Session = Depends(get_db)
):
    """验证重置密码 - 面试考点：密码重置"""
    from app.services.cache_service import cache_service
    
    # 获取缓存的验证码信息
    reset_info = cache_service.get_password_reset(data.email)
    if not reset_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码已过期，请重新发送"
        )
    
    # 验证验证码
    if reset_info["code"] != data.code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码错误"
        )
    
    # 更新密码
    db_user = db.query(User).filter(User.id == reset_info["user_id"]).first()
    db_user.hashed_password = get_password_hash(data.new_password)
    db.commit()
    
    # 删除缓存
    cache_service.delete_password_reset(data.email)
    
    return {"message": "密码重置成功"}


@router.get("/me")
async def get_user_info(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """获取用户信息 - 面试考点：用户信息获取"""
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    return {
        "id": db_user.id,
        "nickname": db_user.nickname,
        "email": db_user.email,
        "avatar": db_user.avatar,
        "created_at": db_user.created_at
    }


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(..., description="头像文件"),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user_id)
):
    """上传头像 - 面试考点：文件上传"""
    # 验证文件类型
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只支持图片文件"
        )
    
    # 读取文件内容
    file_content = await file.read()
    
    # 验证文件大小（限制2MB）
    file_size = len(file_content)
    if file_size > 2 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件大小不能超过2MB"
        )
    
    # 生成文件名
    file_extension = file.filename.split(".")[-1]
    filename = f"{uuid.uuid4().hex}.{file_extension}"
    
    # 保存文件
    upload_dir = "uploads/avatars"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, filename)
    
    with open(file_path, "wb") as buffer:
        buffer.write(file_content)
    
    # 更新用户头像
    db_user = db.query(User).filter(User.id == user_id).first()
    db_user.avatar = f"/uploads/avatars/{filename}"
    db.commit()
    
    # 删除用户缓存 - 面试考点：保持缓存一致性
    from app.services.cache_service import cache_service
    cache_service.delete_user_info(user_id)
    
    return {"message": "头像上传成功", "avatar_url": db_user.avatar}