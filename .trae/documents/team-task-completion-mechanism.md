# 团队任务多人完成机制 — 完整实施计划（前后端）

## Context

团队任务（is_team_wide=True 或多人 assignees）需要**每个被分配人分别标记"我完成了"**，所有人都标记完成后任务自动变成 completed。单人 assignee 保持现状不变。

**现有基础（已就绪）：**
- `TaskCompletion` model（task_id + user_id + completed_at）✓
- `POST /{task_id}/complete` 接口 ✓ 但硬编码只允许 team_wide
- `TaskResponse.completions / completed_count / total_members` schema ✓
- 前端 Detail.vue 有完成进度 UI ✓ 但只对 team_wide 展示、按钮无权限控制

---

## 后端改动（task.py 主）

### 1. POST /complete 放开适用范围
**文件：** `backend/app/api/v1/task.py` ~L462

**改：** `if not db_task.is_team_wide: raise 400`
**为：** 判断是否需要多人追踪 — team_wide **或** assignees > 1

### 2. POST /complete 自动推进 status
写完 TaskCompletion 后判断目标人是否全部完成，是则自动 `db_task.status = COMPLETED`。

新增私有逻辑（可放在 complete_team_task 内部或提取辅助函数）：
```python
# 获取目标人集合
if db_task.is_team_wide:
    target_ids = set(WorkspaceMember.active_members(db_task.workspace_id).user_ids)
elif len(db_task.assignees or []) > 1:
    target_ids = {a.id for a in db_task.assignees}
else:
    target_ids = set()  # 单人任务不跟踪

completed_ids = {c.user_id for c in db_task.completions}
if target_ids and completed_ids >= target_ids:
    db_task.status = TaskStatus.COMPLETED
```

### 3. PATCH /status 防绕过
在实际 update 前，多人追踪任务若尝试设为 completed 且未全部完成 → 拒绝。

### 4. completions nickname 修复
**问题：** `CompletionUser.nickname` 需要从 `TaskCompletion.user.nickname` 拿，Pydantic `from_attributes=True` 不会自动穿透 relationship。

**方案：** 给 `CompletionUser` schema 加 `@model_validator(mode='from_attributes')` 从 `user` relationship 提取 nickname。

### 5. total_members 覆盖多人 assignees
**文件：** `backend/app/api/v1/task.py` get_task / update_task 端点注入 `_total_members_cache` 时：
- team_wide → workspace 活跃成员数（不变）
- 多人 assignees → `len(db_task.assignees)`
- 单人 → 0（不展示进度）

---

## 前端改动（Detail.vue 主）

### 1. 完成进度区块展示条件
**文件：** `frontend/src/views/Task/Detail.vue` L40

**改：** `v-if="task.is_team_wide"`
**为：** `v-if="task.is_team_wide || task.assignee_nicknames?.length > 0"`

### 2. "我完成了"按钮权限控制
**文件：** `frontend/src/views/Task/Detail.vue` L63

按钮只对目标人显示，且已完成的人不再显示：
```
v-if="canShowMarkComplete"
```
computed 或 method：
```js
const canShowMarkComplete = () => {
  if (!task.is_team_wide && !(task.assignee_nicknames?.length > 0)) return false
  // 已完成则不再显示
  if (task.completions?.some(c => c.user_id === currentUserId)) return false
  // 当前用户是目标人（team_wide 下默认是成员，多人 assignees 需判断是否在列表中）
  if (task.assignee_nicknames?.length > 0) {
    // 多人 assignees 下：只有被分配到的人能点
    return userStore.user?.nickname && task.assignee_nicknames.includes(userStore.user.nickname)
  }
  return true  // team_wide：任何 workspace 成员都能点
}
```

---

## 修改文件清单

| 文件 | 类型 | 改动 |
|---|---|---|
| `backend/app/api/v1/task.py` | 后端 | POST /complete 放开范围 + 自动推进 status、PATCH 防绕过、total_members 覆盖 |
| `backend/app/schemas/task.py` | 后端 | CompletionUser 加 model_validator 提取 nickname |
| `frontend/src/views/Task/Detail.vue` | 前端 | v-if 覆盖多人 assignees、按钮加权限控制 |

**不修改：** TaskCompletion model、Task model、task_crud.py、Edit.vue（assignee_ids 多选已存在）、TaskListResponse schema。

---

## 验证方法

1. 多人 assignees 任务 → 分配给 A/B/C，分别点"我完成了" → 最后一人点后 status 自动变 completed
2. team_wide 任务 → workspace 5 人分别点 → 自动 completed
3. 直接 curl PATCH status=completed（没走 POST /complete）→ 多人任务应返回 400
4. 单人 assignee 任务 → 直接 PATCH status=completed → 正常（不受影响）
5. Detail.vue 多人 assignees 任务 → 看到进度条、已完成列表、"我完成了"按钮（仅自己可见）
6. 重复标记 → 返回"已标记"
