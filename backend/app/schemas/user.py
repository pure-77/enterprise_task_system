from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    """用户基础模型 - 面试考点：定义公共字段"""
    email: EmailStr = Field(..., description="邮箱")
    nickname: str = Field(..., min_length=2, max_length=50, description="昵称")


class UserCreate(UserBase):
    """用户创建模型 - 面试考点：注册时的数据验证"""
    password: str = Field(..., min_length=6, max_length=50, description="密码")
    verify_code: str = Field(..., min_length=6, max_length=6, description="验证码")
    
    @validator('password')
    def password_strength(cls, v):
        """密码强度验证 - 面试考点：自定义验证器"""
        if len(v) < 6:
            raise ValueError('密码长度不能少于6位')
        return v


class UserUpdate(BaseModel):
    """用户更新模型 - 面试考点：部分字段可选"""
    nickname: Optional[str] = Field(None, min_length=2, max_length=50, description="昵称")
    avatar: Optional[str] = Field(None, description="头像URL")


class UserInDB(UserBase):
    """数据库中的用户模型 - 面试考点：包含内部字段"""
    id: int
    hashed_password: str
    avatar: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True  # 面试考点：支持ORM模型转换


class UserResponse(UserBase):
    """用户响应模型 - 面试考点：返回给前端的数据"""
    id: int
    avatar: Optional[str] = None
    created_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    """用户登录模型 - 面试考点：登录时的数据验证"""
    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., description="密码")


class Token(BaseModel):
    """令牌模型 - 面试考点：JWT令牌响应"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """令牌数据模型 - 面试考点：JWT解码后的数据"""
    email: Optional[str] = None


class VerifyCodeRequest(BaseModel):
    """验证码请求模型 - 面试考点：发送验证码的请求"""
    email: EmailStr = Field(..., description="邮箱")


class VerifyCodeResponse(BaseModel):
    """验证码响应模型 - 面试考点：返回剩余等待时间"""
    message: str
    remaining_time: int = Field(..., description="剩余等待时间（秒）")


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求模型 - 面试考点：用于token刷新"""
    refresh_token: str = Field(..., description="刷新令牌")
