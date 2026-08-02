from celery import Celery
from app.core.config import settings

# 创建 Celery 实例
celery_app = Celery(
    'personal_task_system',
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=['app.tasks.excel_tasks']
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
    broker_connection_retry_on_startup=True
)

# celery -A app.core.celery_config worker --loglevel=info --pool=solo
