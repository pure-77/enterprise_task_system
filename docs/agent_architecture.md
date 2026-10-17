# Agent 全链路架构文档

> 从用户在前端输入 "帮我创建任务【写周报】，明天下午6点截止" 到页面出现结果，
> 中间经过的每一个类、方法、配置项、文件位置。

---

## 一、总览调用链（按执行顺序）

```
用户输入 "帮我创建任务..."
        │
        ▼
  前端 Index.vue ── handleSend()
        │
        ▼
  agentStore.sendMessage(text, workspaceId)
        │
        ▼
  POST /api/v1/agent/chat          ← FastAPI 路由层
        │
        ▼
  AgentService(workspace_id, user).chat()  ← 核心编排
        │
        ├─ ① _route_intent()            → 意图识别（关键字匹配）
        ├─ ② AgentMemory.load()         → Redis 加载历史对话
        ├─ ③ ToolRegistry.get_schemas_by_group("task") → 只加载 task 组 tools
        ├─ ④ get_llm(has_image=False)   → 选 LLM Provider
        │     └─ DeepSeekProvider.chat(messages, tools)
        │
        │        ┌─ LLM 返回 tool_call: create_task(title="写周报", ...)
        │        │
        ├─ ⑤ ToolRegistry.execute(tool_call, context)
        │     └─ _handler_create_task(**kwargs, context={user, workspace_id})
        │           └─ task_crud.create(db, task_in, user_id, workspace_id)
        │                 └─ INSERT INTO tasks ... （直调现有 CRUD）
        │
        ├─ ⑥ 把 tool_result 回喂给 LLM → LLM 生成自然语言回复
        ├─ ⑦ AgentMemory.save(user_msg, assistant_reply)  → Redis 存新对话
        │
        ▼
  返回 { reply, tool_calls, session_id, model_used }
        │
        ▼
  前端 Index.vue ── store.appendAssistantMsg() → 渲染 Markdown
```

---

## 二、各环节详解

### 环节 1：前端发送

| 步骤 | 类/方法 | 文件位置 | 说明 |
|------|---------|---------|------|
| 1.1 | `Index.vue` `handleSend()` | `frontend/src/views/agent/Index.vue` | 读取输入框 → 调 `store.sendMessage()` |
| 1.2 | `agentStore.sendMessage(text, workspaceId)` | `frontend/src/pinia/agentStore.js` | 追加用户消息 → 调 API |
| 1.3 | `api/agent.js` `chat(data)` | `frontend/src/api/agent.js` | `POST /api/v1/agent/chat`，带 workspace_id |

**关键配置**：前端从 `workspaceStore.currentWorkspace.id` 取当前空间 ID，null 自动转 0（个人模式）。

---

### 环节 2：FastAPI 路由层

| 步骤 | 类/方法 | 文件位置 | 说明 |
|------|---------|---------|------|
| 2.1 | `router = APIRouter(prefix="/api/v1/agent")` | `backend/app/modules/agent/router.py` | 模块入口，在 `main.py` 注册 |
| 2.2 | `agent_chat()` 端点 | `backend/app/modules/agent/router.py:25` | `POST /chat`，接收 `AgentChatRequest` |
| 2.3 | `Depends(get_current_user)` | — | JWT 鉴权，注入当前用户 |
| 2.4 | `workspace_id or 0` | `router.py:51` | None 兜底为 0（个人模式） |

**Pydantic Schema**（`backend/app/modules/agent/schemas.py`）：

| Schema | 字段 | 说明 |
|--------|------|------|
| `AgentChatRequest` | `message`, `workspace_id`, `session_id`, `images` | 前端请求体 |
| `AgentChatResponse` | `reply`, `tool_calls[]`, `session_id`, `model_used` | 返回体 |
| `AgentToolCall` | `name`, `args`, `result`, `success` | 单个工具调用记录 |

---

### 环节 3：核心编排 AgentService

文件：`backend/app/modules/agent/service.py`

```python
class AgentService:
    def __init__(self, user, workspace_id=0, session_id=None): ...
    async def chat(self, message, has_image=False) -> dict: ...
```

`chat()` 方法内部流程：

