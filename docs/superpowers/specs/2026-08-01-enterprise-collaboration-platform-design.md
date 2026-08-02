# 企业协作平台 — 重构设计说明书

> **目标定位**：轻量级企业协作平台（钉钉替代方案，覆盖核心 70% 日常协作功能）
> **重构策略**：渐进式改造（保留现有任务系统，扩展新模块）
> **推进方式**：核心依赖递进法，4 个 Phase 分阶段交付
> **日期**：2026-08-01

---

## 一、现状与目标

### 1.1 现有系统资产

| 组件 | 技术 | 状态 |
|------|------|------|
| 后端框架 | FastAPI 0.135 + SQLAlchemy 2.0 | ✅ 可复用 |
| 数据库 | MySQL + Redis | ✅ 可复用 |
| 异步任务 | Celery + Redis | ✅ 可复用 |
| 认证 | JWT 双 Token + bcrypt | ✅ 可复用 |
| 实时通信 | WebSocket + Redis Pub/Sub | ⚠️ 需重构（扩展多通道） |
| 任务管理 | 完整 CRUD + 工作空间 + 权限 | ✅ 保留 |
| 前端框架 | Vue 3 + Element Plus + Pinia | ✅ 可复用 |

### 1.2 目标架构

```
┌─────────────────────────────────────────────────────┐
│                   前端 (Vue 3 SPA)                    │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐     │
│  │  IM  │ │ 审批 │ │ 考勤 │ │ 日程 │ │ 任务 │ ... │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘     │
│  ┌──────────────────────────────────────────┐       │
│  │           统一 API 层 (Axios + WS)        │       │
│  └──────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────┘
                         │
                    HTTP + WS
                         │
┌─────────────────────────────────────────────────────┐
│               后端 (FastAPI 模块化)                   │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐             │
│  │ API 网关  │ │  WebSocket│ │  中间件   │             │
│  │(统一路由) │ │ (多通道)  │ │(日志/CORS)│             │
│  └──────────┘ └──────────┘ └──────────┘             │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐     │
│  │ org  │ │  im  │ │apprv │ │attend│ │ cal  │ ... │
│  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘     │
│  ┌──────────────────────────────────────────┐       │
│  │         共享服务层 (auth/cache/storage)    │       │
│  └──────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────┘
                         │
              MySQL + Redis + 文件存储
```

---

## 二、后端目录结构

```
backend/
├── app/
│   ├── main.py                    # FastAPI 入口（统一挂载各模块路由）
│   ├── core/                      # 核心基础设施（保留+增强）
│   │   ├── config.py              # 全局配置
│   │   ├── security.py            # JWT + 密码
│   │   ├── permissions.py         # 权限检查
│   │   ├── exceptions.py          # 全局异常类
│   │   └── celery_config.py       # Celery 配置
│   ├── db/                        # 数据库（保留）
│   │   ├── base.py                # BaseModel
│   │   ├── session.py             # 会话管理
│   │   └── redis_client.py        # Redis 客户端
│   ├── middleware/                 # 🆕 中间件
│   │   ├── audit_log.py           # 审计日志中间件
│   │   ├── rate_limit.py          # 限流中间件
│   │   └── response_handler.py    # 统一响应格式
│   ├── modules/                   # 🆕 业务模块（每个模块独立目录）
│   │   ├── task/                  # 现有任务模块（重构）
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── crud.py
│   │   │   ├── services.py
│   │   │   └── router.py
│   │   ├── org/                   # 🆕 组织架构
│   │   │   ├── models.py          # Department, Position, OrgMember
│   │   │   ├── schemas.py
│   │   │   ├── crud.py
│   │   │   └── router.py
│   │   ├── im/                    # 🆕 即时通讯
│   │   │   ├── models.py          # Conversation, Member, Message, Read
│   │   │   ├── schemas.py
│   │   │   ├── crud.py
│   │   │   ├── ws_handler.py      # WebSocket 消息处理
│   │   │   └── router.py
│   │   ├── approval/              # 🆕 OA 审批
│   │   │   ├── models.py          # Template, Instance, Node, CC
│   │   │   ├── schemas.py
│   │   │   ├── flow_engine.py     # 审批流引擎
│   │   │   ├── crud.py
│   │   │   └── router.py
│   │   ├── attendance/            # 🆕 考勤
│   │   │   ├── models.py          # Rule, Record, Stats
│   │   │   ├── schemas.py
│   │   │   ├── crud.py
│   │   │   └── router.py
│   │   ├── calendar/              # 🆕 日程
│   │   │   ├── models.py          # Event, Attendee, Reminder
│   │   │   ├── schemas.py
│   │   │   ├── recurrence.py      # RFC 5545 重复规则解析
│   │   │   ├── crud.py
│   │   │   └── router.py
│   │   ├── announcement/          # 🆕 公告
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── crud.py
│   │   │   └── router.py
│   │   ├── file/                  # 🆕 文件管理
│   │   │   ├── models.py
│   │   │   ├── schemas.py
│   │   │   ├── storage.py         # 存储适配器
│   │   │   ├── crud.py
│   │   │   └── router.py
│   │   └── notification/          # 🆕 通知中心
│   │       ├── models.py
│   │       ├── schemas.py
│   │       ├── crud.py
│   │       └── router.py
│   ├── shared/                    # 🆕 共享服务
│   │   ├── auth_service.py        # 认证依赖
│   │   ├── cache_service.py       # Redis 缓存（保留+增强）
│   │   ├── email_service.py       # 邮件服务（保留）
│   │   ├── file_storage.py        # 文件存储抽象
│   │   └── notification_service.py # 统一通知发送
│   └── tasks/                     # Celery 任务（保留+扩展）
│       ├── excel_tasks.py
│       └── notification_tasks.py  # 🆕 通知推送任务
├── migrations/                    # 数据库迁移
├── uploads/                       # 文件存储
├── requirements.txt
├── Dockerfile                     # 🆕
├── docker-compose.yml             # 🆕
└── .env
```

