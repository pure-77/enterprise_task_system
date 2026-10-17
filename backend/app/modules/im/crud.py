"""即时通讯模块 — CRUD 操作"""
from datetime import datetime
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import desc, and_, or_
from app.modules.im.models import (
    Conversation, ConversationMember, Message, MessageRead,
    ConversationType, MessageType, MemberRole
)
from app.core.exceptions import ResourceNotFoundError, PermissionDeniedError, BusinessError
from app.db.base import get_beijing_time


class ConversationCRUD:

    def create_single(self, db: Session, workspace_id: int, creator_id: int, peer_id: int) -> Conversation:
        """创建单聊 — 检查是否已存在，存在则返回已有会话"""
        # 查找 creator 参与的 single 类型的会话
        candidates = (
            db.query(Conversation)
            .join(ConversationMember)
            .filter(
                Conversation.workspace_id == workspace_id,
                Conversation.type == ConversationType.SINGLE,
                Conversation.is_active == True,
                ConversationMember.user_id == creator_id,
                ConversationMember.is_active == True
            ).all()
        )
        # 检查 peer 是否也在同一会话中
        for conv in candidates:
            peer_member = db.query(ConversationMember).filter(
                ConversationMember.conversation_id == conv.id,
                ConversationMember.user_id == peer_id,
                ConversationMember.is_active == True
            ).first()
            if peer_member:
                return conv

        conv = Conversation(
            workspace_id=workspace_id,
            type=ConversationType.SINGLE,
            created_by=creator_id
        )
        db.add(conv)
        db.flush()

        for uid in [creator_id, peer_id]:
            db.add(ConversationMember(
                conversation_id=conv.id,
                user_id=uid,
                role=MemberRole.MEMBER,
                joined_at=get_beijing_time()
            ))

        db.commit()
        db.refresh(conv)
        return conv

    def create_group(
        self, db: Session, workspace_id: int, creator_id: int,
        name: str, member_ids: list[int], avatar: str = None
    ) -> Conversation:
        """创建群聊"""
        conv = Conversation(
            workspace_id=workspace_id,
            type=ConversationType.GROUP,
            name=name,
            avatar=avatar,
            created_by=creator_id
        )
        db.add(conv)
        db.flush()

        # 创建者为群主
        db.add(ConversationMember(
            conversation_id=conv.id,
            user_id=creator_id,
            role=MemberRole.OWNER,
            joined_at=get_beijing_time()
        ))
        for uid in member_ids:
            if uid != creator_id:
                db.add(ConversationMember(
                    conversation_id=conv.id,
                    user_id=uid,
                    role=MemberRole.MEMBER,
                    joined_at=get_beijing_time()
                ))

        db.commit()
        db.refresh(conv)
        return conv

    def get_list(self, db: Session, user_id: int, workspace_id: int) -> list[dict]:
        """获取用户的会话列表（按最后消息时间倒序）
        优化：使用 selectinload 预加载成员→用户、批量查询最后消息，消除 N+1
        """
        memberships = (
            db.query(ConversationMember)
            .options(
                selectinload(ConversationMember.conversation).joinedload(Conversation.members).selectinload(ConversationMember.user),
            )
            .join(Conversation)
            .filter(
                ConversationMember.user_id == user_id,
                ConversationMember.is_active == True,
                Conversation.workspace_id == workspace_id,
                Conversation.is_active == True
            )
            .order_by(desc(Conversation.last_message_at))
            .all()
        )

        # 批量查询所有会话的最后一条消息，避免 N+1
        last_msg_ids = [m.conversation.last_message_id for m in memberships if m.conversation.last_message_id]
        last_messages_map = {}
        if last_msg_ids:
            msgs = db.query(Message).options(
                joinedload(Message.sender)
            ).filter(Message.id.in_(last_msg_ids)).all()
            last_messages_map = {msg.id: msg for msg in msgs}

        result = []
        for m in memberships:
            conv = m.conversation
            last_msg = last_messages_map.get(conv.last_message_id) if conv.last_message_id else None

            # 单聊显示对方名字和头像，群聊用会话名称
            display_name = conv.name
            display_avatar = conv.avatar
            if conv.type == ConversationType.SINGLE:
                peer = next((mb for mb in conv.members if mb.user_id != user_id and mb.is_active), None)
                if peer and peer.user:
                    display_name = peer.user.nickname
                    display_avatar = peer.user.avatar

            result.append({
                "id": conv.id,
                "type": conv.type.value,
                "name": display_name,
                "avatar": display_avatar,
                "is_muted": m.is_muted,
                "unread_count": m.unread_count,
                "last_message": {
                    "content": last_msg.content[:100] if last_msg else None,
                    "msg_type": last_msg.msg_type.value if last_msg else None,
                    "sender_name": last_msg.sender.nickname if last_msg and last_msg.sender else None,
                    "created_at": last_msg.created_at.isoformat() if last_msg and last_msg.created_at else None,
                } if last_msg else None,
                "last_message_at": conv.last_message_at.isoformat() if conv.last_message_at else None,
                "member_count": len([mb for mb in conv.members if mb.is_active]) if conv.members else 0,
            })
        return result

    def get_by_id(self, db: Session, conv_id: int) -> Conversation:
        conv = db.query(Conversation).filter(
            Conversation.id == conv_id,
            Conversation.is_active == True
        ).first()
        if not conv:
            raise ResourceNotFoundError(resource="会话")
        return conv

    def get_member(self, db: Session, conv_id: int, user_id: int) -> ConversationMember:
        member = db.query(ConversationMember).filter(
            ConversationMember.conversation_id == conv_id,
            ConversationMember.user_id == user_id,
            ConversationMember.is_active == True
        ).first()
        if not member:
            raise PermissionDeniedError(detail="你不是该会话的成员")
        return member

    def add_member(self, db: Session, conv_id: int, operator_id: int, user_id: int) -> ConversationMember:
        conv = self.get_by_id(db, conv_id)
        if conv.type == ConversationType.SINGLE:
            raise BusinessError("单聊不支持添加成员")
        existing = db.query(ConversationMember).filter(
            ConversationMember.conversation_id == conv_id,
            ConversationMember.user_id == user_id
        ).first()
        if existing:
            if existing.is_active:
                raise BusinessError("该用户已在会话中")
            existing.is_active = True
            db.commit()
            return existing

        member = ConversationMember(
            conversation_id=conv_id,
            user_id=user_id,
            role=MemberRole.MEMBER,
            joined_at=get_beijing_time()
        )
        db.add(member)
        db.commit()
        db.refresh(member)
        return member

    def remove_member(self, db: Session, conv_id: int, operator_id: int, user_id: int) -> None:
        member = db.query(ConversationMember).filter(
            ConversationMember.conversation_id == conv_id,
            ConversationMember.user_id == user_id,
            ConversationMember.is_active == True
        ).first()
        if not member:
            raise ResourceNotFoundError(resource="成员")
        member.is_active = False
        db.commit()

    def mute_all(self, db: Session, conv_id: int, is_muted: bool) -> Conversation:
        conv = self.get_by_id(db, conv_id)
        conv.is_muted = is_muted
        db.commit()
        db.refresh(conv)
        return conv


