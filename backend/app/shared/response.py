"""统一响应格式工具"""
from typing import Any, Optional


def success_response(data: Any = None, message: str = "success") -> dict:
    """成功响应"""
    return {
        "code": 0,
        "message": message,
        "data": data
    }


def error_response(
    code: int,
    message: str,
    detail: Optional[str] = None,
    status_code: int = 200
) -> dict:
    """错误响应 — 由 response_handler 中间件根据 code 决定实际 HTTP status。
    业务代码使用 raise AppException(code, message, detail) 抛出异常。
    """
    body: dict = {
        "code": code,
        "message": message,
        "data": None
    }
    if detail:
        body["detail"] = detail
    return body


def paginated_response(
    items: list,
    total: int,
    page: int,
    page_size: int
) -> dict:
    """分页响应"""
    return {
        "code": 0,
        "message": "success",
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0
        }
    }
