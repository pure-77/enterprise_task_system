# 项目优化方案

> 生成时间：2026-08-14
> 范围：功能优化 + 性能优化 + 架构建议
> 状态：评估建议，尚未实施（除静态文件认证中间件外）

---

## Top 3 最高优先级

| # | 类别 | 问题 | 影响 |
|---|------|------|------|
| 1 | 安全 (P0) | CORS `allow_origins=["*"]` + `allow_credentials=True` | 浏览器安全策略冲突，且任何人可跨域调用 API |
| 2 | 安全 (P0) | `/uploads` 静态文件无认证保护 | 任何人猜到 URL 即可直接下载所有文件（含用户头像、IM 图片、文档） |
| 3 | 架构 (P0) | `init_db()` 每次启动都执行 `ALTER TABLE` / `CREATE TABLE` | 生产环境多实例部署时会并发改表导致崩溃；无版本化迁移管理 |

> **注**：#2 静态文件认证中间件已实施，详见下方"已实施"部分。

---

## 一、功能性优化建议

### P0 — 必须修复

#### F1. CORS 配置过宽

- **文件**：`backend/app/main.py` 第 37-43 行
- **问题**：`allow_origins=["*"]` 与 `allow_credentials=True` 同时设置，浏览器实际上会拒绝这种组合
- **影响**：所有 API 接口
- **建议方向**：改为白名单配置：`allow_origins=["http://localhost:3000"]` 并通过环境变量管理

#### F2. 静态文件无认证（已实施 ✅）

- **文件**：`backend/app/main.py` 第 72 行
- **问题**：`/uploads` 路径挂载了 `StaticFiles`，任何猜到 URL 的人都可以直接访问
- **影响**：头像、IM 图片、文件
- **已实施**：新增 `backend/app/middleware/static_auth.py` 中间件，验证 JWT token 后才允许访问静态资源；前端新增 `appendToken()` 工具函数为 `<img>` / `<el-avatar>` 等标签自动追加 `?token=xxx`

#### F3. WebSocket Token 通过 URL Query 传递

- **文件**：`backend/app/api/v1/websocket.py` 第 191 行
- **问题**：`ws://...?token=xxx` 会被 Nginx/服务日志记录
- **影响**：IM、通知、任务状态推送
- **建议方向**：改为握手时的 Authorization header 或通过第一次消息发送 token

#### F4. 路由 meta 不一致

- **文件**：`frontend/src/router/routes.js` 第 9 行 vs `frontend/src/layouts/MainLayout.vue` 第 205 行
- **问题**：`routes.js` 根路径标记 `requiresWorkspace: true`，但 `MainLayout.vue` 中已改为 `false`
- **影响**：首页跳转
- **建议方向**：统一路由 meta，以 `routes.js` 为准

---

### P1 — 建议优化

#### F5. 审计日志同步写

- **文件**：`backend/app/middleware/audit_log.py`
- **问题**：每个写请求都创建新的 DB session 同步写日志
- **影响**：所有写操作
- **建议方向**：改为异步队列（如 Redis List + Celery），或使用 `background_tasks`

#### F6. 缓存命中仍查库验证

- **文件**：`backend/app/core/permissions.py` 第 21-34 行
- **问题**：缓存命中后仍 `query.filter().first()` 查库验证
- **影响**：每次权限校验请求
- **建议方向**：缓存数据应足够可信，命中时直接返回，仅在缓存未命中时查库

#### F7. IM 消息撤回无存储清理

- **文件**：`backend/app/modules/im/crud.py`
- **问题**：撤回后 `is_recalled=True` 但文件仍保留
- **影响**：IM 文件存储
- **建议方向**：撤回时如为文件/图片，应异步清理存储

#### F8. 文件管理缺少回收站

- **文件**：`backend/app/modules/file/crud.py`
- **问题**：删除后直接物理删除
- **影响**：文件管理
- **建议方向**：添加软删除 + 定期清理任务（Celery beat）

#### F9. 审批流引擎缺少并发控制

- **文件**：`backend/app/modules/approval/flow_engine.py`
- **问题**：使用 `with_for_update()` 但其他查询未加锁
- **影响**：审批审批
- **建议方向**：所有涉及状态变更的查询都应使用行锁

#### F10. 个人模式下功能直接报错

- **文件**：`backend/app/modules/*/router.py`
- **问题**：IM、文件、审批等功能在个人模式下应友好提示而非 500 错误
- **影响**：IM、文件、审批等
- **建议方向**：统一 `requiresWorkspace` 的前置检查，返回 400 + 友好提示

---

### P2 — 体验增强

| # | 问题 | 建议方向 |
|---|------|----------|
| F11 | 前端全局 loading 状态缺失，列表页加载无骨架屏 | 添加全局 `Loading` 组件或骨架屏 |
| F12 | IM 缺少已读回执，用户不知道消息是否被阅读 | 添加 `read_at` 状态和"已读/未读"提示 |
| F13 | 文件管理缺少搜索，只能翻页浏览 | 添加文件名搜索 + 按类型/时间过滤 |
| F14 | 日程日历缺少提醒推送 | 对接通知系统，在到期前推送提醒 |
| F15 | 数据统计缺少导出功能 | 支持 Excel/PDF 导出 |
| F16 | 缺少暗黑模式下的富文本编辑器样式适配 | 富文本编辑器的样式在暗模式下可能不协调 |

---

## 二、性能优化建议

### P0 — 影响大

#### P1. 启动时同步改表