| 步骤 | 调用 | 类/方法 | 文件 |
|------|------|---------|------|
| 3.1 | 意图识别 | `_route_intent(user_message)` | `service.py:63` |
| 3.2 | 加载记忆 | `AgentMemory(self.user.id, self.workspace_id, session_id).load()` | `memory.py:44` |
| 3.3 | System Prompt 注入 | `settings.AGENT_SYSTEM_PROMPT + 时间 + workspace_id` | `service.py:111-124` |
| 3.4 | 加载工具 | `ToolRegistry.get_schemas_by_group(intent_group)` | `tool_registry.py:69` |
| 3.5 | 选 LLM | `get_llm(has_image=has_image)` | `llm_provider.py:164` |
| 3.6 | 主循环（最多 10 轮） | `llm.chat() → ToolRegistry.execute() → llm.chat() → ...` | `service.py` chat 方法内 |
| 3.7 | 存记忆 | `AgentMemory.save()` | `memory.py:71` |
| 3.8 | 返回 | `AgentChatResponse(reply=..., tool_calls=...)` | `schemas.py:35` |

**意图识别表**（`_route_intent()`）：

| 关键字 | 路由到工具组 |
|--------|-------------|
| 任务/待办/截止/创建任务/写周报 | `task` |
| 日程/会议/日历/几点/安排 | `calendar` |
| 消息/聊天/群聊/IM/会话 | `im` |
| 考勤/打卡/签到/上班/下班 | `attendance` |
| 通知/未读/消息提醒 | `notification` |
| 审批/请假/报销 | `approval` |
| 统计/完成率/数据/报表 | `statistics` |
| 成员/同事/团队/部门/人 | `org` |
| 文件/上传/下载/文档 | `file` |
| 公告/通知栏 | `announcement` |
| （未命中） | 加载全部工具（兜底） |

---

### 环节 4：LLM Provider 抽象层

文件：`backend/app/modules/agent/llm_provider.py`

```python
class LLMProvider(ABC):           # 抽象基类
    async def chat(self, messages, tools) -> str: ...

class DeepSeekProvider(LLMProvider):   # 默认推理引擎
class QwenVLProvider(LLMProvider):     # 多模态图片理解
class QwenTextProvider(LLMProvider):   # 备选推理 / 降级

def get_llm(has_image=False, use_qwen=False) -> LLMProvider:  # 工厂路由
```

**配置项**（`backend/app/core/config.py`）：

| 配置 | .env 变量 | 默认值 | 说明 |
|------|----------|--------|------|
| `DEEPSEEK_API_KEY` | `DEEPSEEK_API_KEY` | — | 必填 |
| `DEEPSEEK_BASE_URL` | `DEEPSEEK_BASE_URL` | `https://api.deepseek.com/v1` | 兼容 OpenAI 协议 |
| `DEEPSEEK_MODEL` | `DEEPSEEK_MODEL` | `deepseek-chat` | Function Calling 模型 |
| `QWEN_API_KEY` | `QWEN_API_KEY` | — | 多模态时必填 |
| `QWEN_BASE_URL` | `QWEN_BASE_URL` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | — |
| `QWEN_TEXT_MODEL` | `QWEN_TEXT_MODEL` | `qwen-plus` | 备选推理 |
| `QWEN_VL_MODEL` | `QWEN_VL_MODEL` | `qwen-vl-max` | 图片理解 |
| `AGENT_MAX_TOOL_ROUNDS` | `AGENT_MAX_TOOL_ROUNDS` | `10` | 主循环最大轮数 |
| `AGENT_SYSTEM_PROMPT` | `AGENT_SYSTEM_PROMPT` | （默认 prompt） | Agent 人设 |

**LLM 路由逻辑**（`get_llm()`）：

```python
if use_qwen:                    # 显式指定用千问
    return QwenTextProvider()
if has_image:                   # 检测到图片 → 千问 VL
    return QwenVLProvider()
try:                            # 默认 → DeepSeek
    return DeepSeekProvider()
except Exception:               # DS 挂了 → 降级千问
    return QwenTextProvider()
```

---

