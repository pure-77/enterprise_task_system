"""MCP 身份上下文装配 — token → 业务 context

复用现有 decode_token 鉴权，不新写一套。
要点：
1. db.expunge(user) 必须，否则 handler 内访问属性会抛 DetachedInstanceError
2. workspace_id 不能完全信任客户端传值，进 context 前先校验成员关系
3. workspace_id=0 归一化为 None（个人空间）
"""
from app.modules.agent.mcp.middleware import _token


def resolve_context(workspace_id: int | None = None) -> dict:
    """从 ContextVar 中的 token 解析出业务 context（user + workspace_id）"""
    token = _token.get()
    if not token:
        raise PermissionError("缺少访问令牌（请在请求头携带 Authorization: Bearer <token>）")

    from app.core.security import decode_token
    from app.db.session import SessionLocal
    from app.models.user import User

    payload = decode_token(token)
    if not payload or not payload.get("sub"):
        raise PermissionError("令牌无效或已过期")

    db = SessionLocal()
    try:
        # sub 存的是邮箱（与 REST 登录一致），按邮箱查用户
        user = db.query(User).filter(User.email == payload["sub"]).first()
        if not user:
            raise PermissionError("用户不存在")

        # 个人空间归一化：0 -> None
        ws = workspace_id if (workspace_id and workspace_id > 0) else None

        # 工作区必须校验成员关系，防止越权访问他人空间数据
        if ws is not None:
            from app.core.permissions import get_workspace_member
            get_workspace_member(ws, user.id, db)

        db.expunge(user)  # 必须：否则 handler 内访问属性会 DetachedInstanceError
        return {"user": user, "workspace_id": ws}
    finally:
        db.close()
