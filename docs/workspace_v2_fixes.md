# 空间隔离修复 + 成员权限 + 团队任务完成追踪

## 决策记录

| 问题 | 决策 |
|------|------|
| 成员权限 | 不能创建/删除任务，可以编辑分配给自己的任务的全部字段 |
| 完成追踪存储 | 新建 `task_completions` 表，每人一条记录 |
| 多人分配存储 | 新建 `task_assignees` 中间表（M2M） |
| 挂载竞态修复 | `v-if` 控制 router-view 延迟渲染 |
| 分类/标签同名 | 允许，两个空间隔离 |
| 团队公开任务完成 | 所有人完成后，管理员手动切换状态 |

---

## Bug 修复

### 1. 竞态：切换 workspace 后分类/标签不更新

**根因：** Vue 子组件 `onMounted` 先于父组件 `MainLayout.onMounted` 执行。子组件加载数据时 `workspaceStore.currentWorkspaceId` 还是 `null`。

**修复：** `layouts/MainLayout.vue`
```html
<router-view v-if="ready" />
```
```js
const ready = ref(false)
onMounted(async () => {
  await workspaceStore.loadWorkspaces()
  workspaceStore.restoreWorkspaceContext()
  ready.value = true  // workspace 上下文就绪后才渲染子组件
})
```

### 2. Statistics 页不传 workspace_id

**修复：** `api/statistics.js` 全部函数新增 `workspaceId` 参数；`views/Statistics/Index.vue` 调用时传入。

### 3. 普通成员可以创建工作区任务 → 403

**修复：** `api/v1/task.py` — `create_task` 新增角色检查：
```python
if member.role == WorkspaceRole.MEMBER:
    raise HTTPException(403, "普通成员不能创建工作区任务")
```

### 4. 被分配人只能改状态 → 可编辑全部字段

**修复：** `api/v1/task.py` — `update_task` 改为：
```python
elif db_task.assignee_id == user_id:
    can_edit_all = True
elif any(a.id == user_id for a in db_task.assignees):
    can_edit_all = True  # 多人分配
```

### 5. assignee_id 无校验

**修复：** 创建/更新时校验被分配人是否是 workspace 成员，不是 → 400。

---

## 新增功能

### 团队任务完成追踪

**数据模型：** `models/task_completion.py`
```python
class TaskCompletion(BaseModel):
    task_id = FK(tasks.id)
    user_id = FK(users.id)
    completed_at = DateTime
```

**API：** `POST /tasks/{task_id}/complete`
- 仅 `is_team_wide=true` 可用
- 每人只能标记一次
- 写入 task_completions 表

**任务详情响应** 新增字段：
```json
{
  "completions": [{"user_id":1, "nickname":"张三", "completed_at":"..."}],
  "total_members": 5,
  "completed_count": 2
}
```

### 管理员手动完成

`PATCH /tasks/{id}/status` → 仅 OWNER/ADMIN 可将团队公开任务标记为 `completed`。
其他状态（in_progress/cancelled/pending）不受限制。

### 多人任务分配

**数据模型：** `models/task_assignee.py`
```python
task_assignees = Table(
    "task_assignees",
    Column("task_id", FK("tasks.id")),
    Column("user_id", FK("users.id")),
)
```

Task 模型新增 M2M 关系：
```python
assignees = relationship("User", secondary="task_assignees")
```

### 前端 UI 变更

**TaskEditDialog / Task/Edit.vue：**
- 被分配人从单选 → 多选下拉框（admin/owner 可见）
- `is_team_wide=true` 时隐藏被分配人选择器
- 选 1 人：assignee_id + assignee_ids 都设
- 选多人：assignee_ids 存全部

**Task/Detail.vue：**
- 团队公开任务显示完成进度条（已完成人数 / 总人数）
- 已完成成员列表（昵称 + 时间）
- "我完成了"按钮（成员点击）
- 多人分配名单显示

**TaskCard.vue：**
- 显示被分配人姓名（已在上一版实现）

---

## 迁移

启动时自动执行（`db/session.py` → `init_db()`）：

```sql
CREATE TABLE IF NOT EXISTS task_completions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_id INT NOT NULL,
    user_id INT NOT NULL,
    completed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE KEY uk_task_user (task_id, user_id)
);

CREATE TABLE IF NOT EXISTS task_assignees (
    task_id INT NOT NULL,
    user_id INT NOT NULL,
    PRIMARY KEY (task_id, user_id),
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

---

## 最终权限矩阵

| 操作 | 个人任务 | 团队非公开 | 团队公开 |
|------|:--------:|:-----------:|:--------:|
| 创建 | — | OWNER/ADMIN | OWNER/ADMIN |
| 查看 | 创建者 | OWNER/ADMIN/创建者/被分配人 | 所有成员 |
| 编辑全部 | 创建者 | OWNER/ADMIN/创建者/被分配人 | 所有成员 |
| 标记"我完成了" | — | — | 所有成员 |
| 标记任务已完成 | — | — | 仅 OWNER/ADMIN |
| 删除 | 创建者 | OWNER/ADMIN/创建者 | OWNER/ADMIN/创建者 |

---

## 修改文件清单

| 层 | 文件 | 变更 |
|----|------|------|
| 后端 | `models/task_completion.py` | 新建 |
| 后端 | `models/task_assignee.py` | 新建 |
| 后端 | `models/task.py` | 新增 assignees M2M、assignee_nicknames/total_members/completed_count 属性 |
| 后端 | `schemas/task.py` | 新增 CompletionUser、assignee_ids、completions、total_members、completed_count |
| 后端 | `crud/task.py` | 处理 assignee_ids CRUD、M2M 过滤、_load_task_relations |
| 后端 | `api/v1/task.py` | 创建角色限制、assignee 校验、complete 端点、状态权限 |
| 后端 | `db/session.py` | 新增 task_completions + task_assignees 迁移 |
| 前端 | `layouts/MainLayout.vue` | v-if 修复挂载竞态 |
| 前端 | `api/statistics.js` | 全部函数加 workspaceId |
| 前端 | `api/task.js` | 新增 completeTeamTask |
| 前端 | `views/Statistics/Index.vue` | 传入 workspace_id |
| 前端 | `views/Task/Detail.vue` | 完成进度 + 多人 + "我完成了" |
| 前端 | `components/TaskEditDialog.vue` | 多人选择 + 团队公开隐藏指派人 |
| 前端 | `views/Task/Edit.vue` | 同上 |

---

## 验证要点

1. 切换到团队空间 → 分类/标签/统计 → 显示团队数据（非个人）
2. MEMBER 尝试创建任务 → 403
3. MEMBER 编辑分配给自己的任务的任意字段 → 成功
4. 创建任务时选非成员为被分配人 → 400
5. 团队公开任务：成员 A 标记完成 → 进度更新，A 显示为已完成
6. 团队公开任务：成员再次标记 → 400 "已标记过"
7. 全部成员完成后 → 管理员标记完成 → 任务状态变为 completed
8. 非管理员尝试标记团队任务为 completed → 403
9. 选多人为被分配人 → 多人都能看到和编辑
10. `is_team_wide=true` → 指派人选择器隐藏