---

## 三、前端目录结构

```
frontend/
├── src/
│   ├── main.js
│   ├── App.vue
│   ├── router/
│   │   ├── index.js
│   │   └── routes/                # 🆕 按模块拆分路由
│   │       ├── auth.js
│   │       ├── task.js
│   │       ├── im.js
│   │       ├── approval.js
│   │       ├── attendance.js
│   │       ├── calendar.js
│   │       ├── announcement.js
│   │       └── org.js
│   ├── stores/                    # 🆕 按模块拆分 Store
│   │   ├── user.js
│   │   ├── task.js
│   │   ├── im.js
│   │   ├── approval.js
│   │   ├── calendar.js
│   │   └── notification.js
│   ├── api/                       # 🆕 按模块拆分 API
│   │   ├── request.js             # Axios 实例（保留）
│   │   ├── auth.js
│   │   ├── task.js
│   │   ├── im.js
│   │   ├── approval.js
│   │   ├── attendance.js
│   │   ├── calendar.js
│   │   ├── announcement.js
│   │   ├── org.js
│   │   └── file.js
│   ├── composables/               # 🆕 通用 composables
│   │   ├── useWebSocket.js        # 多通道 WebSocket
│   │   ├── useNotification.js     # 通知状态
│   │   └── useInfiniteScroll.js   # 无限滚动
│   ├── components/
│   │   ├── base/                  # 基础组件（保留）
│   │   ├── im/                    # 🆕 IM 组件
│   │   │   ├── ChatWindow.vue
│   │   │   ├── MessageBubble.vue
│   │   │   ├── ConversationList.vue
│   │   │   ├── MessageInput.vue
│   │   │   └── EmojiPicker.vue
│   │   ├── approval/              # 🆕 审批组件
│   │   │   ├── ApprovalCard.vue
│   │   │   ├── ApprovalTimeline.vue
│   │   │   └── FormRenderer.vue
│   │   ├── calendar/              # 🆕 日历组件
│   │   │   ├── CalendarView.vue
│   │   │   ├── EventCard.vue
│   │   │   └── EventDialog.vue
│   │   ├── org/                   # 🆕 组织架构组件
│   │   │   ├── DeptTree.vue
│   │   │   └── MemberCard.vue
│   │   ├── file/                  # 🆕 文件组件
│   │   │   ├── FileBrowser.vue
│   │   │   └── FileUploader.vue
│   │   ├── notification/          # 🆕 通知组件
│   │   │   ├── NotificationBell.vue
│   │   │   └── NotificationList.vue
│   │   ├── task/                  # 任务组件（保留）
│   │   └── layout/                # 布局组件
│   │       ├── MainLayout.vue     # 主布局（改造：增加左侧导航）
│   │       ├── Sidebar.vue        # 🆕 统一侧边栏导航
│   │       └── TopBar.vue         # 🆕 顶部栏（搜索+通知+用户）
│   └── views/                     # 页面视图
│       ├── im/                    # 🆕
│       │   ├── Index.vue          # IM 主页（会话列表+聊天窗口）
│       │   └── Chat.vue           # 聊天详情页
│       ├── approval/              # 🆕
│       │   ├── Index.vue          # 审批首页（待办/已办/我发起的）
│       │   ├── Create.vue         # 发起审批
│       │   └── Detail.vue         # 审批详情
│       ├── attendance/            # 🆕
│       │   ├── Index.vue          # 打卡主页
│       │   ├── Records.vue        # 打卡记录
│       │   └── Stats.vue          # 考勤统计
│       ├── calendar/              # 🆕
│       │   └── Index.vue          # 日历主页
│       ├── announcement/          # 🆕
│       │   ├── Index.vue          # 公告列表
│       │   └── Detail.vue         # 公告详情
│       ├── org/                   # 🆕
│       │   ├── Dept.vue           # 部门管理
│       │   └── Members.vue        # 成员花名册
│       ├── file/                  # 🆕
│       │   └── Index.vue          # 文件管理
│       ├── task/                  # 保留+改造
│       ├── auth/                  # 保留
│       └── workspace/             # 保留+改造
├── vite.config.js
└── package.json
```