### 环节 5：工具注册中心 ToolRegistry

文件：`backend/app/modules/agent/tool_registry.py`

```python
class ToolRegistry:       # 单例（通过类方法访问）
    @classmethod
    def register(cls, name, group, schema, handler, description): ...
    
    @classmethod
    def get_all_schemas(cls) -> list[dict]: ...              # 全部 JSON Schema
    @classmethod
    def get_schemas_by_group(cls, group: str) -> list[dict]: ...  # 按组加载
    @classmethod
    async def execute(cls, tool_call, context: dict) -> str: ...   # 执行工具
    @classmethod
    def list_tools(cls) -> list[dict]: ...                  # /api/v1/agent/tools
```

**启动时注册**（`backend/app/modules/agent/tools/__init__.py`）：

```python
def register_all_tools():
    register_task_tools()          # 4 个工具
    register_calendar_tools()      # 3 个工具
    register_im_tools()            # 3 个工具
    register_attendance_tools()    # 3 个工具
    register_notification_tools()  # 2 个工具
    register_announcement_tools()  # 1 个工具
    register_approval_tools()      # 1 个工具
    register_statistics_tools()    # 1 个工具
    register_org_tools()           # 1 个工具
    register_file_tools()          # 1 个工具
```

在 `backend/app/main.py` 的 `startup` 事件调用：
```python
@app.on_event("startup")
async def on_startup():
    from app.modules.agent.tools import register_all_tools
    register_all_tools()   # 进程启动时注册全部 20 个工具
```

---

### 环节 6：工具 Handler 执行

每个工具文件结构统一（以 `backend/app/modules/agent/tools/task_tools.py` 为例）：

```python
# 1. Schema 函数 — 返回给 LLM 的 JSON Schema
def _schema_create_task() -> dict: ...

# 2. Handler 函数 — 实际执行
async def _handler_create_task(title: str, due_date: str = None, 
                               workspace_id: int = None, context: dict = None) -> str:
    user: User = context["user"]
    db: Session = next(get_db())
    
    # workspace_id 兜底（LLM 没传时从 context 取）
    if workspace_id is None:
        workspace_id = context.get("workspace_id")
    
    # 直调现有 CRUD
    from app.crud.task import task as task_crud
    task = task_crud.create(db, task_in, user_id=user.id, 
                            workspace_id=workspace_id)
    return json.dumps({"success": True, "task_id": task.id})

# 3. 注册函数 — ToolRegistry.register()
def register_task_tools():
    ToolRegistry.register(
        name="create_task", group="task",
        schema=_schema_create_task(),
        handler=_handler_create_task,
        description="创建一个新任务"
    )
```

**已注册工具清单**：

| 工具组 | 文件 | 工具名 | Handler 函数 |
|--------|------|--------|--------------|
| **task** | `task_tools.py` | `create_task` | `_handler_create_task` |
| | | `list_tasks` | `_handler_list_tasks` |
| | | `complete_task` | `_handler_complete_task` |
| | | `update_task_status` | `_handler_update_task_status` |
| **calendar** | `calendar_tools.py` | `list_calendar_events` | `_handler_list_events` |
| | | `create_calendar_event` | `_handler_create_event` |
| | | `delete_calendar_event` | `_handler_delete_event` |
| **im** | `im_tools.py` | `send_im_message` | `_handler_send_im_message` |
| | | `list_im_conversations` | `_handler_list_conversations` |
| | | `list_im_messages` | `_handler_list_messages` |
| **attendance** | `attendance_tools.py` | `check_in` | `_handler_check_in` |
| | | `check_out` | `_handler_check_out` |
| | | `get_attendance_stats` | `_handler_attendance_stats` |
| **notification** | `notification_tools.py` | `list_notifications` | `_handler_list_notifications` |
| | | `mark_notification_read` | `_handler_mark_read` |
| | | `list_announcements` | `_handler_list_announcements` |
| **misc** | `misc_tools.py` | `my_approvals` | `_handler_my_approvals` |
| | | `get_statistics` | `_handler_get_stats` |
| | | `list_workspace_members` | `_handler_list_members` |
| | | `search_files` | `_handler_search_files` |

