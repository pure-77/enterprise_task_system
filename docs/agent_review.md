# Agent 模块问题排查报告

> 范围：Agent 模块前后端全链路 —— 提示词、意图路由、工具注册与调用、记忆与会话持久化、前端渲染。
> 方式：静态代码审查（未改动任何代码）。标注「待验证」的结论需要实际运行确认。
> 结论优先级：P0 = 功能走不通 / 越权；P1 = 数据与行为错误；P2 = 工程质量与体验。

排查覆盖文件：

| 层 | 文件 |
| --- | --- |
| 后端核心 | `backend/app/modules/agent/service.py`、`router.py`、`schemas.py`、`tool_registry.py`、`memory.py`、`session_service.py`、`llm_provider.py` |
| 工具组 | `backend/app/modules/agent/tools/{__init__,task_tools,calendar_tools,im_tools,notification_tools,attendance_tools,misc_tools}.py` |
| 配置 | `backend/app/core/config.py`（AGENT_SYSTEM_PROMPT / AGENT_* ） |
| 关联业务 | `backend/app/crud/task.py`、`backend/app/api/v1/task.py` |
| 前端 | `frontend/src/views/agent/Index.vue`、`frontend/src/pinia/agentStore.js`、`frontend/src/api/agent.js`、`frontend/src/utils/markdown.js` |

---

## 一、P0：直接导致功能走不通

### 1. 工具分组取空 → 返回「没有可用的工具」死路

`service.py` Step 2：`ToolRegistry.get_schemas_by_group(intent_group)` 返回空列表时，直接回复「抱歉，当前没有可用的工具，请联系管理员」，**而不是降级成全量 tools**。

触发条件有两个：

- **模块注册失败**：`tools/__init__.py` 的 `_safe_register` 只打 warning 并吞掉异常，任何模块的 CRUD 签名变化都会让该组永久消失，用户问「审批」就会拿到上面那句话，且启动日志埋在 warning 级别里。
- **意图分组名与注册组名不一致**：见下一条。

### 2. 意图兜底（Level 2）候选集错误，二级路由实际失效

`service.py` `_llm_classify_intent`：

- 候选集 = `_KEYWORD_ROUTES` 中各组的 group 名 → 包含 `calendar_strong`、`calendar_time`，**但不包含 `calendar`**。
- 而该函数的 prompt 却要求模型只回答 `calendar`。

结果：

| 模型回答 | 是否在候选 | 后果 |
| --- | --- | --- |
| `calendar` | 否 | 返回 `None` → 退化为全量 tools（路由白做） |
| `calendar_strong` | 是 | `get_schemas_by_group("calendar_strong")` → 空 → 撞上第 1 条死路 |
| 其他已注册组名 | 是 | 正常 |

即：Level 2 兜底对「日程」类意图基本不可用。

### 3. 多模态是半成品，VL 分支永不触发

- `schemas.py` 的 `AgentChatRequest` **没有 `image_url` 字段**；`router.py` 用 `getattr(request, "image_url", None)` 取，恒为 `None` → `get_llm(has_image=False)` → 永远走 DeepSeek，`QwenVLProvider` 是死代码。
- 同时 `service.py` 把 `image_url` 作为顶层 key 塞进 OpenAI 格式的 messages（非法字段），若真传图会 400；VL 模型需要的是 `content` 数组 parts 格式。
- `AgentMemory._load_from_mysql` 也把 `image_url` 回灌进 message dict，同样非法。

### 4. 记忆回灌破坏 OpenAI 消息契约

`memory.py` `_load_from_mysql`：

- 会把带 `tool_calls` 的 assistant 消息读回，但**没有配对的 `tool` 消息**。Redis 24h TTL 过期后必然走这条路 → 下一轮请求大概率被 DeepSeek 以「assistant message with tool_calls must be followed by tool messages」拒绝。
- 症状：隔天回到同一会话，对话直接报错。
- 顺带：历史里 assistant 的 `tool_calls` 与本轮实际注入的工具集不一定匹配，也可能被判定为无效调用。

### 5. 会话与 workspace 脱钩 + 前端跨空间混显

- `session_service.py` `get_or_create_session` 只按 `session_key` 查会话，**不校验 `workspace_id`**：切换空间后同一 `session_key` 继续写入旧空间的会话，新空间的对话记录挂到旧会话下。
- `Index.vue` 的 `store.init()` 不传 workspaceId；`agentStore.js` `_refreshCurrentSession` 用 `currentSession?.workspace_id || null` 兜底成 `null` → `/agent/sessions` 返回该用户**所有空间**的会话 → 侧边栏跨空间混显。
- 切换 workspace 时不重置 `currentSession` / `messages`（页面没有 watch workspace）。
- 违反项目既定约束「空间隔离 / 不跨空间泄露」。

---

## 二、P1：工具语义、权限与数据正确性

