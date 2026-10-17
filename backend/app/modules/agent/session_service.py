"""Agent 会话持久化服务（MySQL）

和 service.py 的 Redis 短期记忆互补：
- Redis AgentMemory:  推理时快速加载对话上下文（24h TTL）
- AgentSessionService: 持久化会话列表 + 完整消息历史（永久留存）
"""
import json
import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.agent_session import AgentSession, AgentMessage
from app.models.user import User

logger = logging.getLogger("agent.session")


class AgentSessionService:
    """Agent 会话管理 — 纯 CRUD"""

    @staticmethod
    def get_or_create_session(
        db: Session,
        user: User,
        workspace_id: int,
        session_key: str,
        title: Optional[str] = None,
    ) -> AgentSession:
        """根据 session_key + workspace_id 获取会话，不存在则创建。

        session_key 在全表是唯一约束，因此必须校验 workspace_id：
        同一 session_key 在不同 workspace 下不能被复用（否则会串空间）。
        若该 key 已被其它 workspace/用户占用，则派生一个带 workspace 的唯一 key。
        """
        ws = workspace_id or 0

        session = db.query(AgentSession).filter(
            AgentSession.session_key == session_key,
            AgentSession.user_id == user.id,
            AgentSession.workspace_id == ws,
        ).first()
        if session:
            return session

        # session_key 已被其它 workspace / 用户占用 → 派生唯一 key
        occupied = db.query(AgentSession).filter(
            AgentSession.session_key == session_key
        ).first()
        if occupied:
            derived_key = f"{session_key}-ws{ws}"
            session = db.query(AgentSession).filter(
                AgentSession.session_key == derived_key
            ).first()
            if session:
                return session
            session_key = derived_key

        session = AgentSession(
            user_id=user.id,
            workspace_id=ws,
            session_key=session_key,
            title=title or "新对话",
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        logger.info(f"[AgentSession] 创建新会话: id={session.id}, key={session_key}, ws={ws}")
        return session

    @staticmethod
    def list_sessions(
        db: Session,
        user: User,
        workspace_id: Optional[int] = None,
        limit: int = 50,
    ) -> list[AgentSession]:
        """列出用户的会话（按 updated_at 倒序）"""
        q = db.query(AgentSession).filter(AgentSession.user_id == user.id)
        if workspace_id is not None:
            q = q.filter(AgentSession.workspace_id == workspace_id)
        return q.order_by(AgentSession.updated_at.desc()).limit(limit).all()

    @staticmethod
    def get_session(db: Session, user: User, session_id: int) -> Optional[AgentSession]:
        """获取单个会话（校验归属）"""
        return db.query(AgentSession).filter(
            AgentSession.id == session_id,
            AgentSession.user_id == user.id,
        ).first()

    @staticmethod
    def get_messages(db: Session, user: User, session_id: int, limit: int = 200) -> list[AgentMessage]:
        """获取会话的消息列表（按 seq 顺序）"""
        session = AgentSessionService.get_session(db, user, session_id)
        if not session:
            return []
        return db.query(AgentMessage).filter(
            AgentMessage.session_id == session.id
        ).order_by(AgentMessage.seq.asc()).limit(limit).all()

    @staticmethod
    def delete_session(db: Session, user: User, session_id: int) -> bool:
        """删除会话（级联删除消息）"""
        session = AgentSessionService.get_session(db, user, session_id)
        if not session:
            return False
        db.delete(session)
        db.commit()
        logger.info(f"[AgentSession] 已删除会话: id={session_id}")
        return True

    @staticmethod
    def delete_message(db: Session, user: User, session_id: int, message_id: int) -> bool:
        """删除单条消息（前端编辑/撤销用）"""
        msg = db.query(AgentMessage).join(AgentSession).filter(
            AgentMessage.id == message_id,
            AgentSession.id == session_id,
            AgentSession.user_id == user.id,
        ).first()
        if not msg:
            return False
        db.delete(msg)
        db.commit()
        return True

    # ===== 写入方法 =====

    @staticmethod
    def append_message(
        db: Session,
        session: AgentSession,
        role: str,
        content: str,
        seq: Optional[int] = None,
        image_url: Optional[str] = None,
        tool_calls: Optional[list] = None,
        thinking: Optional[str] = None,
    ) -> AgentMessage:
        """追加一条消息到会话"""
        # 自动算 seq
        if seq is None:
            max_seq = db.query(AgentMessage).filter(
                AgentMessage.session_id == session.id
            ).count()
            seq = max_seq

        msg = AgentMessage(
            session_id=session.id,
            role=role,
            content=content[:8000],  # 截断防爆
            seq=seq,
            image_url=image_url,
            tool_calls=json.dumps(tool_calls, ensure_ascii=False) if tool_calls else None,
            thinking=thinking,
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)

        # 更新会话统计
        session.message_count = db.query(AgentMessage).filter(
            AgentMessage.session_id == session.id
        ).count()
        db.commit()
        return msg
