"""审计日志中间件 — 自动记录所有写操作"""
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.security import decode_token
from app.db.session import get_db_session

SKIP_PREFIXES = ["/docs", "/redoc", "/openapi.json", "/health", "/uploads", "/static"]


class AuditLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)

        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            path = request.url.path
            if not any(path.startswith(p) for p in SKIP_PREFIXES):
                self._log(request, response, start_time)

        return response

    def _log(self, request: Request, response, start_time: float):
        try:
            user_id = None
            workspace_id = None
            auth_header = request.headers.get("authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header.replace("Bearer ", "")
                payload = decode_token(token)
                if payload:
                    user_id = payload.get("user_id")

            path = request.url.path
            parts = [p for p in path.split("/") if p]
            module = "system"
            target_type = None
            target_id = None

            if "api" in parts and "v1" in parts:
                idx = parts.index("v1")
                if len(parts) > idx + 1:
                    module = parts[idx + 1]
                if len(parts) > idx + 2:
                    target_type = parts[idx + 2]
                if len(parts) > idx + 3 and parts[idx + 3].isdigit():
                    target_id = int(parts[idx + 3])

            workspace_id = request.query_params.get("workspace_id")

            db = get_db_session()
            try:
                from app.modules.org.models import AuditLog
                log_entry = AuditLog(
                    workspace_id=int(workspace_id) if workspace_id else None,
                    user_id=user_id,
                    module=module,
                    action=request.method.lower(),
                    target_type=target_type,
                    target_id=target_id,
                    detail={
                        "method": request.method,
                        "path": path,
                        "status_code": response.status_code,
                        "duration_ms": round((time.time() - start_time) * 1000, 2)
                    },
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent", "")
                )
                db.add(log_entry)
                db.commit()
            except Exception:
                db.rollback()
            finally:
                db.close()
        except Exception:
            pass  # 审计日志写入失败不影响主业务
