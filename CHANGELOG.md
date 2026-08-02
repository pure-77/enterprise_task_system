# Celery 备份任务修复 — 更新日志 (2026-05-11)

## 核心问题

Celery 异步备份任务（Excel 导出/JSON 导入）存在多个 bug，导致功能完全不可用：

1. Excel 异步导出在 Celery worker 中生成了文件但从未保存到磁盘，用户无法下载
2. 前端 Excel 导出期望 blob 响应，但后端返回 JSON `{task_id, message}`，导致下载的文件为损坏的 JSON 文本
3. 前端导入成功回调访问 `response.imported_tasks`，但后端返回的是 `{task_id, message}`
4. WebSocket Redis 订阅者在守护线程内调用 `asyncio.create_task()`，因无线程事件循环而静默失败
5. 无 Celery worker 部署配置，生产环境任务不会被执行
6. Redis 客户端在模块加载时创建连接，Celery worker fork 时可能导致连接损坏
7. `app/models/__init__.py` 缺少 `task_assignees` 和 `TaskCompletion` 导入，Celery worker 中 SQLAlchemy mapper 初始化失败
8. `.env` 文件使用 `;` 作为注释符，Python-dotenv 无法解析，每次启动有警告

---

## 后端修复

### 1. `app/tasks/excel_tasks.py` — Excel 导出任务保存到磁盘

**改动：** 任务生成的 Excel 文件现在写入 `backend/temp_exports/` 目录，返回路径和文件名。

```python
# 返回格式变更
{"status": "success", "file_path": "...", "file_name": "...", "file_size": N}
```

同时将 `next(get_db())` 替换为 `get_db_session()`（非生成器工厂函数）。

### 2. `app/api/v1/backup.py` — 新增下载端点

**新增：** `GET /api/v1/backup/download/{task_id}` — 下载 Celery 异步生成的 Excel 文件，下载后自动清理临时文件。

**改进：** `GET /api/v1/backup/task/{task_id}` 状态查询现在返回 `download_url` 字段（当文件就绪时）。

### 3. `app/api/v1/websocket.py` — 线程安全修复

**改动：** `redis_subscriber()` 守护线程中的 `asyncio.create_task()` 替换为 `asyncio.run_coroutine_threadsafe(mgr.send_personal_message(...), loop)`。

**新增：** `stop_redis_subscriber()` 函数，通过 `threading.Event` 信号优雅关闭 pubsub。

### 4. `app/main.py` — 新增 shutdown 事件

**新增：** `@app.on_event("shutdown")` 处理函数，调用 `stop_redis_subscriber()` 清理资源。

### 5. `app/core/celery_config.py` — 移除冗余注册

移除了 `celery_app.autodiscover_tasks()` 调用。任务已通过构造函数的 `include` 参数显式注册。

### 6. `app/db/redis_client.py` — 懒加载初始化

模块级 `redis_client = redis.from_url(...)` 替换为懒加载的 `get_redis()` 函数。防止 Celery prefork worker pool 中的连接损坏。

### 7. `app/db/session.py` — 新增 Session 工厂

新增 `get_db_session()` 函数，为非请求上下文（Celery 任务等）提供直接的 Session 对象，替代易出错的 `next(get_db())` 模式。

### 8. `supervisor.conf` — 新增 Celery Worker 配置

新增 `[program:celery_worker]` 段，配置 Celery worker 自动启动和重启。

### 9. `app/models/__init__.py` — 补充缺失的模型导入

`task_assignees` 和 `TaskCompletion` 表未在 `__init__.py` 中导入，导致 Celery worker 进程中 SQLAlchemy mapper 初始化失败：
```
InvalidRequestError: 'task_assignees' failed to locate a name
```
Web 服务器通过 `init_db()` 手动导入了这些模型，但 Celery worker 不走这个路径。现在统一在 `__init__.py` 中导入。

### 10. `app/core/celery_config.py` — 添加 `broker_connection_retry_on_startup`

消除 Celery 6.0 弃用警告。

### 11. `backend/.env` — 修复注释格式

`;` 改为 `#`（Python-dotenv 只识别 `#` 注释）。

### 12. 相关文件适配 `get_redis()`

- `app/api/v1/task.py` — `publish_task_status_update()` 改用 `get_redis()`
- `app/services/cache_service.py` — 全部 Redis 操作改用 `get_redis()`
- `test_modules.py` — 测试代码同步更新

---

## 前端修复

### 13. `src/api/backup.js` — API 层重构

- `exportExcel()` — 移除 `responseType: 'blob'`，现在返回 JSON `{task_id, message}`
- **新增** `getTaskStatus(taskId)` — 轮询 Celery 任务状态
- **新增** `downloadFile(taskId)` — 下载生成的 Excel 文件（blob 响应）

### 14. `src/views/User/Backup.vue` — 重写备份页面

- 移除了 201 行已注释的旧版代码
- Excel 导出改为异步流程：提交任务 → 轮询状态 → 下载文件，附实时状态提示
- JSON 导入改为异步流程：提交文件 → 轮询状态 → 显示导入数量
- 分离 Excel 导出和 JSON 导出的 loading 状态

---

## 使用方式

### 开发环境

```bash
# 终端 1：启动 FastAPI
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# 终端 2：启动 Celery Worker
cd backend
celery -A app.core.celery_config worker --loglevel=info --pool=solo
```

Windows 需使用 `--pool=solo`，Linux/macOS 可用默认的 prefork pool。

### 生产环境

```bash
supervisorctl reread
supervisorctl update
supervisorctl start celery_worker
```
