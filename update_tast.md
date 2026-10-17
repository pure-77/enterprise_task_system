🔴 严重问题（必须修复）

  1. DEBUG 模式下验证码绕过

  backend/app/services/cache_service.py:120-123

  Redis 挂掉 + DEBUG=True 时，验证码固定返回 123456，任何人可用此注册。

  # 删除这几行
  if settings.DEBUG:
      print("DEBUG模式：返回固定验证码 '123456'")
      return "123456"

  2. 验证码明文打印到日志

  backend/app/api/v1/auth.py:37,62,72,74,78 和 cache_service.py:103,113,116

  多处 print() 把验证码明文输出，日志系统可被任何人看到。

  3. 500 错误泄露内部信息

  backend/app/middleware/response_handler.py:84-93

  str(e) 直接返回给客户端，可能暴露数据库连接串、文件路径等。

  4. CORS 配置 * + credentials=True

  backend/app/main.py:40-46

  允许所有来源携带凭证，应限制为实际前端域名。

  5. XSS 漏洞 — v-html 未转义

  frontend/src/views/announcement/Detail.vue:10

  <div v-html="detail.content">  <!-- 攻击者可注入任意 JS -->

  用 DOMPurify 过滤。

  6. IM 事件监听器内存泄漏

  frontend/src/views/im/Index.vue:695-702

  onMounted 注册匿名函数，onUnmounted 用不同引用移除 → 实际移除不生效。每次进出 IM 页面泄漏 2 个监听器。

  ---

  🟠 高优先级（性能/数据完整性）

  7. IM mark_read 的 db.rollback() 毁掉整个事务

  backend/app/modules/im/crud.py:379-386

  循环中 IntegrityError 触发 rollback() 回滚了整个事务，之前成功插入的记录全部丢失。应用 savepoint。

  8. 审批模块 N+1 查询

  backend/app/modules/approval/flow_engine.py:473-513

  _format_instance 懒加载 nodes、cc_list、template、approver 等关联。列表 20 条 → 额外 120+ 次查询。用
  joinedload/selectinload 解决。

  9. IM 消息列表 N+1 查询

  backend/app/modules/im/crud.py:263-304

  get_messages 未 eager load sender，每条消息访问 sender.nickname 触发一次查询。

  10. 权限缓存形同虚设

  backend/app/core/permissions.py:21-34

  缓存命中后仍然查数据库"验证成员存在"，缓存性能收益为零。

  11. 每次任务列表请求都检查过期任务

  backend/app/crud/task.py:133

  check_overdue_tasks(db) 在 get_multi 中调用，每次 GET /tasks 都扫描。应改为定时任务。

  12. Token 刷新后 WebSocket 未重连

  frontend/src/composables/useWebSocket.js

  HTTP 拦截器刷新了 token，但 WS 连接仍用旧 token。

  13. 统计页 Excel 导出配置错误

  frontend/src/views/Statistics/Index.vue:398-399

  responseType: 'blob' 被当作请求 body 发送，而非 axios 配置 → 下载文件损坏。

  14. 任务列表重复 API 请求

  frontend/src/views/Task/List.vue:734-755

  4 个 watcher 都触发 loadTasks()，改一个 filter 可能发 2-3 个相同请求。

  ---

  🟡 中等优先级

  ┌─────┬───────────────────────────────────────┬────────────────────────────────────────────────────────┐
  │  #  │                 文件                  │                          问题                          │
  ├─────┼───────────────────────────────────────┼────────────────────────────────────────────────────────┤
  │ 15  │ websocket.py:238 / useWebSocket.js:24 │ Token 改 URL 参数，日志可见                            │
  ├─────┼───────────────────────────────────────┼────────────────────────────────────────────────────────┤
  │ 16  │ auth.py:73                            │ 验证码比较非恒定时间，可用时序攻击                     │
  ├─────┼───────────────────────────────────────┼────────────────────────────────────────────────────────┤
  │ 17  │ task.py:301, invitation.py:54,76      │ 字符串拼接构造 JSON，用户输入可注入                    │
  ├─────┼───────────────────────────────────────┼────────────────────────────────────────────────────────┤
  │ 18  │ format.js:20-26                       │ formatTime 剥离时区标识，UTC+8 用户时间显示偏差 8 小时 │
  ├─────┼───────────────────────────────────────┼────────────────────────────────────────────────────────┤
  │ 19  │ request.js:99-106,123-131,136-144     │ 401 清理逻辑重复 3 处，应抽函数                        │
  ├─────┼───────────────────────────────────────┼────────────────────────────────────────────────────────┤
  │ 20  │ MainLayout.vue:355                    │ setInterval 未存储 ID，无法清理                        │
  ├─────┼───────────────────────────────────────┼────────────────────────────────────────────────────────┤
  │ 21  │ file/Index.vue:177                    │ goUp() 永远回根目录而非上级目录                        │
  ├─────┼───────────────────────────────────────┼────────────────────────────────────────────────────────┤
  │ 22  │ file/Index.vue:232-236                │ Blob URL 未 revoke，内存泄漏                           │
  ├─────┼───────────────────────────────────────┼────────────────────────────────────────────────────────┤
  │ 23  │ approval/Detail.vue:51                │ canAct() 未校验当前用户是否为审批人                    │
  ├─────┼───────────────────────────────────────┼────────────────────────────────────────────────────────┤
  │ 24  │ Dashboard/Index.vue:399-460           │ 4 个独立请求串行调，应用 Promise.all                   │
  ├─────┼───────────────────────────────────────┼────────────────────────────────────────────────────────┤
  │ 25  │ task_assignee.py                      │ 缺少 (task_id, user_id) 唯一约束，可重复指派           │
  └─────┴───────────────────────────────────────┴────────────────────────────────────────────────────────┘

  ---

  🔵 低优先级

  - redis_client.py — Redis 断线无重连机制
  - cache_service.py:330 和 442 — delete_user_info 定义了两次（死代码）
  - MainLayout.vue:72-78 — 搜索框无任何功能，纯装饰
  - workspaceStore.js:97 — parseInt 未检查 NaN
  - 多个视图文件有 200-400 行注释掉的旧代码（已在 git 历史中）