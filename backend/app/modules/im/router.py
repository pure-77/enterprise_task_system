"""即时通讯模块 — API 路由"""
import os
import json
import uuid
import logging
from fastapi import APIRouter, Depends, Query, UploadFile, File as FastAPIFile, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import get_current_user
from app.core.permissions import get_workspace_member
from app.core.exceptions import BusinessError, ResourceNotFoundError
from app.models.user import User
from app.modules.im.models import MessageType
from app.modules.im.crud import conversation_crud, message_crud, read_crud
from app.modules.im.schemas import ConversationCreate, MessageCreate, ReadMark, MemberAdd, MuteToggle
from app.modules.im.storage import storage, is_image, ALLOWED_IMAGE_EXTENSIONS, IM_IMAGE_MAX_SIZE, IM_FILE_MAX_SIZE
from app.api.v1.websocket import publish_im_message, publish_read_status

router = APIRouter()

logger = logging.getLogger(__name__)


# ==================== 会话管理 ====================

@router.post("/conversations", status_code=201)
async def create_conversation(
    conv_in: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建会话"""
    get_workspace_member(conv_in.workspace_id, current_user.id, db)

    if conv_in.type == "single":
        if not conv_in.peer_id:
            raise BusinessError("单聊需要指定 peer_id")
        if conv_in.peer_id == current_user.id:
            raise BusinessError("不能和自己创建单聊")
        conv = conversation_crud.create_single(
            db, conv_in.workspace_id, current_user.id, conv_in.peer_id
        )
    elif conv_in.type == "group":
        if not conv_in.name:
            raise BusinessError("群聊需要指定名称")
        conv = conversation_crud.create_group(
            db, conv_in.workspace_id, current_user.id,
            name=conv_in.name,
            member_ids=conv_in.member_ids or [],
            avatar=conv_in.avatar
        )
    else:
        raise BusinessError(f"不支持的会话类型: {conv_in.type}")

    return {
        "id": conv.id,
        "type": conv.type.value,
        "name": conv.name,
        "workspace_id": conv.workspace_id,
        "created_by": conv.created_by,
        "member_count": len(conv.members) if conv.members else 0,
    }


@router.get("/conversations")
async def get_conversations(
    workspace_id: int = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取会话列表"""
    get_workspace_member(workspace_id, current_user.id, db)
    return conversation_crud.get_list(db, current_user.id, workspace_id)


@router.get("/conversations/{conv_id}")
async def get_conversation_detail(
    conv_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取会话详情（含成员列表）"""
    conv = conversation_crud.get_by_id(db, conv_id)
    conversation_crud.get_member(db, conv_id, current_user.id)  # 验证成员身份

    members = []
    for m in conv.members:
        if m.is_active:
            members.append({
                "id": m.user_id,
                "nickname": m.user.nickname if m.user else None,
                "avatar": m.user.avatar if m.user else None,
                "role": m.role.value,
                "nickname_in_group": m.nickname,
                "joined_at": m.joined_at.isoformat() if m.joined_at else None,
            })

    return {
        "id": conv.id,
        "type": conv.type.value,
        "name": conv.name,
        "avatar": conv.avatar,
        "is_muted": conv.is_muted,
        "workspace_id": conv.workspace_id,
        "created_by": conv.created_by,
        "members": members,
    }


# ==================== 消息收发 ====================

@router.get("/conversations/{conv_id}/messages")
async def get_messages(
    conv_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    before_id: int = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取消息列表"""
    conversation_crud.get_member(db, conv_id, current_user.id)
    return message_crud.get_messages(db, conv_id, current_user.id, page, page_size, before_id)


@router.post("/conversations/{conv_id}/messages", status_code=201)
async def send_message(
    conv_id: int,
    msg_in: MessageCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """发送消息"""
    conversation_crud.get_member(db, conv_id, current_user.id)

    try:
        msg_type = MessageType(msg_in.msg_type)
    except ValueError:
        msg_type = MessageType.TEXT

    msg = message_crud.send(
        db, conv_id, current_user.id,
        msg_type=msg_type,
        content=msg_in.content,
        reply_to_id=msg_in.reply_to_id
    )

    result = {
        "id": msg.id,
        "conversation_id": msg.conversation_id,
        "sender_id": msg.sender_id,
        "sender_name": current_user.nickname,
        "sender_avatar": current_user.avatar,
        "msg_type": msg.msg_type.value,
        "content": msg.content,
        "reply_to_id": msg.reply_to_id,
        "read_count": 0,  # 新消息默认未读
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
    }

    # 通过 Redis Pub/Sub 推送给在线成员（Redis 不可用时静默跳过）
    try:
        publish_im_message(conv_id, result)
    except Exception:
        pass

    # RAG：文本消息后台异步索引进知识库（仅文本；失败不影响发送）
    if msg_type == MessageType.TEXT:
        try:
            from app.modules.knowledge.indexer import index_source
            background_tasks.add_task(index_source, "im", msg.id)
        except Exception as e:
            logger.warning(f"消息索引进队失败（不影响发送）: {e}")

    return result


@router.post("/conversations/{conv_id}/read")
async def mark_read(
    conv_id: int,
    body: ReadMark,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """标记消息已读"""
    conversation_crud.get_member(db, conv_id, current_user.id)
    # 获取需要标记的消息 ID 列表（用于 WebSocket 通知）
    if body.message_ids:
        marked_ids = body.message_ids
    else:
        from app.modules.im.models import Message
        marked_ids = [m.id for m in db.query(Message.id).filter(
            Message.conversation_id == conv_id,
            Message.is_active == True
        ).all()]
    count = read_crud.mark_read(db, conv_id, current_user.id, body.message_ids)
    # 推送已读状态给会话其他成员
    if count > 0 and marked_ids:
        from app.modules.im.models import ConversationMember
        members = db.query(ConversationMember.user_id).filter(
            ConversationMember.conversation_id == conv_id,
            ConversationMember.is_active == True
        ).all()
        member_ids = [m.user_id for m in members]
        publish_read_status(conv_id, current_user.id, marked_ids, member_ids)
    return {"marked_count": count}


# ==================== 消息撤回 ====================

@router.put("/messages/{msg_id}/recall")
async def recall_message(
    msg_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """撤回消息（2分钟内）"""
    msg = message_crud.recall(db, msg_id, current_user.id)

    # 通过 WebSocket 推送撤回消息给会话其他成员
    try:
        recall_data = {
            "id": msg.id,
            "conversation_id": msg.conversation_id,
            "sender_id": msg.sender_id,
            "is_recalled": True,
            "recalled_at": msg.recalled_at.isoformat() if msg.recalled_at else None,
        }
        publish_im_message(msg.conversation_id, recall_data)
    except Exception:
        pass

    # RAG：后台异步清理该消息的向量与分片元数据
    try:
        from app.modules.knowledge.indexer import delete_source_index
        background_tasks.add_task(delete_source_index, "im", msg_id)
    except Exception as e:
        logger.warning(f"消息索引清理入队失败（不影响撤回）: {e}")

    return {"message": "消息已撤回"}


# ==================== 文件上传 ====================

@router.post("/upload")
async def upload_im_file(
    workspace_id: int = Query(None),
    file: UploadFile = FastAPIFile(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """IM 文件上传接口 — 支持图片和普通文件"""
    if not workspace_id:
        raise BusinessError("缺少工作空间ID")
    get_workspace_member(workspace_id, current_user.id, db)

    ext = os.path.splitext(file.filename or "")[1].lower()
    content = await file.read()
    await file.seek(0)

    if is_image(ext):
        max_size = IM_IMAGE_MAX_SIZE
        msg_type = MessageType.IMAGE
    else:
        max_size = IM_FILE_MAX_SIZE
        msg_type = MessageType.FILE

    if len(content) > max_size:
        size_mb = max_size // 1024 // 1024
        raise BusinessError(f"文件大小不能超过 {size_mb}MB")

    if ext and ext not in ALLOWED_IMAGE_EXTENSIONS and ext not in {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.md', '.csv', '.zip', '.rar', '.mp4', '.mp3', '.json', '.xml', '.html', '.css', '.js', '.py'}:
        raise BusinessError(f"不支持的文件类型: {ext}")

    relative_path = f"im_{uuid.uuid4().hex}{ext}"
    size = await storage.upload(file, workspace_id, relative_path)
    file_url = storage.get_url(workspace_id, relative_path)

    return {
        "url": file_url,
        "name": file.filename or "unknown",
        "size": size,
        "mime_type": file.content_type,
        "msg_type": msg_type.value,
    }


# ==================== 文件访问（带权限校验） ====================

@router.get("/files/{file_id}")
async def get_im_file(
    file_id: int,
    workspace_id: int = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取IM上传的文件信息"""
    if not workspace_id:
        raise BusinessError("缺少工作空间ID")
    get_workspace_member(workspace_id, current_user.id, db)

    from app.modules.file.models import File
    f = db.query(File).filter(File.id == file_id, File.is_active == True).first()
    if not f:
        raise ResourceNotFoundError(resource="文件")

    return {
        "id": f.id,
        "name": f.name,
        "size": f.size,
        "mime_type": f.mime_type,
        "url": storage.get_url(f.workspace_id, f.path),
    }


# ==================== 群管理 ====================

@router.post("/conversations/{conv_id}/members", status_code=201)
async def add_member(
    conv_id: int,
    body: MemberAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """添加成员"""
    conversation_crud.get_member(db, conv_id, current_user.id)
    member = conversation_crud.add_member(db, conv_id, current_user.id, body.user_id)
    return {"message": "成员已添加", "user_id": member.user_id}


@router.delete("/conversations/{conv_id}/members/{user_id}")
async def remove_member(
    conv_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """移除成员"""
    conversation_crud.get_member(db, conv_id, current_user.id)
    conversation_crud.remove_member(db, conv_id, current_user.id, user_id)
    return {"message": "成员已移除"}


@router.put("/conversations/{conv_id}/mute")
async def toggle_mute(
    conv_id: int,
    body: MuteToggle,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """全员禁言开关 — 仅群主/管理员"""
    member = conversation_crud.get_member(db, conv_id, current_user.id)
    from app.modules.im.models import MemberRole
    if member.role not in [MemberRole.OWNER, MemberRole.ADMIN]:
        from app.core.exceptions import PermissionDeniedError
        raise PermissionDeniedError(detail="需要群主或管理员权限")
    conv = conversation_crud.mute_all(db, conv_id, body.is_muted)
    return {"is_muted": conv.is_muted}