**所有 Handler 统一签名**：
```python
async def _handler_xxx(..., workspace_id: int = None, context: dict = None) -> str:
```
- 返回值统一 `json.dumps({...}, ensure_ascii=False)` —— LLM 直接可读
- `context` 字典固定包含 `{"user": User对象, "workspace_id": int}`

---

### 环节 7：对话记忆

文件：`backend/app/modules/agent/memory.py`

```python
class AgentMemory:
    def __init__(self, workspace_id=None, user_id=None, session_id=None): ...
    
    # Redis Key: agent:memory:{workspace_id}:{user_id}:{session_id}
    def key(self) -> str: ...
    
    def load(self) -> list[dict]: ...      # 从 Redis 读取（JSON 数组）
    def save(self, user_message, assistant_reply, image_url=None): ...
    def clear(self): ...
    def count(self) -> int: ...
```

**Redis 配置**（`backend/app/core/config.py`）：

| 配置 | 值 | 说明 |
|------|-----|------|
| `REDIS_URL` | `redis://localhost:6379/0` | — |
| 记忆 TTL | 24 小时 | 通过 `setex(key, 86400, json)` |
| 最大历史轮数 | 20 | 超出后丢弃最早的 |

**前端持久化**（`frontend/src/pinia/agentStore.js`）：

| 存储 | Key | 内容 | 生命周期 |
|------|-----|------|---------|
| localStorage | `agent_sessions` | 会话列表 | 永久 |
| localStorage | `agent_msgs_{session_id}` | 每个会话的消息数组 | 永久 |
| Redis | `agent:memory:ws:user:session` | 多轮对话上下文 | 24h 过期 |

---

### 环节 8：后端返回 + 前端渲染

后端返回（`AgentChatResponse`）：
```json
{
  "reply": "任务「写周报」已创建，截止时间：2026-09-26 18:00 ✅",
  "tool_calls": [
    {"name": "create_task", "args": {...}, "result": "{...}", "success": true}
  ],
  "session_id": "abc123",
  "model_used": "deepseek-chat"
}
```

前端渲染（`frontend/src/views/agent/Index.vue`）：

| 元素 | 默认视图 | 开发者模式（⚙️ 开启） |
|------|---------|---------------------|
| Agent 回复 | `v-html="renderMd(msg.content)"` Markdown 渲染 | 同左 |
| 工具调用卡片 | **隐藏** | 显示 ✅/❌ + 参数 + 结果 |
| 快捷提示 | 5 条预设 prompt 卡片 | 同左 |
| 会话列表 | 左侧边栏，localStorage 持久化 | 同左 |

**Markdown 渲染**（`frontend/src/utils/markdown.js`）：
- 库：`markdown-it@^14.1.0` + `highlight.js@^11.10.0`
- 支持：**粗体** · *斜体* · `inline code` · 代码块（语法高亮） · 列表 · 链接

---

## 三、配置文件汇总

### 后端（`backend/.env`）

```env
# ===== Agent / LLM =====
DEEPSEEK_API_KEY=sk-xxx                    # 必填
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat

QWEN_API_KEY=sk-xxx                        # 多模态时填
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_TEXT_MODEL=qwen-plus
QWEN_VL_MODEL=qwen-vl-max

AGENT_MAX_TOOL_ROUNDS=10                   # 主循环最大轮数
AGENT_SYSTEM_PROMPT=                       # 可选，默认值在 config.py

# ===== Redis =====
REDIS_URL=redis://localhost:6379/0         # 记忆存储

# ===== Celery（定时提醒） =====
CELERY_BROKER_URL=redis://localhost:6379/1
```

### 后端（`backend/app/core/config.py`）

| 字段 | 类型 | 默认值 |
|------|------|--------|
| `AGENT_MAX_TOOL_ROUNDS` | int | 10 |
| `AGENT_SYSTEM_PROMPT` | str | 见 config.py |
| `DEEPSEEK_API_KEY` | str | — |
| `DEEPSEEK_BASE_URL` | str | `https://api.deepseek.com/v1` |
| `DEEPSEEK_MODEL` | str | `deepseek-chat` |
| `QWEN_API_KEY` | str | — |
| `QWEN_BASE_URL` | str | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `QWEN_TEXT_MODEL` | str | `qwen-plus` |
| `QWEN_VL_MODEL` | str | `qwen-vl-max` |

