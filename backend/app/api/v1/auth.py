from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.user import UserCreate, UserResponse, VerifyCodeRequest, VerifyCodeResponse, UserLogin, Token, RefreshTokenRequest
from app.crud.user import user
from app.services.email_service import email_service
from app.services.cache_service import cache_service
from app.core.exceptions import (
    EmailAlreadyExistsException,
    InvalidVerifyCodeException,
    VerifyCodeSendTooFrequentlyException
)
from app.core.security import create_access_token, create_refresh_token

router = APIRouter()


@router.post("/send-verify-code", response_model=VerifyCodeResponse)
async def send_verify_code(
    request: VerifyCodeRequest,
    db: Session = Depends(get_db)
):
    """发送验证码接口 - 面试考点：异步发送邮件，防刷机制"""
    email = request.email
    
    # 检查邮箱是否已注册 - 面试考点：注册前检查邮箱唯一性
    if user.is_email_exists(db, email):
        raise EmailAlreadyExistsException()
    
    # 检查是否可以发送验证码 - 面试考点：防刷机制，1分钟内只能发送1次
    if not cache_service.can_send_verify_code(email):
        remaining_time = cache_service.get_remaining_time(email)
        raise VerifyCodeSendTooFrequentlyException()
    
    # 生成验证码 - 面试考点：6位随机数字
    code = email_service.generate_verify_code(6)
    print(f"生成的验证码: {code} for {email}")
    
    # 存储验证码到Redis - 面试考点：设置5分钟过期时间
    cache_service.set_verify_code(email, code)
    
    # 记录发送时间 - 面试考点：用于防刷机制
    cache_service.set_send_time(email)
    
    # 异步发送邮件 — 投递到 Celery Worker，不阻塞响应
    from app.tasks.email_tasks import send_verify_code_email
    send_verify_code_email.delay(email, code)
    
    return VerifyCodeResponse(
        message="验证码已发送到您的邮箱",
        remaining_time=60
    )


@router.post("/register", response_model=UserResponse)
async def register(
    user_in: UserCreate,
    db: Session = Depends(get_db)
):
    """用户注册接口 - 面试考点：验证码校验、密码加密、邮箱唯一性"""
    
    print(f"收到注册请求，email: {user_in.email}, verify_code: {user_in.verify_code}")
    
    # 检查邮箱是否已注册 - 面试考点：数据库唯一性校验
    if user.is_email_exists(db, user_in.email):
        print(f"邮箱已注册: {user_in.email}")
        raise EmailAlreadyExistsException()
    
    # 验证验证码 - 面试考点：从Redis读取验证码进行校验
    # print(f"开始验证验证码...")
    stored_code = cache_service.get_verify_code(user_in.email)
    # print(f"存储的验证码: {stored_code}, 输入的验证码: {user_in.verify_code}")
    if not stored_code or stored_code != user_in.verify_code:
        # print(f"验证码验证失败: stored_code={stored_code}, input={user_in.verify_code}")
        raise InvalidVerifyCodeException()
    
    # 创建用户 - 面试考点：密码在CRUD层加密
    print(f"验证码验证成功，创建用户: {user_in.email}")
    db_user = user.create(db, user_in)
    
    # 删除验证码 - 面试考点：验证码使用后删除，防止重复使用
    cache_service.delete_verify_code(user_in.email)
    print(f"用户创建成功: {db_user.id}")
    
    return db_user


@router.post("/login", response_model=Token)
async def login(
    user_in: UserLogin,
    db: Session = Depends(get_db)
):
    """用户登录接口 - 面试考点：密码验证、JWT令牌生成、刷新令牌存储"""
    from app.core.security import verify_password
    
    # 查找用户 - 面试考点：根据邮箱查询用户
    db_user = user.get_by_email(db, user_in.email)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误"
        )
    
    # 验证密码 - 面试考点：使用bcrypt验证密码
    if not verify_password(user_in.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误"
        )
    
    # 生成JWT令牌 - 面试考点：包含用户信息和过期时间
    access_token = create_access_token(data={"sub": db_user.email, "user_id": db_user.id}, db=db)
    refresh_token = create_refresh_token(data={"sub": db_user.email, "user_id": db_user.id}, db=db)
    
    # 存储刷新令牌到Redis - 面试考点：使用用户ID作为key，设置7天过期
    cache_service.set_refresh_token(db_user.id, refresh_token)
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )

# 
@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    """刷新令牌接口 - 面试考点：使用刷新令牌获取新的访问令牌，含重用检测"""
    import hashlib
    from app.core.security import decode_token, create_access_token, create_refresh_token

    refresh_token = request.refresh_token

    # 解码刷新令牌 - 传 db 确保冷启动时也能从 system_config 表读到正确的签名密钥
    payload = decode_token(refresh_token, db=db)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌"
        )

    # 获取用户ID - 面试考点：从令牌中提取用户信息
    user_id = payload.get("user_id")
    email = payload.get("sub")

    if not user_id or not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的刷新令牌"
        )

    # 计算令牌哈希用于重用检测
    token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()

    # 从Redis中获取存储的当前有效刷新令牌
    stored_refresh_token = cache_service.get_refresh_token(user_id)

    # 判断令牌是否匹配当前有效令牌
    if stored_refresh_token and stored_refresh_token == refresh_token:
        # 令牌匹配，可以正常轮转
        pass
    elif cache_service.is_refresh_token_used(user_id, token_hash):
        # 令牌不匹配但曾被使用过（多标签页或重放攻击）
        # 只拒绝请求，不删除当前有效令牌，避免误伤其他标签页
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="刷新令牌已被使用，请使用最新的令牌"
        )
    elif not stored_refresh_token:
        # Redis 无记录（Redis 重启/缓存被清）——JWT 本身验签+有效期已通过上面的 decode_token 校验，
        # 信任该令牌并回种 Redis，避免 Redis 数据丢失后所有用户被迫重新登录
        cache_service.set_refresh_token(user_id, refresh_token)
    else:
        # 令牌不是当前有效令牌，也未被使用过（已过期或无效）
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="刷新令牌已过期或无效"
        )

    # 标记旧令牌为已使用（令牌轮转 + 重用检测）
    cache_service.mark_refresh_token_used(user_id, token_hash)

    # 生成新的访问令牌 - 面试考点：创建新的access_token
    new_access_token = create_access_token(data={"sub": email, "user_id": user_id})

    # 生成新的刷新令牌 - 面试考点：同时更新refresh_token
    new_refresh_token = create_refresh_token(data={"sub": email, "user_id": user_id})

    # 存入redis因为jwt本身是不会自动销毁的，更新Redis中的刷新令牌 - 面试考点：存储新的refresh_token
    cache_service.set_refresh_token(user_id, new_refresh_token)

    return Token(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer"
    )


@router.post("/logout")
async def logout(
    authorization: str = Header(None, alias="Authorization")
):
    """用户退出登录接口 - 面试考点：删除刷新令牌，使令牌失效"""
    from app.core.security import decode_token
    
    # 验证Authorization头 - 面试考点：检查token是否存在
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证令牌"
        )
    
    # 提取token - 面试考点：从"Bearer {token}"格式中提取token
    try:
        token = authorization.replace("Bearer ", "")
    except:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌格式"
        )
    
    # 解码token - 面试考点：验证token有效性并获取用户信息
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌"
        )
    
    # 获取用户ID - 面试考点：从token中提取用户信息
    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌"
        )
    
    # 删除Redis中的刷新令牌 - 面试考点：使刷新令牌失效
    cache_service.delete_refresh_token(user_id)

    # 失效用户所有缓存
    cache_service.invalidate_user_all_caches(user_id)

    return {
        "message": "退出登录成功"
    }