### 6. 个人空间 `workspace_id = 0` 与 `None` 混用，任务会「消失」

- `tools/task_tools.py` `_handler_create_task` 把 `0` 直接写进 `TaskCreate.workspace_id` → 落库为 `workspace_id = 0`，而不是 `NULL`。
- 个人任务列表按 `workspace_id IS NULL` 过滤（`crud/task.py` 的 `get_multi` else 分支），因此 **Agent 在个人空间创建的任务在列表里查不到**；权限判定也会把它当成「workspace 0 的团队任务」。
- HTTP 侧同样用 truthy 判断（`api/v1/task.py` 的 `if task_in.workspace_id:`），把 0 归到了个人分支，形成两套不一致的语义。
- 个人模式下仍会调用 `get_workspace_member(0, user.id, db)`（task_tools 第 86 行附近）→ 若 workspace 0 没有该用户的成员记录，则**直接 403**。**（待验证）**

### 7. Agent 绕过 HTTP 层的权限规则（越权风险最高）

| 位置 | 问题 |
| --- | --- |
| `task_tools.create_task` | 未校验「普通成员不能创建工作区任务」（HTTP 有：`api/v1/task.py`）；未校验 `assignee_id` 是否空间成员 |
| `misc_tools.get_file_detail` | 无任何成员校验，任意用户可读任意文件元数据（含下载 url） |
| `misc_tools.delete_file` | 仅校验 uploader，未校验空间成员 |
| `im_tools.send_im_message` | 不校验会话归属，可向任意会话发消息 |
| `im_tools.list_im_messages` | 不校验会话归属，可读任意会话消息 |
| `calendar_tools.create_event` | import 了 `get_workspace_member` 却未使用，等于无校验 |
| `misc_tools.approve/reject_approval` | 只按 `instance_id + approver_id` 找 PENDING 节点，不校验实例所属空间与流程规则 |
| `attendance_tools.*` | 无成员校验；且绕过 HTTP 层「非工作时段打卡需提示」的规则 |

结论：HTTP 层的权限在 Agent 工具层被整体绕开，需要统一收口到同一套权限函数。

### 8. 重试机制对非幂等操作不安全

`tool_registry.py` `execute` 对所有工具统一 retry 一次：`create_task` / `send_im_message` / `approve_approval` 属于「写操作已提交但后置步骤抛错」的场景，重试会造成**重复创建、重复发消息、重复审批**。

另外：由于 `execute` 用 `handler(**args, context=context)`，LLM 多传一个参数就会 `TypeError` 触发一次无意义重试。

建议：只对读类工具重试，或为写类工具引入幂等键。

### 9. `complete_task` 多人分支存在死锁漏洞

`task_tools._handler_complete_task`：

- `is_team_wide=True` 但 `TaskAssignee` 为空时，`all_user_ids` 为空 → 条件 `if all_user_ids and completed_count >= len(all_user_ids)` 永不成立 → **任务永远无法置为 completed**。
- 用 `TaskCompletion` 全表 `count()` 与 assignee 数量比较，未校验两者是否同一批人。
- 与项目既定规则「多人任务需全员完成」不一致的边界没有兜底。

### 10. Agent 写路径缺少副作用联动

HTTP 建任务会执行：`publish_task_status_update`（通知被分配人）+ `workspace_activity` + `_invalidate_task_caches`。
Agent 的 `create_task` 三样都没做 → 被分配人收不到通知；任务列表缓存不失效，前端可能「刚创建却看不到」。

### 11. System Prompt 声称的能力与按组注入的工具矛盾

- `config.py` 的 prompt 声明支持 9 大类能力，但实际按意图只注入 3~5 个工具，且**未告知模型本轮可用工具清单**。
- 用户说「看下任务再给张三发消息」→ 只加载 task 组 → 模型调 `send_im_message` → 得到「未知工具」。
- prompt 原则 5「不确定就问」与注入上下文「不要询问用户」冲突，模型行为不稳定（可能反问空间/时间）。

---

## 三、P1：数据与输出准确性

### 12. 截止时间解析表存在错误格式

`tools/task_tools.py` 的格式列表：

```python
for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %M", "%Y-%m-%d"):
```

`%M` 是**分钟**（例如 `2026-10-15 25`），显然是 `%H:%M` 的笔误。
同时解析失败时 `deadline_dt = None` 被静默丢弃，函数仍返回 `success=True` 和「已创建」→ 用户以为设置了截止时间。

### 13. `completed_at` 语义错误

`tools/task_tools.py` 的 `get_task_detail` 用 `task.updated_at` 当作 `completed_at` 返回（模型里没有 `completed_at` 字段）。模型据此回答「完成时间」会给出错误答案。

### 14. 工具成功/失败判定依赖混合约定

