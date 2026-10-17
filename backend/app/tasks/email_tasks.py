"""异步邮件发送任务 — 将邮件发送从请求线程剥离到 Celery Worker"""
import asyncio
import logging
from email.message import EmailMessage
from aiosmtplib import SMTP
from app.core.config import settings
from app.core.celery_config import celery_app

logger = logging.getLogger("celery.email")


@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def send_verify_code_email(self, email: str, code: str):
    """异步发送验证码邮件"""
    try:
        message = EmailMessage()
        message["From"] = settings.EMAIL_FROM
        message["To"] = email
        message["Subject"] = "个人任务管理系统 - 验证码"

        html_content = f"""
        <html>
            <body>
                <h2>验证码</h2>
                <p>您的验证码是：<strong style="font-size: 24px; color: #409EFF;">{code}</strong></p>
                <p>验证码有效期为5分钟，请尽快使用。</p>
            </body>
        </html>
        """
        message.set_content(html_content, subtype="html")

        async def _send():
            async with SMTP(
                hostname=settings.EMAIL_HOST,
                port=settings.EMAIL_PORT,
                use_tls=True,
                timeout=15
            ) as smtp:
                await smtp.login(settings.EMAIL_USERNAME, settings.EMAIL_PASSWORD)
                await smtp.send_message(message)

        asyncio.run(_send())
        logger.info(f"验证码邮件发送成功: {email}")
        return {"status": "success", "email": email}
    except Exception as e:
        logger.warning(f"验证码邮件发送失败: {email}, error={e}")
        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f"验证码邮件重试次数耗尽: {email}")
            return {"status": "failed", "email": email, "error": str(e)}


@celery_app.task(bind=True, max_retries=3, default_retry_delay=10)
def send_invitation_email(self, email: str, workspace_name: str, inviter_name: str, role: str):
    """异步发送邀请邮件"""
    try:
        role_label = "管理员" if role == "admin" else "成员"
        message = EmailMessage()
        message["From"] = settings.EMAIL_FROM
        message["To"] = email
        message["Subject"] = f"任务管理系统 - 邀请加入「{workspace_name}」"

        html_content = f"""
        <html>
            <body>
                <h2>团队协作邀请</h2>
                <p><strong>{inviter_name}</strong> 邀请你加入工作空间 <strong>「{workspace_name}」</strong></p>
                <p>角色：<strong>{role_label}</strong></p>
                <p>请登录系统，在「邀请通知」页面处理该邀请。</p>
            </body>
        </html>
        """
        message.set_content(html_content, subtype="html")

        async def _send():
            async with SMTP(
                hostname=settings.EMAIL_HOST,
                port=settings.EMAIL_PORT,
                use_tls=True,
                timeout=15
            ) as smtp:
                await smtp.login(settings.EMAIL_USERNAME, settings.EMAIL_PASSWORD)
                await smtp.send_message(message)

        asyncio.run(_send())
        logger.info(f"邀请邮件发送成功: {email}, workspace={workspace_name}")
        return {"status": "success", "email": email}
    except Exception as e:
        logger.warning(f"邀请邮件发送失败: {email}, error={e}")
        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f"邀请邮件重试次数耗尽: {email}")
            return {"status": "failed", "email": email, "error": str(e)}


@celery_app.task(bind=True, max_retries=2, default_retry_delay=5)
def send_generic_email(self, email: str, subject: str, html_content: str):
    """异步发送通用邮件"""
    try:
        message = EmailMessage()
        message["From"] = settings.EMAIL_FROM
        message["To"] = email
        message["Subject"] = subject
        message.set_content(html_content, subtype="html")

        async def _send():
            async with SMTP(
                hostname=settings.EMAIL_HOST,
                port=settings.EMAIL_PORT,
                use_tls=True,
                timeout=15
            ) as smtp:
                await smtp.login(settings.EMAIL_USERNAME, settings.EMAIL_PASSWORD)
                await smtp.send_message(message)

        asyncio.run(_send())
        logger.info(f"通用邮件发送成功: {email}, subject={subject}")
        return {"status": "success", "email": email}
    except Exception as e:
        logger.warning(f"通用邮件发送失败: {email}, error={e}")
        try:
            self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(f"通用邮件重试次数耗尽: {email}")
            return {"status": "failed", "email": email, "error": str(e)}
