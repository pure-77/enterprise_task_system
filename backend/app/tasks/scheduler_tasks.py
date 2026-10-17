"""定时调度任务 — 统计预计算 + 逾期检测 + 健康检查
这些任务由 Celery Beat 定时触发，Worker 执行"""
import logging
from datetime import datetime, timedelta
from app.core.celery_config import celery_app
from app.db.session import SessionLocal
from app.services.cache_service import CacheService

logger = logging.getLogger("celery.scheduler")


# ==================== 统计数据预计算 ====================

@celery_app.task
def precompute_user_stats():
    """预计算所有活跃用户的统计概览，写入缓存
    每 10 分钟执行一次，避免用户首次加载统计时等待"""
    db = SessionLocal()
    try:
        from app.models.user import User
        from app.crud.statistics import statistics

        users = db.query(User).filter(User.is_active == True).all()
        computed = 0
        for user in users:
            try:
                # 个人统计
                data = statistics.get_overview(db, user.id, None)
                if data:
                    CacheService.set_stats(user.id, data, None)
                    computed += 1

                # 工作空间统计
                from app.models.workspace import WorkspaceMember
                ws_ids = db.query(WorkspaceMember.workspace_id).filter(
                    WorkspaceMember.user_id == user.id,
                    WorkspaceMember.is_active == True
                ).distinct().all()
                for (ws_id,) in ws_ids:
                    ws_data = statistics.get_overview(db, user.id, ws_id)
                    if ws_data:
                        CacheService.set_stats(user.id, ws_data, ws_id)
                        computed += 1
            except Exception as e:
                logger.warning(f"预计算用户统计失败: user_id={user.id} error={e}")
                continue

        logger.info(f"统计预计算完成: computed={computed} users={len(users)}")
        return {"status": "success", "computed": computed, "users": len(users)}
    except Exception as e:
        logger.error(f"统计预计算任务失败: {e}")
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()


# ==================== 逾期任务检测 ====================

@celery_app.task
def detect_overdue_tasks():
    """检测逾期未完成的任务，自动标记逾期并通知责任人
    每小时执行一次"""
    db = SessionLocal()
    try:
        from app.models.task import Task, TaskStatus
        from app.models.workspace import WorkspaceMember
        from app.tasks.notification_tasks import push_notification_to_user

        now = datetime.utcnow()
        overdue_tasks = db.query(Task).filter(
            Task.status == TaskStatus.PENDING,
            Task.due_date < now,
            Task.is_active == True
        ).all()

        if not overdue_tasks:
            return {"status": "ok", "overdue_count": 0}

        notified = 0
        for task in overdue_tasks:
            try:
                # 自动标记为逾期（扩展状态）
                if hasattr(TaskStatus, 'OVERDUE'):
                    task.status = TaskStatus.OVERDUE
                    db.commit()

                # 通知责任人
                assignee_ids = [task.user_id]
                # 也通知分配到人
                from app.models.task_assignee import task_assignees
                assignee_rows = db.query(task_assignees).filter(
                    task_assignees.c.task_id == task.id
                ).all()
                for row in assignee_rows:
                    if row.user_id not in assignee_ids:
                        assignee_ids.append(row.user_id)

                for uid in assignee_ids:
                    push_notification_to_user.delay(
                        uid,
                        "task",
                        f"任务逾期提醒：{task.title}",
                        f"任务「{task.title}」已于 {task.due_date.strftime('%Y-%m-%d %H:%M')} 逾期，请尽快处理。",
                        "task",
                        task.id
                    )
                    notified += 1

                # 失效任务相关缓存
                CacheService.delete_task_detail(task.id)
                if task.workspace_id:
                    CacheService.invalidate_user_stats(task.user_id)

            except Exception as e:
                logger.warning(f"处理逾期任务失败: task_id={task.id} error={e}")
                continue

        logger.info(f"逾期任务检测完成: overdue={len(overdue_tasks)} notified={notified}")
        return {"status": "success", "overdue_count": len(overdue_tasks), "notified": notified}
    except Exception as e:
        logger.error(f"逾期任务检测失败: {e}")
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()


# ==================== 每日数据清理 ====================

