import hashlib
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.config import settings, get_jwt_secret
from app.db.session import get_db
from app.crud.user import user


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码 - 面试考点：使用bcrypt进行密码验证，自动处理salt"""
    # 使用SHA-256预处理密码
    plain_password = hashlib.sha256(plain_password.encode()).hexdigest()
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def get_password_hash(password: str) -> str:
    """密码加密 - 面试考点：bcrypt算法自动生成salt并存储在hash中，无需单独存储"""
    # 使用SHA-256预处理密码，确保密码长度固定为64字节
    password = hashlib.sha256(password.encode()).hexdigest()
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode(), salt)
    return hashed.decode()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None, db: Session = None) -> str:
    """
    创建访问令牌 - 面试考点：JWT包含过期时间，避免令牌永久有效
    没过期时间 → 严重漏洞
    秘钥太简单 / 硬编码 → 漏洞
    JWT 放敏感信息 → 漏洞
    不用 HTTPS → Token 可被抓包
    
    JWT 密钥动态获取（方案 A：首次启动自动生成持久化到 system_config 表）
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    secret = get_jwt_secret(db)
    encoded_jwt = jwt.encode(to_encode, secret, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, db: Session = None) -> str:
    """
    创建刷新令牌 - 面试考点：刷新令牌有效期更长，用于获取新的访问令牌
    1. Refresh Token 为什么有效期更长？
    因为它的作用是免重新登录，如果太短，用户要频繁登录，体验差。
    2. 为什么要分 Access Token 和 Refresh Token？
    安全设计！
    AccessToken 携带频繁，泄露风险高 → 有效期短，损失小
    RefreshToken 只在刷新时使用，泄露风险低 → 有效期长
    3. type: "refresh" 是干嘛的？
    类型隔离
    避免刷新 Token 被用来直接访问业务接口
    是企业级安全标准写法
    4. 为什么用 UTC 时间？
    避免服务器时区不同导致 Token 提前 / 延后过期。
    5. Refresh Token 泄露了怎么办？
    标准安全方案：
    RefreshToken 只能用一次
    使用后立刻作废（Redis / 数据库黑名单）
    强制用户重新登录
    """
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = data.copy()
    # jti 唯一标识：同秒内生成的 refresh token 也必须不同，
    # 否则 payload 完全一致 → 签名一致 → 轮转发出"相同 token"，重用检测失效
    import secrets as _secrets
    to_encode.update({"exp": expire, "type": "refresh", "jti": _secrets.token_hex(8)})
    secret = get_jwt_secret(db)
    encoded_jwt = jwt.encode(to_encode, secret, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str, db: Session = None) -> Optional[dict]:
    """解码令牌 - 面试考点：处理JWTError异常，验证令牌有效性"""
    try:
        secret = get_jwt_secret(db)
        payload = jwt.decode(token, secret, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """获取当前用户 - 面试考点：JWT令牌验证，用户信息提取"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 解码令牌（传 db → 动态读 system_config 表；不传 → 兜底）
    payload = decode_token(token, db=db)
    if payload is None:
        raise credentials_exception

    # 禁止刷新令牌用于业务接口访问
    if payload.get("type") == "refresh":
        raise credentials_exception

    # 获取用户信息
    email: str = payload.get("sub")
    user_id: int = payload.get("user_id")

    if email is None or user_id is None:
        raise credentials_exception

    # 从数据库获取用户（通过主键user_id查询，比email更高效）
    db_user = user.get(db, id=user_id)
    if db_user is None:
        raise credentials_exception

    return db_user
