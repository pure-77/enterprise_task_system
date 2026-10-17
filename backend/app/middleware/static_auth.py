"""静态文件认证中间件 — 保护 /uploads 路径，仅登录用户可访问"""
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from app.core.security import decode_token

logger = logging.getLogger("static_auth")


class StaticAuthMiddleware(BaseHTTPMiddleware):
    """拦截 /uploads 请求，验证 JWT token
    支持 Authorization header 和 ?token= 查询参数两种方式
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # 只拦截 /uploads 路径
        if not path.startswith("/uploads"):
            return await call_next(request)

        # 提取 token: 优先 Authorization header, 其次 query parameter
        token = None
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
        if not token:
            token = request.query_params.get("token")

        # 无 token
        if not token:
            return JSONResponse(
                status_code=401,
                content={"code": 401, "message": "请先登录后访问", "data": None}
            )

        # 验证 token
        payload = decode_token(token)
        if not payload:
            return JSONResponse(
                status_code=401,
                content={"code": 401, "message": "Token无效或已过期", "data": None}
            )

        # 禁止 refresh token 访问静态资源
        if payload.get("type") == "refresh":
            return JSONResponse(
                status_code=401,
                content={"code": 401, "message": "无效的访问令牌", "data": None}
            )

        return await call_next(request)