- **文件**：`backend/app/db/session.py` 第 56-214 行
- **问题**：`init_db()` 每次启动执行 10+ 条 `ALTER TABLE`
- **影响**：多实例并发启动时可能导致死锁/崩溃；启动慢
- **建议方向**：引入 Alembic 做版本化迁移，`init_db` 只做 `create_all`

#### P2. SQLAlchemy N+1 查询

- **文件**：`backend/app/crud/task.py` 第 56-62 行
- **问题**：任务详情加载虽用了 `joinedload`，但 IM 会话列表加载成员时逐个查询
- **影响**：列表页每条任务/会话额外 2-3 次查询
- **建议方向**：统一使用 `joinedload`/`selectinload` 预加载关联

#### P3. IM 消息列表无分页限制

- **文件**：`backend/app/modules/im/crud.py`
- **问题**：`page_size` 上限 100，但历史消息可能上千条
- **影响**：首次进入会话时加载 100 条；滚动加载时可能慢
- **建议方向**：添加上游加载（上翻加载历史）+ 消息分页缓存

#### P4. 前端构建 1MB+ 超大 chunk

- **文件**：`frontend/vite.config.js`
- **问题**：无 `manualChunks` 配置
- **影响**：首屏加载 1MB+ JS，白屏时间长
- **建议方向**：配置 `manualChunks` 拆分：element-plus / vue-core / business

---

### P1 — 显著提升

| # | 问题 | 位置 | 建议方向 |
|---|------|------|----------|
| P5 | 缓存服务用 `print()` 而非 logger | `backend/app/services/cache_service.py` | 统一使用 `logging.getLogger()`，便于日志管理 |
| P6 | 数据库连接池未调优 | `backend/app/db/session.py` | 生产环境建议 `pool_size=20, max_overflow=10` |
| P7 | Redis 客户端无连接池 | `backend/app/db/redis_client.py` | 使用 `redis.ConnectionPool` 管理连接复用 |
| P8 | 文件上传全量读入内存 | `backend/app/modules/file/router.py` | 大文件（>50MB）会占满内存，流式写入磁盘 |
| P9 | 审计日志阻塞主流程 | `backend/app/middleware/audit_log.py` | 改为 `asyncio.create_task()` 或 `background_tasks.add_task()` |
| P10 | IM Redis 订阅用线程 | `backend/app/api/v1/websocket.py` 第 141-186 行 | 改用 async Redis 客户端（`aioredis`）的 pub/sub |
| P11 | IM 消息序列化在 API 层 | `backend/app/modules/im/router.py` | 每条消息都要手动组装 dict，使用 Pydantic schema 统一序列化 |
| P12 | Dashboard 统计接口串行查询 | `backend/app/modules/task/router.py` | 使用 `asyncio.gather()` 并行查询 |

---

### P2 — 精细优化

| # | 问题 | 建议方向 |
|---|------|----------|
| P13 | Security 密码哈希双重哈希（`SHA-256 + bcrypt`） | 去掉 SHA-256 预处理，直接用 bcrypt |
| P14 | 数据库查询未用 `yield_per` | 列表分页场景使用 `yield_per()` 减少内存占用 |
| P15 | 前端无请求取消 | 组件卸载时使用 `AbortController` 或 axios cancel token |
| P16 | Pinia store 直接读 localStorage | 封装为响应式方法，便于测试 |
| P17 | Docker Compose 无健康检查 | 添加 `healthcheck` 配置确保 MySQL/Redis 就绪后再启动后端 |
| P18 | gunicorn 配置缺少 worker 调优 | 设置 `workers=2*CPU+1`, `worker_class=uvicorn.workers.UvicornWorker` |

---

## 三、架构层面建议

| 维度 | 建议 |
|------|------|
| **测试覆盖** | 目前仅有零散 `test_integration_phase1~4.py` 和 `test_modules.py`，建议引入 pytest + pytest-cov，建立单元测试覆盖率 ≥ 70% |
| **CI/CD** | 缺少 `.github/workflows/` 或 `.gitlab-ci.yml`，建议建立自动化测试 + 构建 + 部署流水线 |
| **监控告警** | 缺少 APM 集成，建议至少接入 Sentry（错误监控）+ Prometheus/Grafana（指标监控） |
| **日志规范** | 日志格式不统一（混用 `print`/`logging`），建议引入 `structlog` 或统一 JSON 日志格式 |
| **API 文档** | 已有 `/docs`（Swagger），但缺少 OpenAPI Spec 的版本化管理 |
| **模块边界** | `modules/` 下的新模块（im/approval/calendar 等）和顶层 `api/v1`、`crud/`、`models/` 存在结构割裂，建议统一到 `modules/` 下 |

---

## 已实施项

### 静态文件认证中间件（2026-08-14）

**新增文件**：
- `backend/app/middleware/static_auth.py` — 拦截 `/uploads` 请求，验证 JWT token

**修改文件**：
- `backend/app/main.py` — 注册 `StaticAuthMiddleware`
- `frontend/src/utils/auth.js` — 新增 `appendToken(url)` 工具函数
- `frontend/src/layouts/MainLayout.vue` — 用户头像追加 token
- `frontend/src/views/im/Index.vue` — 会话头像、消息图片、文件 URL 追加 token
- `frontend/src/views/org/DeptManage.vue` — 部门成员头像追加 token
- `frontend/src/views/User/Profile.vue` — 个人资料头像追加 token

**认证流程**：
```
浏览器 <img src="/uploads/avatars/xxx.jpg?token=eyJhbG...">
  → StaticAuthMiddleware 拦截
  → 从 query param 提取 token
  → decode_token() 验证
  → 通过 → StaticFiles 返回文件
  → 失败 → 401 JSON
```