`service.py` 判定 `is_success`：先看 `success` 键，再看 `error` 键，最后兜底字符串匹配 `"error"`。但各工具返回风格不统一：

- `create_task` / `complete_task`：`{"success": ...}`
- `list_tasks` / `search_files` / `attendance_stats`：成功无 `success` 键；失败只有 `{"error": ...}`
- `get_file_detail`：失败返回 `{"success": False, ...}`

当前逻辑勉强可用，但任何新工具只要返回体带 `error` 字样（例如内容里出现 "error"）就会误判。建议统一返回契约。

---

## 四、P2：资源、安全与前端体验

### 15. 数据库连接泄漏（明确 bug）

`calendar_tools.py`、`attendance_tools.py` 使用：

```python
db: Session = next(get_db())
```

且**没有 `finally: db.close()`**（这两个模块的每个 handler 都是如此），而 task/im/notification/misc 组用的是 `SessionLocal()` + `finally close`。
每调用一次泄漏一个连接，长期运行会打满连接池。

### 16. async 上下文中执行同步阻塞 DB

- service 主循环与全部 handler 都是同步 SQLAlchemy 调用。
- `service.py` Step 7/8 在 async generator 里新建 `SessionLocal()` 做持久化与审计写入。
- 结果：阻塞事件循环，Gunicorn 多 Worker 下并发能力下降。

### 17. 前端工具结果 XSS

`Index.vue` 的 `formatToolResult` 把 `obj.message` / `obj.error` 直接拼进 `v-html` 且未转义。
`utils/markdown.js` 用了 `html: false` 是安全的，但这段不是 → 工具错误串中回显用户输入（如任务标题）即可注入 HTML。

### 18. 开发者模式开关形同虚设

`Index.vue` 中工具卡片**无条件渲染**，仅「原始参数 JSON」折叠区受 `showToolCalls` 控制 —— 与注释「默认关闭」以及既定偏好「前端不应向用户展示工具调用」相反。
另外历史会话（`agentStore.switchSession`）加载的 `tool_calls` 没有 `meta` 字段，图标 / 动作名 / 危险等级全部丢失。

### 19. 长对话摘要会丢信息

`memory.py` `load_with_summary`：摘要只放进本次返回值，Redis 只保留 `recent_msgs` → 下一轮 `load()` 已经拿不到摘要，每次压缩都在永久丢弃前文，长期上下文语义持续退化。

### 20. 审计与会话字段语义不一致

- 审计表 `session_id` 写入的是 `self.session_id` 原始值（前端随机 key / `ws-x-user-y`），与 MySQL `AgentSession.session_key` 语义不同但字段名相同。
- 工具调用记录只保留 `result[:500]`，无对话上下文，事后定位问题困难。

---

## 五、修复优先级建议

| 优先级 | 条目 | 说明 |
| --- | --- | --- |
| 1 | 第 1、2 条 | 分组空降级为全量 tools + 修正 Level 2 候选集，一两行即可恢复路由 |
| 2 | 第 6、7 条 | 个人空间 0/None 语义统一 + Agent 层权限收口，涉及越权，风险最高 |
| 3 | 第 4、5 条 | 记忆 OpenAI 契约修复 + 会话按 workspace 校验，用户可见的「隔天报错 / 串空间」 |
| 4 | 第 8、15 条 | 写操作重试策略、连接泄漏 |
| 5 | 第 12、13、17、18 条 | prompt 与输出准确性、前端安全与偏好一致性 |
| 6 | 其余 | 按需处理 |

---

## 附：关键代码位置速查

| 问题 | 位置 |
| --- | --- |
| 分组取空死路 | `backend/app/modules/agent/service.py`（Step 2，`if not tools`） |
| 意图候选集错误 | `backend/app/modules/agent/service.py`（`_llm_classify_intent`） |
| 注册异常被吞 | `backend/app/modules/agent/tools/__init__.py`（`_safe_register`） |
| 多模态字段缺失 | `backend/app/modules/agent/schemas.py`（`AgentChatRequest`）、`router.py` |
| 记忆契约破坏 | `backend/app/modules/agent/memory.py`（`_load_from_mysql`、`_seed_redis`） |
| 会话 workspace 校验缺失 | `backend/app/modules/agent/session_service.py`（`get_or_create_session`） |
| 连接泄漏 | `backend/app/modules/agent/tools/calendar_tools.py`、`attendance_tools.py` |
| 写操作盲重试 | `backend/app/modules/agent/tool_registry.py`（`execute`） |
| 多人完成死锁 | `backend/app/modules/agent/tools/task_tools.py`（`_handler_complete_task`） |
| 截止时间格式错误 | `backend/app/modules/agent/tools/task_tools.py`（`_handler_create_task`） |
| 前端 XSS / 工具卡片 | `frontend/src/views/agent/Index.vue`（`formatToolResult`、tool-cards 模板） |
