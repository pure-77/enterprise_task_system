# Workspace 任务可见性 & 数据隔离修复计划

## Context

用户反馈系统有两类业务逻辑问题：
1. Workspace 内任务可见性过度过滤 — 普通成员只能看到分配给自己的任务
2. 个人空间 ↔ Workspace 隔离不彻底 — 存在多处遗漏 workspace_id 过滤导致串空间的漏洞

---

## 修改 1：Workspace 任务可见性（task.py）

**文件：** `backend/app/crud/task.py` L149-L162

**问题：** 普通 workspace 成员被额外过滤为"只能看到分配给自己 / 自己创建 / is_team_wide / 多人分配含自己"。Workspace 是共享空间，所有成员都应该能看到该 workspace 下的全部任务。

**修复：** 删除 L149-L162 的整个 `if member.role not in [...]` 块，让所有 workspace 成员走统一的 `Task.workspace_id == workspace_id` 过滤（已在 L147 执行）。

---

## 修改 2：Category 隔离漏洞（category.py）

### 2a. `get_by_id_and_user_id` — 个人模式漏了 workspace_id 过滤

**文件：** `backend/app/crud/category.py` L20-L25

**问题：** workspace_id=None（个人模式）时，只靠 `id + user_id` 查询，没加 `workspace_id IS NULL`。一个 workspace 分类如果创建者恰好也是查这个 ID 的用户，就会串进来。

```python
# 当前（有漏洞）:
query = db.query(self.model).filter(self.model.id == id, self.model.user_id == user_id)
if workspace_id is not None:
    query = query.filter(self.model.workspace_id == workspace_id)
# ← 没有 else!

# 修复后:
query = db.query(self.model).filter(self.model.id == id, self.model.user_id == user_id)
if workspace_id is not None:
    query = query.filter(self.model.workspace_id == workspace_id)
else:
    query = query.filter(self.model.workspace_id == None)  # ← 补
```

### 2b. `delete` 的 move_to_category_id — 完全没加 workspace_id 过滤

**文件：** `backend/app/crud/category.py` L44-L47

**问题：** 任务迁移目标分类只按 `id` 查，没加 workspace_id 约束。可以把 workspace X 分类的任务迁到 workspace Y 的分类上。

```python
# 当前（有漏洞）:
target_category = db.query(self.model).filter(
    self.model.id == move_to_category_id
).first()

# 修复后（加上 workspace 隔离）:
target_q = db.query(self.model).filter(self.model.id == move_to_category_id)
if workspace_id is not None:
    target_q = target_q.filter(self.model.workspace_id == workspace_id)
else:
    target_q = target_q.filter(self.model.workspace_id == None)
target_category = target_q.first()
```

---

## 不修改的部分（经确认逻辑正确）

| 位置 | 现状 | 结论 |
|---|---|---|
| category.py `get_by_user_id` L13-L18 | 个人模式加了 `workspace_id == None`，workspace 模式加了 `workspace_id == X` | ✓ 正确 |
| category.py `get_with_task_count` L73-L78 | 同上，也有 else 分支 | ✓ 正确 |
| tag.py `get_multi` L20-L25 | 个人模式加了 `user_id + workspace_id IS NULL`，workspace 模式只按 `workspace_id` | ✓ 正确 |
| tag.py `get_by_id` L11-L16 | 同上，也有 else 分支 | ✓ 正确 |
| tag.py `get_by_name` L61-L65 | 同上，也有 else 分支 | ✓ 正确 |
| task.py 个人空间分支 L163-L168 | `user_id=自己 AND workspace_id IS NULL` | ✓ 正确 |

---

## 修改文件清单

| 文件 | 改动 |
|---|---|
| `backend/app/crud/task.py` | 删除 L149-L162 普通成员过度过滤块（14行） |
| `backend/app/crud/category.py` | 1) `get_by_id_and_user_id` 补 else 分支（1行）<br>2) `delete` 的 move_to_category 补 workspace 过滤（3行） |

---

## 验证方法

1. **Workspace 任务可见性** — workspace 成员 A 创建任务，成员 B 应能在列表里看到（不需手动分配给 B）
2. **分类隔离** — 个人空间创建的分类，workspace 成员看不到；workspace 创建的分类，个人空间看不到
3. **成员创建者隔离**（用户指定：仅创建者可见）— workspace 成员 A 创建的分类，成员 B 在 workspace 里看不到（当前 `user_id` 过滤已实现）
4. **delete 不串空间** — 尝试删除个人分类并把任务迁移到 workspace 分类，应被拒绝（或反过来）