class MessageCRUD:

    def send(
        self, db: Session, conv_id: int, sender_id: int,
        msg_type: MessageType, content: str, reply_to_id: int = None
    ) -> Message:
        now = get_beijing_time()
        msg = Message(
            conversation_id=conv_id,
            sender_id=sender_id,
            msg_type=msg_type,
            content=content,
            reply_to_id=reply_to_id,
            created_at=now
        )
        db.add(msg)
        db.flush()

        # 更新会话最后消息
        conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
        conv.last_message_id = msg.id
        conv.last_message_at = now

        # 增加所有其他成员的未读数
        db.query(ConversationMember).filter(
            ConversationMember.conversation_id == conv_id,
            ConversationMember.user_id != sender_id,
            ConversationMember.is_active == True
        ).update(
            {"unread_count": ConversationMember.unread_count + 1},
            synchronize_session=False
        )

        db.commit()
        return msg

    def get_messages(
        self, db: Session, conv_id: int, user_id: int,
        page: int = 1, page_size: int = 20, before_id: int = None
    ) -> dict:
        """获取消息列表 — 游标分页（before_id），批量加载已读数和发送者
        - 首次加载: page=1, before_id=None → 返回最新的 page_size 条
        - 上翻加载: before_id=最后一条消息ID → 返回该 ID 之前的 page_size 条
        """
        query = db.query(Message).filter(
            Message.conversation_id == conv_id,
            Message.is_active == True,
            Message.is_recalled == False
        )
        if before_id:
            query = query.filter(Message.id < before_id)

        # 游标分页: 不使用 offset，直接用 WHERE id < before_id + LIMIT
        messages = (
            query.order_by(desc(Message.created_at), desc(Message.id))
            .limit(page_size)
            .all()
        )

        if not messages:
            return {"items": [], "total": 0, "page": page, "page_size": page_size, "has_more": False}

        # 批量查询已读人数（排除发送者自己），避免 N+1
        msg_ids = [m.id for m in messages]
        from sqlalchemy import func
        # 查询每条消息的已读人数，但排除发送者自己
        read_counts = {}
        for msg in messages:
            count = db.query(func.count(MessageRead.user_id)).filter(
                MessageRead.message_id == msg.id,
                MessageRead.user_id != msg.sender_id  # 排除发送者自己
            ).scalar()
            read_counts[msg.id] = count

        items = []
        for msg in reversed(messages):  # 旧→新正序
            items.append({
                "id": msg.id,
                "conversation_id": msg.conversation_id,
                "sender_id": msg.sender_id,
                "sender_name": msg.sender.nickname if msg.sender else None,
                "sender_avatar": msg.sender.avatar if msg.sender else None,
                "msg_type": msg.msg_type.value,
                "content": msg.content,
                "reply_to_id": msg.reply_to_id,
                "read_count": read_counts.get(msg.id, 0),
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
            })

        # 是否还有更早的消息
        oldest_id = min(msg_ids)
        has_more = db.query(Message.id).filter(
            Message.conversation_id == conv_id,
            Message.is_active == True,
            Message.is_recalled == False,
            Message.id < oldest_id
        ).first() is not None

        return {
            "items": items,
            "total": None,  # 游标分页不返回 total，用 has_more 代替
            "page": page,
            "page_size": page_size,
            "has_more": has_more,
            "oldest_id": oldest_id,
        }

    def recall(self, db: Session, msg_id: int, user_id: int) -> Message:
        msg = db.query(Message).filter(
            Message.id == msg_id,
            Message.is_active == True
        ).first()
        if not msg:
            raise ResourceNotFoundError(resource="消息")
        if msg.sender_id != user_id:
            raise PermissionDeniedError(detail="只能撤回自己发送的消息")

        from datetime import timedelta
        if (get_beijing_time() - msg.created_at.replace(tzinfo=None)).total_seconds() > 120:
            raise BusinessError("超过2分钟的消息无法撤回")

        msg.is_recalled = True
        msg.recalled_at = get_beijing_time()
        db.commit()
        return msg


