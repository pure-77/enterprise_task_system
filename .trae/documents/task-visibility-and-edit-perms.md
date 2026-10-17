# Workspace 任务可见性与修改权限修复计划

## Context

用户明确了 workspace 任务的可见性和修改权限规则。上一轮修复了分类隔离漏洞和**过度放宽**的可见性（全量可见），现在需要**恢复正确的可见性过滤**并**补齐状态修改的权限校验**。

### 规则总览

| 维度 | Owner / Admin | 普通成员 |
|---|---|---|
| **可见性** | workspace 内所有任务 | 分配给自己的 + 自己创建的 + is_team_wide |
| **修改权限（PUT）** | 所有任务 | 仅 is_team_wide 或 分配给自己的 |
| **状态修改（PATCH /status）** | 所有任务 | 仅 is_team_wide 或 分配给自己的 |
| is_team_wide（选了「全部」） | 任何成员可改 | 同 |

**关键变化（与当前代码对比）：**
- 恢复被删的 workspace 成员可见性过滤块
- 去掉"创建者能编辑但没分配给自己"的权限
- PATCH /tasks/{id}/status 当前只有可见性校验，缺少修改权限校验（bug）

---

## 修改 1：恢复 task.py 可见性过滤

**文件：** `backend/app/crud/task.py` L146-L148（我上轮改成了全量可见）

**恢复：** 在 workspace 成员校验后加回普通成员的可见性过滤块：

```python
query = query.filter(Task.workspace_id == workspace_id)

if member.role not in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN]:
    # 普通成员 → 分配给自己 + 自己创建的 + 团队公开 + 多人分配包含自己
    from app.models.task_assignee import task_assignees
    query = query.outerjoin(
        task_assignees,
        Task.id == task_assignees.c.task_id
    ).filter(
        or_(
            Task.assignee_id == user_id,
            Task.user_id == user_id,
            Task.is_team_wide == True,
            task_assignees.c.user_id == user_id
        )
    )
```

---

## 修改 2：PUT /tasks/{id} — 去掉创建者的编辑权限

**文件：** `backend/app/api/v1/task.py` L292

**当前：** `member.role in [OWNER, ADMIN] or db_task.user_id == user_id` → 创建者可编辑

**修复：** 去掉 `or db_task.user_id == user_id`。创建者如果没分配给自己，就不能改。

修改后 can_edit_all 逻辑：
```python
if member.role in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN]:
    can_edit_all = True
elif db_task.assignee_id == user_id:
    can_edit_all = True
elif any(a.id == user_id for a in db_task.assignees):
    can_edit_all = True
# is_team_wide 的情况在上面 L280-L288 已处理（任何成员可改）
```

---

## 修改 3：PATCH /tasks/{id}/status — 补齐修改权限校验（当前是 bug）

**文件：** `backend/app/api/v1/task.py` L369-L408

**当前问题：** PATCH /status 只做了**可见性**校验（get_task_with_permission），然后除了 team_wide+completed 外直接 update。这意味着**只要能看到任务就能改它的状态**，完全绕过了修改权限。

**修复：** 在调用 `task_crud.update` 前，加与 PUT 相同的修改权限校验：

```python
db_task = task_crud.get_task_with_permission(db, task_id, user_id)
if not db_task:
    raise HTTPException(status_code=404, detail="任务不存在")

# --- 新增：修改权限校验 ---
if db_task.workspace_id is None:
    # 个人任务：仅创建者
    if db_task.user_id != user_id:
        raise HTTPException(status_code=403, detail="仅任务创建者可修改状态")
elif db_task.is_team_wide:
    # 团队公开（选了「全部」）：任何成员可改，但 completed 需 Owner/Admin（已有 L387-L397 处理）
    pass
else:
    # 非公开团队任务
    member = get_workspace_member(db_task.workspace_id, user_id, db)
    if member.role in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN]:
        pass  # 可改
    elif db_task.assignee_id == user_id or any(a.id == user_id for a in db_task.assignees):
        pass  # 分配给自己，可改
    else:
        raise HTTPException(status_code=403, detail="仅任务 Owner/Admin 或被分配人可修改状态")
```

---

## 不修改的部分

| 位置 | 理由 |
|---|---|
| `get_task_with_permission` | 是**可见性**校验（读权限），方向正确，不需要改 |
| `get_multi` 的 OWNER/ADMIN 全量可见 | 当前已经跳过了普通成员的过滤，正确 |
| DELETE /tasks/{id} | 当前只允许 Owner/Admin/创建者删除，合理 |
| 前端 assignee 选择 | 用户说的"给空间内的人分配"已由现有 assignee_id + assignees M2M 支持 |
| Category 隔离 | 上轮已修复 |
| Tag 隔离 | 经审查已正确 |

---

## 修改文件清单

| 文件 | 改动 |
|---|---|
| `backend/app/crud/task.py` | 恢复 L146 后的普通成员可见性过滤块（加回 ~14 行） |
| `backend/app/api/v1/task.py` | 1) PUT L292 去掉 `or db_task.user_id == user_id`<br>2) PATCH /status 补齐权限校验（~20 行） |

---

## 验证方法

1. **可见性** — workspace 成员 A 创建任务，分配给 B：
   - Owner/Admin 能看到
   - A（创建者）能看到（user_id 过滤）
   - B（被分配）能看到（assignee_id 过滤）
   - 成员 C 看不到（没分配没创建）
2. **is_team_wide** — 标记"全部"的任务，所有成员都能看到
3. **修改权限** — 成员 C 尝试通过 API 改任务状态 → 返回 403
4. **PUT vs PATCH** — 两条路径的修改权限一致（PUT 改全部字段，PATCH 只改 status，但权限规则相同）