@celery_app.task
def daily_cleanup():
    """每日数据清理：
    1. 清理过期验证码缓存
    2. 清理过期密码重置缓存
    3. 清理临时导出文件（超过24小时）
    4. 清理已读通知（超过30天）"""
    db = SessionLocal()
    try:
        from app.models.notification import Notification
        from app.db.base import get_beijing_time

        # 1. 清理已读通知（30天前）
        cutoff = get_beijing_time() - timedelta(days=30)
        deleted_notifs = db.query(Notification).filter(
            Notification.is_read == True,
            Notification.read_at < cutoff,
            Notification.is_active == True
        ).update({"is_active": False}, synchronize_session=False)
        db.commit()

        # 2. 清理临时导出文件
        import os
        export_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'temp_exports')
        if os.path.exists(export_dir):
            now = datetime.now().timestamp()
            cleaned_files = 0
            for fname in os.listdir(export_dir):
                fpath = os.path.join(export_dir, fname)
                if os.path.isfile(fpath) and (now - os.path.getmtime(fpath)) > 86400:
                    os.remove(fpath)
                    cleaned_files += 1

        logger.info(f"每日清理完成: notifs_deleted={deleted_notifs} files_cleaned={cleaned_files}")
        return {"status": "success", "notifs_deleted": deleted_notifs, "files_cleaned": cleaned_files}
    except Exception as e:
        logger.error(f"每日清理失败: {e}")
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()


# ==================== 系统健康检查 ====================

@celery_app.task
def check_system_health():
    """系统健康检查：探测 Redis、数据库、Celery Worker 状态，写入缓存"""
    import time
    results = {}

    # Redis 探测
    try:
        from app.db.redis_client import get_redis
        start = time.time()
        get_redis().ping()
        results["redis"] = {"status": "ok", "latency_ms": round((time.time() - start) * 1000)}
    except Exception as e:
        results["redis"] = {"status": "error", "message": str(e)}

    # 数据库探测
    try:
        from sqlalchemy import text
        from app.db.session import SessionLocal
        start = time.time()
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        results["database"] = {"status": "ok", "latency_ms": round((time.time() - start) * 1000)}
    except Exception as e:
        results["database"] = {"status": "error", "message": str(e)}

    # Celery Worker 探测（通过检查自身是否能执行）
    results["celery"] = {"status": "ok", "worker": True}

    # 写入缓存供监控面板读取（60秒TTL）
    try:
        from app.db.redis_client import get_redis
        import json as _json
        get_redis().setex("system:health:check", 60, _json.dumps({
            **results,
            "timestamp": datetime.now().isoformat(),
            "status": "ok" if all(r["status"] == "ok" for r in results.values()) else "degraded"
        }))
    except Exception:
        pass

    logger.info(f"健康检查: {results}")
    return results


# ==================== 到期前提醒（任务 + 日程 ====================

