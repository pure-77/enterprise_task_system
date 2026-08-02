"""统一响应格式中间件"""
import json
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from fastapi import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.exceptions import AppCodeException


def _clean_headers(headers: dict) -> dict:
    """移除原始响应中与内容长度/编码相关的头，让服务器自动计算"""
    skip = {"content-length", "content-encoding", "transfer-encoding"}
    return {k: v for k, v in headers.items() if k.lower() not in skip}


# 不包装的路径 — OpenAPI spec 必须保持原始格式
SKIP_WRAP_PATHS = {"/openapi.json", "/docs", "/redoc", "/docs/oauth2-redirect"}


class ResponseHandlerMiddleware(BaseHTTPMiddleware):
    """统一包装所有 JSON 响应为 {"code": 0, "message": "success", "data": ...} 格式"""

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)

            # 跳过 OpenAPI 相关路径
            if request.url.path in SKIP_WRAP_PATHS or request.url.path.startswith("/docs"):
                return response

            content_type = response.headers.get("content-type", "")
            if "application/json" not in content_type:
                return response

            body = b""
            async for chunk in response.body_iterator:
                body += chunk

            if not body:
                return response

            try:
                data = json.loads(body)
                if isinstance(data, dict) and "code" in data:
                    return Response(
                        content=json.dumps(data, ensure_ascii=False),
                        status_code=response.status_code,
                        headers=_clean_headers(dict(response.headers)),
                        media_type="application/json"
                    )
                wrapped = {"code": 0, "message": "success", "data": data}
                return Response(
                    content=json.dumps(wrapped, ensure_ascii=False),
                    status_code=response.status_code,
                    headers=_clean_headers(dict(response.headers)),
                    media_type="application/json"
                )
            except json.JSONDecodeError:
                pass

            return Response(
                content=body,
                status_code=response.status_code,
                headers=_clean_headers(dict(response.headers)),
                media_type=response.headers.get("content-type", "application/octet-stream")
            )

        except AppCodeException as e:
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "code": e.code,
                    "message": e.err_message,
                    "data": None,
                    "detail": e.detail
                }
            )
        except HTTPException:
            # FastAPI 内置异常（401/403/404/422等）— 直接放行，让 FastAPI 处理
            raise
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "code": 50000,
                    "message": "服务器内部错误",
                    "data": None,
                    "detail": str(e)
                }
            )
