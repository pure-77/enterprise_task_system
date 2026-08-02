# 任务系统空间隔离与权限管控

## 需求

1. 团队空间和个人空间的分类、标签隔离，互不干扰
2. 管理员/创建者可分配任务给成员，任务标明分配给谁
3. 成员只能看到自己的任务，完成后可提交完成
4. 团队公开任务无需分配个人，全员可见可编辑

---

## 数据库变更

**表：`tasks`** — 新增 `is_team_wide` 字段

```sql
ALTER TABLE tasks ADD COLUMN is_team_wide BOOLEAN DEFAULT FALSE
  COMMENT '团队公开任务，全员可见可编辑';
```

迁移已写入 `backend/app/db/session.py` 的 `init_db()`，启动时自动执行。

---

## 后端变更

### 1. Model — `backend/app/models/task.py`

| 变更 | 说明 |
|------|------|
| 新增 `is_team_wide` 列 | `Column(Boolean, default=False)` |
| 新增 `assignee_nickname` 属性 | 返回 `self.assignee.nickname`，用于 API 响应 |

### 2. Schema — `backend/app/schemas/task.py`

`TaskBase`、`TaskCreate`、`TaskUpdate`、`TaskResponse` 均新增 `is_team_wide` 字段。

### 3. CRUD — `backend/app/crud/task.py`

**新增 `get_task_with_permission(db, task_id, user_id)`**

替代旧的 `get_by_id`（原先仅允许创建者读取），实现完整角色权限：

| 情境 | 权限 |
|------|------|
| 个人任务 | 仅创建者可读 |
| 团队任务 + OWNER/ADMIN | 可读任何任务 |
| 团队任务 + MEMBER | 可读：分配给自己的 / 自己创建的 / 团队公开的 |

**重写 `get_multi`**

- 列表查询加入 workspace 成员校验（非成员返回空列表）
- MEMBER 角色按 `assignee_id == user_id OR user_id == user_id OR is_team_wide == True` 过滤
- OWNER/ADMIN 可看团队内所有任务

### 4. API — `backend/app/api/v1/task.py`

#### 更新接口 `PUT /tasks/{id}`

| 角色 | 权限 |
|------|------|
| 个人任务创建者 | 编辑全部字段 |
| `is_team_wide=true` 任何成员 | 编辑全部字段 |
| `is_team_wide=false` OWNER/ADMIN/创建者 | 编辑全部字段 |
| `is_team_wide=false` 被分配人 | **仅可编辑 status** |

被分配人尝试编辑其他字段 → `403 "你只能更新任务状态"`

#### 状态更新 `PATCH /tasks/{id}/status`

- 创建者 / 被分配人 / 团队公开任务成员 → 可更新状态
- 被分配人可提交完成（`completed`）或标记进行中（`in_progress`）

#### 删除 `DELETE /tasks/{id}`

- 个人任务：仅创建者
- 团队任务：OWNER / ADMIN / 创建者

#### 列表 `GET /tasks`

- 加入 workspace 成员校验
- 批量更新/删除加入 workspace 成员校验

---

## 前端变更

### 任务编辑 — `components/TaskEditDialog.vue` + `views/Task/Edit.vue`

| 新增字段 | 显示条件 | 说明 |
|----------|----------|------|
| 被分配人下拉框 | 团队空间 + admin/owner | 从 workspace 成员列表加载 |
| 团队公开开关 | 团队空间 + admin/owner | el-switch，提示"所有成员可见、可编辑" |

修复：加载分类/标签时传入当前 workspace_id，不再漏传。

### 任务卡片 — `components/TaskCard.vue`

- 显示 `assignee_nickname`（被分配人姓名）
- 显示"团队"蓝色徽章（`is_team_wide=true`）

### 任务列表 — `views/Task/List.vue`

- 新增被分配人筛选下拉框（团队空间模式下可见）
- 新增 `loadFilterMembers()` 加载成员列表用于筛选

### 任务详情 — `views/Task/Detail.vue`

- 显示被分配人信息行
- 显示"所有成员可见可编辑"标签（`is_team_wide=true`）

### Dashboard — `views/Dashboard/Index.vue`

- 修复：统计加载时传入 `workspace_id`，不再始终显示个人空间数据

### 状态管理 — `pinia/taskStore.js`

- `filters` 新增 `assignee_id`
- `updateTask` 合并 workspace 上下文
- `resetFilters` 包含 `assignee_id`

---

## 权限矩阵

| 操作 | 个人任务 | 团队非公开 | 团队公开 |
|------|:--------:|:-----------:|:--------:|
| 查看 | 创建者 | 创建者 + OWNER/ADMIN + 被分配人 | 所有成员 |
| 编辑全部 | 创建者 | 创建者 + OWNER/ADMIN | 所有成员 |
| 仅编辑状态 | — | 被分配人 | 所有成员 |
| 删除 | 创建者 | 创建者 + OWNER/ADMIN | 创建者 + OWNER/ADMIN |

---

## 验证要点

1. 个人空间创建分类/标签 → 切到团队空间 → 不出现
2. 团队空间创建分类/标签 → 切到个人空间 → 不出现
3. admin 创建任务分配给成员 A → 成员 B 看不到
4. 创建 `is_team_wide=true` 任务 → 所有成员可见、可编辑
5. 成员被分配任务 → 可标记为"已完成"
6. 成员尝试编辑非自己的非公开任务 → 403
