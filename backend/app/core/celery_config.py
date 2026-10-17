from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

# 创建 Celery 实例
celery_app = Celery(
    'personal_task_system',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        'app.tasks.excel_tasks',
        'app.tasks.email_tasks',
        'app.tasks.notification_tasks',
        'app.tasks.scheduler_tasks',
    ]
)

# 配置 Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,
    worker_concurrency=4,
    task_acks_late=True,
    task_default_queue='default',
    task_default_exchange='default',
    task_default_routing_key='default',
    broker_connection_retry_on_startup=True,
    # 任务重试中间件
    task_publish_retry=True,
    task_publish_retry_policy={
        'max_retries': 3,
        'interval_step': 2,
        'interval_max': 30,
    },
)

# ==================== Celery Beat 定时调度 ====================
celery_app.conf.beat_schedule = {
    # 每 10 分钟：预计算统计数据（写入缓存，用户零等待）
    'precompute-stats-every-10min': {
        'task': 'app.tasks.scheduler_tasks.precompute_user_stats',
        'schedule': crontab(minute='*/10'),
    },
    # 每小时：检测逾期任务并通知
    'detect-overdue-tasks-hourly': {
        'task': 'app.tasks.scheduler_tasks.detect_overdue_tasks',
        'schedule': crontab(minute=0),
    },
    # 每天凌晨 3 点：数据清理
    'daily-cleanup-at-3am': {
        'task': 'app.tasks.scheduler_tasks.daily_cleanup',
        'schedule': crontab(hour=3, minute=0),
    },
    # 每 5 分钟：系统健康检查
    'health-check-every-5min': {
        'task': 'app.tasks.scheduler_tasks.check_system_health',
        'schedule': crontab(minute='*/5'),
    },
    # 每 30 分钟：到期前 6 小时邮件提醒（任务 + 日程）
    'remind-due-soon-every-30min': {
        'task': 'app.tasks.scheduler_tasks.send_due_soon_reminders',
        'schedule': crontab(minute='0,30'),
    },
}

# celery -A app.core.celery_config worker --loglevel=info --pool=solo
# celery -A app.core.celery_config beat --loglevel=info