---

## 四、关键技术方案

### 4.1 IM 实时消息架构

```
┌──────────┐  ws://.../ws/im?token=xxx   ┌──────────────┐
│  Client A │◄──────────────────────────►│              │
└──────────┘                             │  WebSocket   │
       │                                  │  Connection  │
       │ send_message(to=B, text="hello") │  Manager     │
       ▼                                  │              │
┌──────────────┐                          │  ┌─────────┐ │
│ HTTP POST    │────►  REST API ──────►   │  │ Redis   │ │
│ /im/messages │      /api/v1/im/messages │  │ Pub/Sub │ │
└──────────────┘                          │  └────┬────┘ │
                                          │       │      │
                                          └───────┼──────┘
                                                  │
                                    channel:im:conversation:{id}
                                                  │
                                          ┌───────┼──────┐
                                          │       ▼      │
┌──────────┐  ws://.../ws/im?token=xxx   │  push to B   │
│  Client B │◄───────────────────────────│  if online   │
└──────────┘                             └──────────────┘
```

**关键设计决策**：
- 消息发送走 **HTTP REST**（可靠持久化），推送走 **WebSocket**（实时通知）
- 每个会话一个 Redis Pub/Sub 频道 `im:conversation:{id}`
- WebSocket 连接管理器按 user_id 维护连接池（支持多端登录）
- 离线消息：用户重连后通过 REST API 拉取未读消息

### 4.2 审批流引擎

```python
# 审批流程节点设计（存储在 approval_templates.flow_schema JSON 中）
{
    "nodes": [
        {
            "sort": 1,
            "name": "直属上级审批",
            "type": "supervisor",      # supervisor | specific | role | condition
            "approver_ids": null,       # type=specific 时指定具体人
            "condition": null           # type=condition 时的条件表达式
        },
        {
            "sort": 2,
            "name": "部门经理审批",
            "type": "role",
            "role": "department_manager"
        },
        {
            "sort": 3,
            "name": "财务审批",
            "type": "specific",
            "approver_ids": [5, 12]
        }
    ]
}
```

**审批状态机**：
```
                   ┌─────────┐
          ┌───────►│ pending │
          │        └────┬────┘
          │             │ submit
          │        ┌────▼────┐
          │   ┌───►│ pending │──┐ (多节点流转)
          │   │    └────┬────┘  │
          │   │         │       │
          │   │    ┌────▼───┐   │
          │   │    │approved│   │ (当前节点通过)
          │   │    └────┬───┘   │
          │   │         │       │
          │   │    ┌────▼───┐   │
          │   │    │rejected│   │ (任一节点拒绝)
          │   │    └────────┘   │
          │   │                 │
          │   │    ┌────────┐   │
          │   └────┤recalled│◄──┘ (申请人撤回)
          │        └────────┘
          │
          └── transferred (转交)
```

