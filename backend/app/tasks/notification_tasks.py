"""异步通知推送任务 — 站内信写入 + WebSocket 推送 + 邮件通知"""
import logging
from app.core.celery_config import celery_app
from app.db.session import SessionLocal
from app.modules.notification.crud import notification_crud
from app.api.v1.websocket import publish_notification
from app.services.cache_service import CacheService

logger = logging.getLogger("celery.notification")


@celery_app.task
def push_notification_to_user(user_id: int, ntype: str, title: str,
                               content: str = None, related_type: str = None,
                               related_id: int = None):
    """异步推送通知：1) 写站内信 2) WebSocket 推送 3) 失效未读缓存"""
    db = SessionLocal()
    try:
        # 1) 写入站内信
        notif = notification_crud.create(
            db, user_id, ntype, title, content, related_type, related_id
        )

        # 2) WebSocket 实时推送
        notif_data = {
            "id": notif.id,
            "type": ntype,
            "title": title,
            "content": content,
            "related_type": related_type,
            "related_id": related_id,
            "is_read": False,
            "created_at": notif.created_at.isoformat() if notif.created_at else None,
        }
        publish_notification(user_id, notif_data)

        # 3) 失效未读计数缓存（让前端刷新时获取最新值）
        CacheService.delete_user_info(user_id)

        logger.info(f"通知推送成功: user_id={user_id} type={ntype} title={title}")
        return {"status": "success", "notif_id": notif.id}
    except Exception as e:
        logger.error(f"通知推送失败: user_id={user_id} type={ntype} error={e}")
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()


@celery_app.task
def push_bulk_notification(user_ids: list[int], ntype: str, title: str,
                            content: str = None, related_type: str = None,
                            related_id: int = None):
    """批量推送通知（如企业公告）"""
    results = []
    for uid in user_ids:
        result = push_notification_to_user.delay(
            uid, ntype, title, content, related_type, related_id
        )
        results.append({"user_id": uid, "task_id": result.id})
    logger.info(f"批量通知已投递: total={len(user_ids)} type={ntype}")
    return {"status": "submitted", "count": len(user_ids), "task_ids": [r["task_id"] for r in results]}


@celery_app.task
def push_workspace_notification(workspace_id: int, ntype: str, title: str,
                                 content: str = None, related_type: str = None,
                                 related_id: int = None):
    """向工作空间所有成员推送通知"""
    from app.db.session import SessionLocal
    from app.models.workspace import WorkspaceMember

    db = SessionLocal()
    try:
        members = db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.is_active == True
        ).all()
        user_ids = [m.user_id for m in members]

        if not user_ids:
            return {"status": "skipped", "reason": "no members"}

        result = push_bulk_notification.delay(
            user_ids, ntype, title, content, related_type, related_id
        )
        logger.info(f"工作空间通知已投递: ws={workspace_id} members={len(user_ids)}")
        return {"status": "submitted", "workspace_id": workspace_id, "count": len(user_ids), "task_id": result.id}
    except Exception as e:
        logger.error(f"工作空间通知失败: ws={workspace_id} error={e}")
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()
