import random
import asyncio
from email.message import EmailMessage
from aiosmtplib import SMTP
from app.core.config import settings


class EmailService:
    """邮件服务类 - 面试考点：异步发送邮件，避免阻塞主线程"""

    @staticmethod
    def generate_verify_code(length: int = 6) -> str:
        """生成验证码 - 面试考点：使用random生成数字验证码"""
        return "".join([str(random.randint(0, 9)) for _ in range(length)])

    @staticmethod
    async def send_verify_code(email: str, code: str) -> bool:
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

            # ✅ 这是 QQ 邮箱 唯一 能成功的写法
            async with SMTP(
                    hostname=settings.EMAIL_HOST,
                    port=settings.EMAIL_PORT,
                    use_tls=True,  # 465端口必须用这个
                    timeout=15
            ) as smtp:
                await smtp.login(settings.EMAIL_USERNAME, settings.EMAIL_PASSWORD)
                await smtp.send_message(message)

            return True

        except Exception as e:
            print(f"发送邮件失败: {e}")
            return False

    @staticmethod
    async def send_verification_code(email: str) -> str:
        """发送验证码 - 生成并发送验证码"""
        code = EmailService.generate_verify_code()
        await EmailService.send_verify_code(email, code)
        return code

    @staticmethod
    async def send_verify_code_async(email: str, code: str):
        """异步发送验证码 - 面试考点：后台任务，不阻塞响应"""
        await EmailService.send_verify_code(email, code)

    @staticmethod
    def send_invitation_email(email: str, workspace_name: str, inviter_name: str, role: str) -> bool:
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

            import asyncio as _asyncio
            async def _send():
                async with SMTP(
                        hostname=settings.EMAIL_HOST,
                        port=settings.EMAIL_PORT,
                        use_tls=True,
                        timeout=15
                ) as smtp:
                    await smtp.login(settings.EMAIL_USERNAME, settings.EMAIL_PASSWORD)
                    await smtp.send_message(message)

            _asyncio.run(_send())
            return True
        except Exception as e:
            print(f"发送邀请邮件失败: {e}")
            return False


email_service = EmailService()


def send_html_email_sync(to_email: str, subject: str, html_content: str) -> bool:
    """同步发送 HTML 邮件（供 Celery 等非 async 上下文调用）"""
    try:
        message = EmailMessage()
        message["From"] = settings.EMAIL_FROM
        message["To"] = to_email
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
        return True
    except Exception as e:
        print(f"发送邮件失败 [{subject}]: {e}")
        return False


