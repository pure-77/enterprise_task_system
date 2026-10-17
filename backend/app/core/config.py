from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """全局配置类 - 面试考点：使用pydantic-settings进行配置管理，类型安全且支持环境变量"""
    
    # 数据库配置
    DATABASE_URL: str
    
    # Redis配置
    REDIS_URL: str
    
    # 邮件配置
    EMAIL_HOST: str
    EMAIL_PORT: int
    EMAIL_USERNAME: str
    EMAIL_PASSWORD: str
    EMAIL_FROM: str
    
    # JWT配置 — SECRET_KEY 改为可选，优先从数据库动态读取（方案 A：首次启动自动生成持久化）
    SECRET_KEY: str = ""   # .env 里可留空，启动时从 system_config 表加载，没有就自动生成
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120  # 2小时，前端有拦截器自动 refresh；拉长减少 Redis 重启导致的掉线
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # 应用配置
    APP_NAME: str = "Personal Task System"
    DEBUG: bool = False
    
    # 验证码配置
    VERIFY_CODE_EXPIRE_SECONDS: int = 300  # 5分钟
    VERIFY_CODE_SEND_INTERVAL: int = 60    # 1分钟防刷

    # 缓存过期配置
    USER_INFO_CACHE_TTL: int = 1800        # 用户信息缓存 30 分钟
    STATS_CACHE_TTL: int = 300             # 统计数据缓存 5 分钟
    PERMISSION_CACHE_TTL: int = 600        # 权限缓存 10 分钟
    TASK_DETAIL_CACHE_TTL: int = 300       # 任务详情缓存 5 分钟
    STATS_REFRESH_INTERVAL: int = 300      # 统计异步刷新间隔 5 分钟

    # ==================== Agent / LLM 配置 ====================
    # DeepSeek 配置（默认推理引擎）
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # 通义千问配置（多模态图片理解 + 备选推理）
    QWEN_API_KEY: str = ""
    QWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    QWEN_MODEL: str = "qwen-plus"
    QWEN_VL_MODEL: str = "qwen-vl-max"

    # Agent 通用配置
    AGENT_MAX_TOOL_ITERATIONS: int = 10     # 单次对话最大工具调用轮次（防死循环）
    AGENT_MEMORY_MAX_ROUNDS: int = 20        # 对话记忆保留最近 N 轮
    AGENT_MEMORY_TTL_SECONDS: int = 86400    # 记忆 Redis TTL（秒），默认 24 小时
    AGENT_SYSTEM_PROMPT: str = """你是「企业办公智能助手」，一个帮助用户操作企业协作平台的 AI Agent。

## 你的能力范围
你可以通过调用工具（tool）来完成以下操作：
- 任务管理：创建、查询、更新、完成任务
- 日程日历：创建、查询、更新会议/日程
- 考勤打卡：上下班打卡、查询记录
- 即时通讯：发送消息、查询会话
- 审批流程：提交审批、查询进度
- 通知公告：查看通知、发布公告
- 文件管理：上传、搜索、预览文件
- 组织架构：查询成员、部门信息
- 数据统计：概览、趋势、完成率

## 工作原则
1. **用户意图优先**：理解用户自然语言的真实意图，选择最合适的工具
2. **参数要精确**：调用工具时参数要完整、格式正确
3. **结果要友好**：工具执行后用自然语言总结结果，不要直接返回原始 JSON
4. **权限要遵守**：只能操作用户有权限的 workspace 和资源
5. **缺参才追问**：当前时间、日期、空间上下文已在下文注入，务必直接使用、不要重复询问；
   仅当关键业务参数确实缺失（如"给谁分配任务""发送给哪个会话"）且无法从上下文推断时，才向用户追问

## 组合指令处理规则
用户一句话可能包含多个操作（如"建任务并通知张三，再约明天下午的评审会"）：
1. 先在心里把整句话拆成若干个独立子操作，识别每个子操作对应的工具
2. 按依赖关系排序执行：需要先查询拿到 ID 的子操作（如找会话、找成员）排在前面
3. 在同一轮回复中连续发起全部所需的工具调用，不要只执行第一个就停下来问用户
4. 每个子操作独立调用一次对应工具；部分子操作失败时继续执行其余子操作，最终汇总时分别说明成功/失败
5. 所有子操作完成后再输出最终自然语言总结；不要在中间步骤对用户说话

## 任务规划规则（plan_tasks）
1. 用户要求"规划 / 拆解 / 安排 / 排期 / 帮我把……准备一下"等**一批任务或一个大目标**时，
   必须调用 plan_tasks 提交完整任务清单，而不是逐个调用 create_task
2. 只有**单个、明确**的任务创建（"创建一个任务：写周报"）才直接使用 create_task
3. plan_tasks 只生成计划、不会创建任务：调用后必须告诉用户"计划已生成，请在卡片上确认"，
   **严禁在用户确认前自行调用 create_task**（这是确认环节的必要等待，不属于追问缺失参数）
4. 计划中的截止时间必须结合注入的当前时间推算成具体的 YYYY-MM-DD HH:mm；
   负责人只在用户明确提及时填写 assignee_name，不确定就留空（默认负责人为用户自己）

## 示例
示例1（复合指令）：
用户：帮我创建任务【写周报】明天下午6点截止，完成后通知张三，再约明天下午3点的评审会
行动：create_task（写周报，截止明天18:00）→ 先 list_workspace_members/list_im_conversations 定位张三 →
      send_im_message（通知）→ create_calendar_event（明天15:00 评审会）→ 汇总结果

示例2（任务规划）：
用户：帮我规划一下下周五的产品上线准备
行动：调用一次 plan_tasks，tasks 中给出多个子任务（如需求确认、测试回归、发布公告、上线复盘），
      各自带合理的优先级与截止时间；然后提示用户在卡片上确认

示例3（先查后做）：
用户：看看我今天的待办，把第一个完成掉
行动：list_tasks（筛选今天/待处理）→ 从结果中取第一个任务 ID → complete_task → 汇报完成情况

## 回复风格
- 简洁明了，不要啰嗦
- 操作成功时给出确认 + 关键结果
- 操作失败时说明原因 + 建议解决方案
- 涉及时间用「YYYY-MM-DD HH:mm」格式
"""

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """获取配置实例 - 面试考点：使用lru_cache缓存配置对象，避免重复读取"""
    return Settings()