@celery_app.task
def send_due_soon_reminders():
    """到期前 6 小时发邮件提醒（任务截止 + 日程开始）
    每 30 分钟跑一次，窗口 [5.5h, 6.5h] 防重复"""
    import asyncio as _asyncio
    from app.services.email_service import send_html_email_sync

    db = SessionLocal()
    redis_client = None
    try:
        from app.db.redis_client import get_redis
        redis_client = get_redis()
    except Exception:
        pass  # Redis 不可用时降级：仍会发，但可能重复

    now = datetime.now()
    # 提醒窗口：5.5h ~ 6.5h 后到期
    window_start = now + timedelta(hours=5.5)
    window_end = now + timedelta(hours=6.5)

    reminded_count = 0

    # --- 1. 任务提醒 ---
    try:
        from app.models.task import Task, TaskStatus
        from app.models.user import User as UserModel

        due_soon_tasks = db.query(Task).filter(
            Task.status == TaskStatus.PENDING,
            Task.due_date >= window_start,
            Task.due_date <= window_end,
            Task.is_active == True,
        ).all()

        for task in due_soon_tasks:
            # Redis 去重
            dedup_key = f"remind:task:{task.id}:{task.due_date.strftime('%Y%m%d%H')}"
            if redis_client and redis_client.exists(dedup_key):
                continue

            # 收集要通知的用户（创建者 + 负责人 + 分配人）
            to_notify = set()
            if task.user_id:
                to_notify.add(task.user_id)
            if task.assignee_id:
                to_notify.add(task.assignee_id)
            # 多人分配
            try:
                from app.models.task_assignee import task_assignees
                rows = db.query(task_assignees).filter(task_assignees.c.task_id == task.id).all()
                for r in rows:
                    to_notify.add(r.user_id)
            except Exception:
                pass

            for uid in to_notify:
                user = db.query(UserModel).filter(UserModel.id == uid, UserModel.is_active == True).first()
                if not user or not user.email:
                    continue
                name = user.nickname or user.real_name or user.email
                html = f"""
                <html><body style="font-family: -apple-system, Segoe UI, sans-serif; padding: 20px;">
                <h3 style="color:#6640C2;">📋 任务即将到期提醒</h3>
                <p><strong>{name}</strong>，您好：</p>
                <p>任务 <strong style="color:#6640C2;">「{task.title}」</strong> 将在 <strong>6 小时后</strong>到期：</p>
                <blockquote style="background:#f8f7ff;border-left:3px solid #6640C2;padding:10px 15px;">
                  截止时间：{task.due_date.strftime('%Y-%m-%d %H:%M')}<br>
                  工作空间：{task.workspace_id or '个人模式'}
                </blockquote>
                <p>请尽快处理 ✨</p>
                </body></html>"""
                try:
                    send_html_email_sync(user.email, f"⏰ 任务到期提醒：{task.title}", html)
                    reminded_count += 1
                except Exception:
                    pass

            if redis_client:
                redis_client.setex(dedup_key, 3600, "1")  # 1 小时内不重复
    except Exception as e:
        logger.error(f"任务提醒失败: {e}")

    # --- 2. 日程提醒 ---
    try:
        from app.models.calendar_event import CalendarEvent, EventParticipant

        due_soon_events = db.query(CalendarEvent).filter(
            CalendarEvent.start_time >= window_start,
            CalendarEvent.start_time <= window_end,
            CalendarEvent.is_active == True,
        ).all()

        for evt in due_soon_events:
            dedup_key = f"remind:event:{evt.id}:{evt.start_time.strftime('%Y%m%d%H')}"
            if redis_client and redis_client.exists(dedup_key):
                continue

            # 收集参与者
            to_notify = set()
            if evt.created_by:
                to_notify.add(evt.created_by)
            try:
                participants = db.query(EventParticipant).filter(EventParticipant.event_id == evt.id).all()
                for p in participants:
                    to_notify.add(p.user_id)
            except Exception:
                pass

            for uid in to_notify:
                user = db.query(UserModel).filter(UserModel.id == uid, UserModel.is_active == True).first()
                if not user or not user.email:
                    continue
                name = user.nickname or user.real_name or user.email
                location = getattr(evt, 'location', None) or ''
                html = f"""
                <html><body style="font-family: -apple-system, Segoe UI, sans-serif; padding: 20px;">
                <h3 style="color:#6640C2;">📅 日程即将开始提醒</h3>
                <p><strong>{name}</strong>，您好：</p>
                <p>日程 <strong style="color:#6640C2;">「{evt.title}」</strong> 将在 <strong>6 小时后</strong>开始：</p>
                <blockquote style="background:#f8f7ff;border-left:3px solid #6640C2;padding:10px 15px;">
                  开始时间：{evt.start_time.strftime('%Y-%m-%d %H:%M')}<br>
                  结束时间：{evt.end_time.strftime('%H:%M')}<br>
                  {'地点：' + location if location else ''}
                </blockquote>
                <p>请安排好时间 ✨</p>
                </body></html>"""
                try:
                    send_html_email_sync(user.email, f"⏰ 日程提醒：{evt.title}", html)
                    reminded_count += 1
                except Exception:
                    pass

            if redis_client:
                redis_client.setex(dedup_key, 3600, "1")
    except Exception as e:
        logger.error(f"日程提醒失败: {e}")

    db.close()
    logger.info(f"到期前提醒完成: sent={reminded_count}")
    return {"status": "ok", "reminded": reminded_count}
