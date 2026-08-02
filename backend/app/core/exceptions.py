"""企业级异常体系 — 包含错误码的企业级异常 + 保留旧版兼容"""
from fastapi import HTTPException, status
from typing import Optional, Any


# ============================================================
# 新版：错误码异常体系 — 业务代码推荐使用
# ============================================================

class AppCodeException(HTTPException):
    """基于错误码的应用异常 — 新模块推荐使用"""

    def __init__(self, code: int, message: str, detail: str = None, http_status: int = 200):
        self.code = code
        self.err_message = message
        self.detail = detail
        body = {"code": code, "message": message, "data": None}
        if detail:
            body["detail"] = detail
        super().__init__(status_code=http_status, detail=body)


# ---------- 认证模块 401xx ----------
class UnauthorizedError(AppCodeException):
    def __init__(self, detail: str = "未授权访问"):
        super().__init__(code=40101, message="未授权访问", detail=detail, http_status=401)


class TokenExpiredError(AppCodeException):
    def __init__(self):
        super().__init__(code=40102, message="Token已过期", detail="请重新登录", http_status=401)


# ---------- 权限模块 403xx ----------
class PermissionDeniedError(AppCodeException):
    def __init__(self, detail: str = "没有操作权限"):
        super().__init__(code=40301, message="权限不足", detail=detail, http_status=403)


# ---------- 资源模块 404xx ----------
class ResourceNotFoundError(AppCodeException):
    def __init__(self, resource: str = "资源"):
        super().__init__(code=40401, message=f"{resource}不存在", detail=f"请求的{resource}未找到", http_status=404)


# ---------- 验证模块 422xx ----------
class ValidationError(AppCodeException):
    def __init__(self, detail: str = "参数验证失败"):
        super().__init__(code=42201, message="参数验证失败", detail=detail, http_status=422)


# ---------- 业务模块 500xx ----------
class BusinessError(AppCodeException):
    def __init__(self, message: str, detail: str = None):
        super().__init__(code=50001, message=message, detail=detail, http_status=400)


# ============================================================
# 旧版：HTTP状态码异常体系 — 保持向后兼容，现有代码继续使用
# ============================================================

class AppException(HTTPException):
    """旧版异常基类 — 保留向后兼容"""
    def __init__(
        self,
        status_code: int,
        detail: Any = None,
        headers: Optional[dict] = None,
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class BadRequestException(AppException):
    def __init__(self, detail: str = "Bad Request"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class UnauthorizedException(AppException):
    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class ForbiddenException(AppException):
    def __init__(self, detail: str = "Forbidden"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class NotFoundException(AppException):
    def __init__(self, detail: str = "Not Found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class ConflictException(AppException):
    def __init__(self, detail: str = "Conflict"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class TooManyRequestsException(AppException):
    def __init__(self, detail: str = "Too Many Requests"):
        super().__init__(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=detail)


class InternalServerException(AppException):
    def __init__(self, detail: str = "Internal Server Error"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


class EmailAlreadyExistsException(ConflictException):
    def __init__(self):
        super().__init__(detail="邮箱已被注册")


class InvalidVerifyCodeException(BadRequestException):
    def __init__(self):
        super().__init__(detail="验证码无效或已过期")


class VerifyCodeSendTooFrequentlyException(TooManyRequestsException):
    def __init__(self):
        super().__init__(detail="验证码发送过于频繁，请稍后再试")