settings = get_settings()


def get_jwt_secret(db=None) -> str:
    """
    动态获取 JWT 签名密钥（方案 A：首次启动自动生成并持久化到数据库）
    
    核心设计：用 _resolve_jwt_secret_once() 做懒加载 + 模块级缓存，
    确保第一次调用就锁定 key，后续不管有没有 db session 都返回同一个值
    （签名和验签必须用同一个 key，否则 token 会验签失败）
    
    优先级（database 优先，.env 只是兼容 fallback）：
    1. system_config 表里有 jwt_secret_key → 用数据库里的
    2. .env 里显式配了 SECRET_KEY → 用 .env 的（兼容旧部署）
    3. 都没有 → 自动生成 secrets.token_urlsafe(64) 并写入数据库
    
    关键：只有当密钥"确实来自数据库"时才写入进程缓存。
    因为本函数可能在「没有 db session」的路径被调用（AuditLog / 静态鉴权 /
    WebSocket / 部分路由），若这时把 .env 常量锁进缓存，就会让该进程永久
    使用与其它进程不同的 key → 多 worker 之间签发的 token 互相验签失败
    （表现为重启后登录后被立刻踢回登录页）。
    
    面试考点：
    - 为什么要缓存？避免同一进程内不同调用路径拿到不同 key
    - 为什么不每次随机生成？换 key 会导致所有已签发的 token 验证失败
    - 为什么用 DB 存？key 不硬编码在 .env 里，git 历史不泄露
    """
    # 必须在第一次使用前声明 global（Python 作用域规则）
    global _cached_jwt_secret

    # 已经缓存过 → 直接返回
    if _cached_jwt_secret is not None:
        return _cached_jwt_secret

    # 第一次调用 → 解析（DB 不可用时的兜底值不锁定缓存，避免污染进程）
    secret, from_db = _resolve_jwt_secret_once(db)
    if from_db:
        _cached_jwt_secret = secret
    return secret


# 模块级缓存变量（进程内共享，同一 uvicorn worker 永远同一个 key）
_cached_jwt_secret: Optional[str] = None


def _resolve_jwt_secret_once(db=None) -> tuple:
    """解析 JWT 密钥，返回 (secret, from_db)

    唯一权威来源是数据库 system_config 表。
    即使调用方没传 db（中间件 / WebSocket / 静态鉴权等路径），这里也会
    自行开一个短连接去读 DB，保证「无 db 首次调用」不会退化成 .env 常量，
    从而让所有进程/worker 都拿到同一个密钥。

    from_db=False 表示 DB 暂不可用（例如首次建表前），返回的是兜底值，
    此时调用方不应把它写入进程缓存。
    """
    own_session = False
    if db is None:
        # 懒加载，避免 config 与 db.session 的循环 import
        try:
            from app.db.session import SessionLocal
            db = SessionLocal()
            own_session = True
        except Exception:
            db = None

    try:
        # 1. 从数据库读（生产级做法）
        if db is not None:
            try:
                from app.models.system_config import SystemConfig
                row = db.query(SystemConfig).filter(
                    SystemConfig.config_key == "jwt_secret_key"
                ).first()
                if row and row.config_value:
                    return row.config_value, True

                # 数据库也没有 → 自动生成并写入
                import secrets
                new_key = secrets.token_urlsafe(64)
                new_row = SystemConfig(
                    config_key="jwt_secret_key",
                    config_value=new_key,
                    description="JWT 签名密钥（首次启动自动生成，请勿随意修改）",
                )
                db.add(new_row)
                db.commit()
                db.refresh(new_row)
                return new_row.config_value, True
            except Exception:
                # 并发生成时唯一键冲突 → 回滚后重读一次（别的进程已写入）
                try:
                    db.rollback()
                except Exception:
                    pass
                try:
                    from app.models.system_config import SystemConfig
                    row = db.query(SystemConfig).filter(
                        SystemConfig.config_key == "jwt_secret_key"
                    ).first()
                    if row and row.config_value:
                        return row.config_value, True
                except Exception:
                    pass
    finally:
        if own_session and db is not None:
            try:
                db.close()
            except Exception:
                pass

    # 2. 兜底：用 .env 配置（仅 DB 不可用时，如首次建表前）
    if settings.SECRET_KEY and len(settings.SECRET_KEY) > 8:
        return settings.SECRET_KEY, False

    # 3. 最终兜底：临时随机生成（不持久化、不缓存）
    import secrets
    return secrets.token_urlsafe(64), False
