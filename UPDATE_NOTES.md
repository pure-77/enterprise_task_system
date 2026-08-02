# 团队协作功能更新文档

## 概述

将原有**个人任务管理系统**升级为**个人 + 多工作空间协作**系统。

### 核心能力

- **多工作空间**：用户可创建/加入多个工作空间（类似 Notion 多工作区）
- **三级角色**：Owner → Admin → Member，精细化权限控制
- **全部共享**：空间内任务、分类、标签全员可见，个人数据完全隔离
- **任务指派**：可将空间任务指派给特定成员
- **邀请机制**：通过邮箱邀请用户加入空间
- **活动日志**：空间内所有操作留痕
- **实时推送**：WebSocket 支持空间事件和任务状态实时通知

### 数据隔离

原有个人数据（`workspace_id = NULL`）完全保留，不受任何影响。空间数据通过 `workspace_id` 隔离。

---

## 一、数据库变更

### 新增表

| 表名 | 说明 |
|------|------|
| `workspaces` | 工作空间（name, description, owner_id） |
| `workspace_members` | 成员关系（workspace_id, user_id, role） |
| `workspace_invitations` | 邀请记录（workspace_id, inviter_id, invitee_email, role, status） |
| `workspace_activities` | 活动日志（workspace_id, user_id, action, target_type, target_id, detail） |

### 修改表

| 表名 | 新增列 |
|------|--------|
| `tasks` | `workspace_id`（可为NULL）, `assignee_id`（可为NULL） |
| `categories` | `workspace_id`（可为NULL） |
| `tags` | `workspace_id`（可为NULL） |

### 角色枚举

- `owner` — 创建者，拥有全部权限
- `admin` — 管理员，管理成员、编辑/删除任何任务
- `member` — 普通成员，仅编辑自己创建的任务

### 执行迁移

```bash
cd backend
python migrate_workspace.py
```

---

## 二、后端 API 新增

### 工作空间（`/api/v1/workspaces`）

| 方法 | URL | 说明 | 权限 |
|------|-----|------|------|
| POST | `/workspaces` | 创建工作空间 | 登录用户 |
| GET | `/workspaces` | 我的空间列表 | 登录用户 |
| GET | `/workspaces/{id}` | 空间详情 | 空间成员 |
| PUT | `/workspaces/{id}` | 更新空间信息 | Owner/Admin |
| DELETE | `/workspaces/{id}` | 解散空间 | Owner |

### 成员管理（`/api/v1/workspaces/{id}/members`）

| 方法 | URL | 说明 |
|------|-----|------|
| GET | `/members` | 成员列表 |
| PUT | `/members/{user_id}/role` | 修改角色 |
| DELETE | `/members/{user_id}` | 移除成员 |
| POST | `/members/leave` | 退出空间 |

### 邀请（`/api/v1/workspaces/{id}/invitations` + `/api/v1/invitations`）

| 方法 | URL | 说明 |
|------|-----|------|
| POST | `/workspaces/{id}/invitations` | 发起邀请 |
| GET | `/workspaces/{id}/invitations` | 空间邀请列表 |
| DELETE | `/workspaces/{id}/invitations/{inv_id}` | 取消邀请 |
| GET | `/invitations` | 我收到的邀请 |
| GET | `/invitations/pending-count` | 待处理邀请数 |
| POST | `/invitations/{id}/accept` | 接受邀请 |
| POST | `/invitations/{id}/reject` | 拒绝邀请 |

### 活动日志（`/api/v1/workspaces/{id}/activities`）

| 方法 | URL | 说明 |
|------|-----|------|
| GET | `/activities` | 最近活动列表 |

### 现有端点变更

tasks/categories/tags 的 GET 请求新增可选 `workspace_id` 参数：
- 传入 `workspace_id` → 查询空间数据
- 不传 → 查询个人数据（向后兼容）

statistics 端点同样支持 `workspace_id` 可选参数。

---

## 三、新增文件清单

### 后端

| 文件 | 说明 |
|------|------|
| `backend/app/models/workspace.py` | Workspace, WorkspaceMember, WorkspaceInvitation, WorkspaceActivity 模型 |
| `backend/app/schemas/workspace.py` | Pydantic 校验模型 |
| `backend/app/crud/workspace.py` | 空间/成员/邀请/活动 CRUD |
| `backend/app/api/v1/workspace.py` | 空间 API 路由 |
| `backend/app/api/v1/invitation.py` | 邀请 API 路由 |
| `backend/app/core/permissions.py` | 空间权限依赖函数 |
| `backend/migrate_workspace.py` | 数据库迁移脚本 |