class ReadCRUD:

    def mark_read(self, db: Session, conv_id: int, user_id: int, message_ids: list[int] = None) -> int:
        """标记消息已读 — 批量处理，避免 N+1 查询和并发重复插入"""
        now = get_beijing_time()

        if message_ids:
            messages = db.query(Message).filter(
                Message.id.in_(message_ids),
                Message.conversation_id == conv_id,
                Message.is_active == True
            ).all()
        else:
            messages = db.query(Message).filter(
                Message.conversation_id == conv_id,
                Message.is_active == True
            ).all()

        if not messages:
            return 0

        # 批量查询已存在的已读记录，避免 N+1
        msg_ids = [m.id for m in messages]
        existing_reads = {
            r.message_id for r in db.query(MessageRead).filter(
                MessageRead.message_id.in_(msg_ids),
                MessageRead.user_id == user_id
            ).all()
        }

        count = 0
        from sqlalchemy.exc import IntegrityError
        for msg in messages:
            if msg.id in existing_reads:
                continue
            try:
                db.add(MessageRead(message_id=msg.id, user_id=user_id, read_at=now))
                db.flush()  # 立即触发唯一约束检查
                count += 1
            except IntegrityError:
                # 唯一约束冲突 = 已被其他事务标记，跳过
                db.rollback()
                continue

        # 清除未读数（使用行锁防止并发）
        db.query(ConversationMember).filter(
            ConversationMember.conversation_id == conv_id,
            ConversationMember.user_id == user_id
        ).with_for_update().update({"unread_count": 0, "last_read_at": now})

        db.commit()
        return count


conversation_crud = ConversationCRUD()
message_crud = MessageCRUD()
read_crud = ReadCRUD()