### 4.3 统一响应格式

所有 API 统一返回：

```json
{
    "code": 0,
    "message": "success",
    "data": { ... }
}
```

错误响应：
```json
{
    "code": 40101,
    "message": "未授权访问",
    "detail": "Token 已过期，请重新登录"
}
```

错误码规范：`{模块码}{错误序号}`，如 `40101` = 认证模块 + Token 过期。

### 4.4 WebSocket 多通道设计

单一 WebSocket 连接，通过消息 `type` 字段区分业务：

```json
// 客户端 → 服务端
{
    "action": "subscribe",
    "channels": ["im", "notification"]
}

// 服务端 → 客户端
{
    "channel": "im",
    "type": "new_message",
    "data": { ... }
}
{
    "channel": "notification",
    "type": "approval_notify",
    "data": { ... }
}
```

### 4.5 文件存储抽象层

```python
class StorageBackend(ABC):
    @abstractmethod
    def upload(self, file: UploadFile, path: str) -> str: ...
    @abstractmethod
    def download(self, path: str) -> bytes: ...
    @abstractmethod
    def delete(self, path: str) -> bool: ...
    @abstractmethod
    def get_url(self, path: str, expires: int = 3600) -> str: ...

class LocalStorage(StorageBackend): ...   # Phase 1 默认
class OSSStorage(StorageBackend): ...     # 未来扩展
```

---

## 五、数据库设计

> 完整的表结构设计（23 张新表 + 2 张修改表 + 11 张保留表）已在本说明书之前产出并与你确认。本章仅描述迁移策略和索引规划，完整字段定义见前述表结构设计。

### 5.0 模块与表对照

| 模块 | 新表 | 保留/修改 |
|------|------|-----------|
| org | departments, positions | workspace_members(改), users(改) |
| im | conversations, conversation_members, messages, message_reads | — |
| approval | approval_templates, approval_instances, approval_nodes, approval_cc | — |
| attendance | attendance_rules, attendance_records, attendance_stats | — |
| calendar | events, event_attendees, event_reminders | — |
| announcement | announcements, announcement_reads | — |
| notification | notifications, notification_settings | — |
| file | file_folders, files | — |
| log | audit_logs | workspace_activities(废弃) |
| task | — | 11 张现有表全部保留 |

## 六、数据库迁移策略

### 5.1 新增表（23 张）

全部使用 SQLAlchemy ORM 定义，通过 `init_db()` 自动创建（开发阶段），生产环境使用 Alembic 迁移脚本。

### 5.2 修改表（2 张）

| 表 | 修改内容 | 方式 |
|----|----------|------|
| users | 加 real_name, mobile, avatar_thumb, last_login_at, last_login_ip | ALTER TABLE ADD COLUMN |
| workspace_members | 加 department_id, position_id, employee_no, real_name, mobile, join_date, status | ALTER TABLE ADD COLUMN |

### 5.3 废弃表

- `workspace_activities` → 由全局 `audit_logs` 替代，保留旧数据只读，新数据写入 audit_logs

### 5.4 索引策略

| 表 | 索引 | 用途 |
|----|------|------|
| messages | (conversation_id, created_at) | 消息分页查询 |
| messages | (sender_id, created_at) | 用户消息查询 |
| notifications | (user_id, is_read, created_at) | 未读通知查询 |
| audit_logs | (workspace_id, module, created_at) | 日志筛选 |
| events | (workspace_id, start_time, end_time) | 日程范围查询 |
| approval_instances | (applicant_id, status) | 我发起的审批 |
| attendance_records | (user_id, date) | 打卡记录查询 |

---

## 七、分阶段实施计划

### Phase 1：基础设施 + 组织架构（20-25 人天）

**目标**：建立模块化架构骨架，组织架构是所有模块的前置依赖

| 任务 | 人天 | 产出 |
|------|------|------|
| 目录结构重构 | 2 | 新的模块化目录 |
| 统一响应格式 + 错误处理 | 1 | 全局中间件 |
| 现有代码迁移到 modules/task/ | 3 | 任务模块独立 |
| 全局审计日志中间件 | 2 | audit_logs 表 + 中间件 |
| Department CRUD + 树查询 | 3 | 部门管理完整 API |
| Position CRUD | 1 | 职位管理 API |
| workspace_members 扩展 | 2 | 成员管理（部门/职位/工号） |
| users 表扩展 | 1 | 加 real_name/mobile 等字段 |
| 前端：组织架构页面 | 4 | 部门树 + 花名册 |
| 前端：MainLayout 改造 | 2 | 新侧边栏 + TopBar |
| Docker + docker-compose | 2 | 容器化部署 |
| 联调 + Bug 修复 | 2 | — |