### 前端

| 文件 | 说明 |
|------|------|
| `frontend/src/api/workspace.js` | 空间 API 调用 |
| `frontend/src/pinia/workspaceStore.js` | 空间状态管理 |
| `frontend/src/views/Workspace/List.vue` | 空间列表页 |
| `frontend/src/views/Workspace/Create.vue` | 创建空间页 |
| `frontend/src/views/Workspace/Settings.vue` | 空间设置（信息+成员+邀请+动态） |
| `frontend/src/views/Invitation/Index.vue` | 邀请通知页 |
| `frontend/src/components/Workspace/WorkspaceSwitcher.vue` | 空间切换组件 |
| `frontend/src/composables/useWebSocket.js` | WebSocket 客户端 |

### 修改的文件

| 文件 | 变更 |
|------|------|
| `backend/app/models/task.py` | +workspace_id, +assignee_id |
| `backend/app/models/category.py` | +workspace_id |
| `backend/app/models/tag.py` | +workspace_id |
| `backend/app/models/__init__.py` | 导出新模型 |
| `backend/app/schemas/task.py` | +workspace_id, +assignee_id |
| `backend/app/schemas/category.py` | +workspace_id |
| `backend/app/schemas/tag.py` | +workspace_id |
| `backend/app/crud/task.py` | workspace/assignee 筛选支持 |
| `backend/app/crud/category.py` | workspace 筛选支持 |
| `backend/app/crud/tag.py` | workspace 筛选支持 |
| `backend/app/crud/statistics.py` | workspace 筛选支持 |
| `backend/app/api/v1/task.py` | workspace 权限检查 |
| `backend/app/api/v1/category.py` | workspace_id 参数 |
| `backend/app/api/v1/tag.py` | workspace_id 参数 |
| `backend/app/api/v1/statistics.py` | workspace_id 参数 |
| `backend/app/api/v1/websocket.py` | 空间事件频道 |
| `backend/app/api/v1/__init__.py` | 注册新路由 |
| `backend/app/services/cache_service.py` | (预留) |
| `backend/init_db.py` | 新表打印信息 |
| `frontend/src/api/task.js` | batchDelete 支持 workspace_id |
| `frontend/src/api/category.js` | getCategories 支持 params |
| `frontend/src/pinia/taskStore.js` | 自动注入 workspace 上下文 |
| `frontend/src/pinia/categoryStore.js` | 自动注入 workspace 上下文 |
| `frontend/src/router/routes.js` | +4 个新路由 |
| `frontend/src/layouts/MainLayout.vue` | 空间切换器 + 菜单项 |
| `frontend/src/views/Task/List.vue` | 空间标识 + 标签加载 |
| `frontend/src/views/Category/Index.vue` | 空间标识 |
| `frontend/src/views/User/Tags.vue` | 空间标识 + API 上下文 |

---

## 四、权限矩阵

| 操作 | Owner | Admin | Member |
|------|-------|-------|--------|
| 修改空间信息 | ✔ | ✔ | ✘ |
| 解散空间 | ✔ | ✘ | ✘ |
| 管理成员（邀请/移除/改角色） | ✔ | ✔ | ✘ |
| 创建空间任务 | ✔ | ✔ | ✔ |
| 编辑自己的任务 | ✔ | ✔ | ✔ |
| 编辑他人的任务 | ✔ | ✔ | ✘ |
| 删除自己的任务 | ✔ | ✔ | ✔ |
| 删除他人的任务 | ✔ | ✔ | ✘ |
| 管理分类/标签 | ✔ | ✔ | ✔ |

---

## 五、使用流程

1. 用户A创建空间 → 自动成为 Owner → 自动创建"未分类"默认分类
2. 用户A在空间设置页邀请用户B（填写B的注册邮箱）
3. 用户B在"邀请通知"页收到邀请 → 接受 → 自动加入空间
4. 两人通过侧边栏空间切换器切换到同一空间
5. 任务/分类/标签页面自动显示空间数据，创建的数据属于该空间
6. 通过活动日志页查看空间操作记录

---

## 六、验证清单

- [ ] 运行 `python migrate_workspace.py` 执行数据库迁移
- [ ] 原有个人任务/分类/标签数据完整保留
- [ ] 创建空间 → 自动创建"未分类"
- [ ] 邀请成员 → 接受/拒绝邀请
- [ ] 不同角色权限控制正确
- [ ] 空间切换后任务/分类/标签数据切换正确
- [ ] 前端构建成功（`npm run build`）
- [ ] 两个浏览器窗口模拟多用户协作