### Celery Beat 定时任务（`backend/app/core/celery_config.py`）

| 任务 | 触发 | 说明 |
|------|------|------|
| `precompute_user_stats` | 每 10 分钟 | 统计预计算 |
| `detect_overdue_tasks` | 每小时 | 逾期检测 |
| `daily_cleanup` | 每天凌晨 3 点 | 数据清理 |
| `check_system_health` | 每 5 分钟 | 健康检查 |
| **`send_due_soon_reminders`** | **每 30 分钟** | **任务/日程到期前 6 小时邮件提醒** |

---

## 四、文件清单总览

### 后端 Agent 模块（`backend/app/modules/agent/`）

| 文件 | 行数 | 职责 |
|------|------|------|
| `__init__.py` | 9 | 模块入口，导出 router |
| `schemas.py` | 38 | Pydantic 请求/响应模型 |
| `router.py` | ~100 | 3 个 API 端点 |
| `service.py` | ~200 | 核心编排 + 意图识别 + 主循环 |
| `llm_provider.py` | ~180 | 3 个 LLM 实现 + 工厂路由 |
| `tool_registry.py` | ~140 | 单例注册中心 |
| `memory.py` | ~130 | Redis 短期记忆 |
| `tools/__init__.py` | ~25 | `register_all_tools()` 统一入口 |
| `tools/task_tools.py` | ~340 | 4 个任务工具 |
| `tools/calendar_tools.py` | ~270 | 3 个日程工具 |
| `tools/im_tools.py` | ~105 | 3 个 IM 工具 |
| `tools/attendance_tools.py` | ~140 | 3 个考勤工具 |
| `tools/notification_tools.py` | ~120 | 3 个通知/公告工具 |
| `tools/misc_tools.py` | ~190 | 审批/统计/组织/文件 各 1 个 |

### 前端 Agent 模块（`frontend/src/`）

| 文件 | 职责 |
|------|------|
| `views/agent/Index.vue` | Agent 主页面（对话 UI） |
| `pinia/agentStore.js` | Agent 状态管理（会话 + 消息持久化） |
| `api/agent.js` | Agent API 封装 |
| `utils/markdown.js` | Markdown 渲染工具 |
| `router/routes.js` | +`/agent` 路由 |
| `layouts/MainLayout.vue` | +侧边栏「AI 助手」分组 + ⚙️ 开发者 toggle |

### 共享/基础设施（已有的，被 Agent 复用）

| 文件 | 被 Agent 怎么用 |
|------|----------------|
| `backend/app/core/config.py` | 读取 LLM/Agent 配置 |
| `backend/app/main.py` | 注册路由 + startup 注册工具 |
| `backend/app/db/redis_client.py` | AgentMemory 读写 |
| `backend/app/services/email_service.py` | `send_html_email_sync()` 定时提醒发邮件 |
| `backend/app/tasks/scheduler_tasks.py` | `send_due_soon_reminders()` 定时任务 |
| `backend/app/core/celery_config.py` | Beat schedule 注册 |
| 各业务模块的 `crud/*.py` | Handler 直调（task_crud, conversation_crud 等） |
| 各业务模块的 `models/*.py` | SQLAlchemy ORM 查询 |

---

## 五、HTTP API 清单

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/agent/chat` | 核心对话端点 |
| GET | `/api/v1/agent/tools` | 列出所有已注册工具（调试用） |
| DELETE | `/api/v1/agent/memory` | 清空当前会话的 Redis 记忆 |

---

## 六、启动命令

```bash
# 1. 后端 API
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8001

# 2. Celery Worker（定时任务执行）
..\.venv\Scripts\python.exe -m celery -A app.core.celery_config worker --pool=solo

# 3. Celery Beat（定时任务触发）
..\.venv\Scripts\python.exe -m celery -A app.core.celery_config beat

# 4. 前端
cd frontend
npm run dev
```