**交付物**：新的模块化架构 + 部门/职位管理 + 成员花名册 + Docker 部署

---

### Phase 2：即时通讯 + 通知中心（25-35 人天）

**目标**：核心沟通能力，最高频使用的模块

| 任务 | 人天 | 产出 |
|------|------|------|
| Conversation + Message 模型 | 2 | 会话和消息表 + CRUD |
| 消息 REST API | 3 | 发送/分页拉取/撤回 |
| WebSocket 多通道重构 | 4 | WS 连接管理 + IM 通道 |
| 消息已读追踪 | 2 | 批量已读标记 |
| 群管理 API | 2 | 创建群/加人/踢人/禁言 |
| 通知中心模型 + API | 3 | 通知创建/列表/已读 |
| 通知偏好设置 | 1 | 用户级通知开关 |
| 前端：IM 聊天窗口 | 6 | 会话列表 + 消息气泡 + 输入框 |
| 前端：WebSocket 对接 | 2 | 实时消息接收 |
| 前端：通知铃铛 + 列表 | 2 | 顶部通知组件 |
| 前端：通知设置页 | 1 | 偏好配置 |
| 联调 + Bug 修复 | 3 | — |

**交付物**：可用的单聊/群聊 + 消息已读 + 通知中心

---

### Phase 3：OA 审批 + 日程日历（30-42 人天）

**目标**：企业核心工作流工具

| 任务 | 人天 | 产出 |
|------|------|------|
| 审批模板模型 + CRUD | 3 | 模板管理（含内置模板） |
| 审批流引擎 | 5 | 多节点顺序流 + 驳回/转交 |
| 审批实例 API | 4 | 提交/审批/撤回/详情 |
| 抄送机制 | 1 | 抄送人 + 已读 |
| 事件模型 + CRUD | 3 | 日程事件管理 |
| RFC 5545 重复规则 | 3 | 重复事件解析+生成 |
| 参与人 + 提醒 | 2 | 会议邀约 + 定时提醒 |
| 前端：审批模板配置页 | 2 | 管理员配置 |
| 前端：发起审批 + 动态表单 | 3 | FormRenderer 组件 |
| 前端：审批详情 + 时间线 | 3 | ApprovalTimeline 组件 |
| 前端：日历视图（月/周/日） | 5 | CalendarView 组件 |
| 前端：事件创建/编辑 | 2 | EventDialog |
| 联调 + Bug 修复 | 4 | — |

**交付物**：请假/报销/出差审批流程 + 个人/团队日历

---

### Phase 4：考勤 + 公告 + 文件管理 + 日志（25-38 人天）

**目标**：补充剩余的协作工具，完善平台

| 任务 | 人天 | 产出 |
|------|------|------|
| 考勤规则 + 记录 API | 4 | 规则管理 + 打卡接口 |
| 考勤统计 + 判定 | 3 | 迟到/早退自动判定 + 汇总 |
| 公告 CRUD + 已读追踪 | 2 | 公告管理 API |
| 文件模块（文件夹+文件） | 3 | 文件 CRUD + 文件夹树 |
| 文件存储适配器 | 2 | LocalStorage + 预留 OSS |
| 前端：打卡页面（移动端适配） | 4 | 打卡 UI |
| 前端：考勤统计仪表盘 | 2 | 统计图表 |
| 前端：公告列表 + 详情 | 2 | 富文本渲染 |
| 前端：文件浏览器 + 上传 | 4 | FileBrowser + FileUploader |
| 前端：审计日志查看器 | 2 | 多条件筛选日志 |
| CI/CD 配置 | 3 | GitHub Actions 测试+部署 |
| 联调 + Bug 修复 | 3 | — |

**交付物**：完整的企业协作平台 v1.0

---

## 八、总工期

| Phase | 内容 | 最小 | 最大 |
|-------|------|------|------|
| Phase 1 | 基础设施 + 组织架构 | 20 天 | 25 天 |
| Phase 2 | IM + 通知 | 25 天 | 35 天 |
| Phase 3 | 审批 + 日程 | 30 天 | 42 天 |
| Phase 4 | 考勤 + 公告 + 文件 + 日志 | 25 天 | 38 天 |
| **累计** | | **100 天** | **140 天** |

| 人力资源 | 预计周期 |
|----------|----------|
| 1 人全职 | **4.5 - 6.5 个月** |
| 2 人全职 | **3 - 4 个月** |

---

## 九、里程碑交付物

| 里程碑 | 时间（单人） | 可交付物 |
|--------|-------------|----------|
| M1 | 第 5 周末 | 模块化架构 + 组织架构 + Docker 部署 |
| M2 | 第 12 周末 | IM 聊天 + 通知中心可用 |
| M3 | 第 20 周末 | OA 审批 + 日历可用 |
| M4 | 第 27 周末 | 完整平台 v1.0 |

---

## 十、风险与对策

| 风险 | 概率 | 影响 | 对策 |
|------|------|------|------|
| IM WebSocket 连接管理复杂度过高 | 中 | Phase 2 延期 | 使用成熟的 WS 库，编写连接压力测试 |
| 审批流引擎设计不灵活 | 中 | Phase 3 返工 | Phase 1 完成时先做审批流引擎的 POC 验证 |
| RFC 5545 重复规则解析困难 | 高 | 日历功能简化 | 只支持简单的 daily/weekly/monthly/yearly 重复，复杂规则按需扩展 |
| 大文件上传导致服务器压力 | 低 | Phase 4 性能问题 | Phase 4 先做小文件（<50MB），大文件分片后续迭代 |
| 前端体积膨胀，首屏加载慢 | 中 | 用户体验差 | 路由懒加载 + 组件按需引入 Element Plus |

---

## 十一、技术规范

### 10.1 代码规范

- Python：PEP 8，类型注解（Type Hints）
- Vue：Composition API + `<script setup>`，ESLint
- 每个模块的 models/schemas/crud/router 强制分离
- 所有 API 接口使用 Pydantic Schema 做请求/响应验证

### 10.2 数据库规范

- 所有表使用 InnoDB + utf8mb4
- 所有查询使用 SQLAlchemy ORM（禁止拼接 SQL）
- 大数据量查询必须分页（默认 page_size=20，最大 100）
- 软删除统一使用 `is_active` 字段

### 10.3 API 规范

- RESTful 风格，资源名用复数
- 分页参数统一：`page`（1-based）、`page_size`（默认 20）
- 排序参数：`sort_by` + `sort_order`（asc/desc）
- 认证统一使用 `Authorization: Bearer {token}` Header

### 10.4 测试策略

| 层级 | 工具 | 覆盖率要求 |
|------|------|-----------|
| 单元测试 | pytest | 核心逻辑 >70% |
| API 测试 | httpx + pytest | 每个端点 ≥1 个用例 |
| WebSocket 测试 | pytest-asyncio | 连接+消息收发 |
| 前端组件测试 | vitest | 关键组件覆盖 |

---

## 十二、验收标准

Phase 1 验收：
- [ ] 所有现有功能正常运行（任务 CRUD、工作空间、认证）
- [ ] 部门树可正确展示无限层级，懒加载
- [ ] 成员可分配到部门和职位
- [ ] `docker-compose up` 一键启动完整服务

Phase 2 验收：
- [ ] 单聊消息发送 + 实时接收延迟 <500ms
- [ ] 群聊创建/管理功能正常
- [ ] 消息已读状态正确同步
- [ ] WebSocket 断线后 5 秒内自动重连
- [ ] 通知铃铛实时显示未读数

Phase 3 验收：
- [ ] 审批模板可创建、编辑、禁用
- [ ] 审批流按节点正确流转，驳回/转交正常
- [ ] 日历月/周/日视图正确渲染
- [ ] 重复事件（daily/weekly/monthly/yearly）正确展开

Phase 4 验收：
- [ ] GPS/WiFi 打卡在误差范围内工作
- [ ] 迟到/早退/缺勤正确判定
- [ ] 文件上传/下载/删除功能正常
- [ ] 审计日志记录所有模块的操作
- [ ] CI/CD 流水线通过
