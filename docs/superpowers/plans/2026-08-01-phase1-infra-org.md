# Phase 1: 基础设施 + 组织架构 — 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立模块化架构骨架，实现组织架构（部门树、职位、成员管理），为后续所有模块奠定基础。

**Architecture:** 将现有扁平目录重构为 `modules/` + `middleware/` + `shared/` 三层模块化结构。现有任务代码迁入 `modules/task/`。新增 `modules/org/` 实现部门、职位、成员扩展。引入统一响应格式和审计日志中间件。

**Tech Stack:** FastAPI 0.135, SQLAlchemy 2.0, MySQL, Redis, Pydantic 2.9, Vue 3 + Element Plus + Pinia, Docker

## Global Constraints

- 所有 API 响应使用统一格式 `{"code": 0, "message": "success", "data": {...}}`
- 所有表使用 InnoDB + utf8mb4，软删除使用 `is_active` 字段
- 现有功能（任务 CRUD、工作空间、认证）不能有任何回归
- 密码使用 SHA-256 + bcrypt 双重处理
- 时间统一使用 Asia/Shanghai 时区
- 前端使用 Composition API + `<script setup>` 语法

---

## File Structure Map

```
backend/app/
├── main.py                          # [MODIFY] 统一挂载 modules/* 路由
├── core/                            # [KEEP] 不变
│   ├── config.py
│   ├── security.py
│   ├── permissions.py
│   ├── exceptions.py                # [MODIFY] 添加企业级异常类
│   └── celery_config.py
├── db/                              # [KEEP] 不变
│   ├── base.py                      # [MODIFY] 确认 BaseModel 可复用
│   ├── session.py                   # [MODIFY] 扩展 init_db 导入新模型
│   └── redis_client.py
├── middleware/                       # [NEW]
│   ├── __init__.py
│   ├── response_handler.py          # 统一响应格式包装
│   └── audit_log.py                 # 操作审计日志中间件
├── modules/                         # [NEW] 业务模块根目录
│   ├── __init__.py
│   ├── task/                        # [MIGRATE] 现有代码迁移至此
│   │   ├── __init__.py
│   │   ├── models.py                # Task, Category, Tag, TaskCompletion, workspace models
│   │   ├── schemas.py               # Task Pydantic schemas
│   │   ├── crud.py                  # Task CRUD operations
│   │   ├── services.py              # TaskStatusService
│   │   └── router.py                # Task API endpoints
│   └── org/                         # [NEW] 组织架构模块
│       ├── __init__.py
│       ├── models.py                # Department, Position
│       ├── schemas.py               # Pydantic schemas
│       ├── crud.py                  # CRUD operations
│       └── router.py                # API endpoints
├── shared/                          # [NEW] 共享服务
│   ├── __init__.py
│   ├── response.py                  # 统一响应工具函数
│   ├── auth_depends.py              # 认证依赖（从 api/v1 提取）
│   └── utils.py                     # 通用工具（分页、时区等）
├── api/                             # [DEPRECATED] 旧 API 层逐步迁移
│   └── v1/                          # 保留兼容，路由转发到 modules/*
└── services/                        # [MIGRATE] 迁入 shared/ 或 modules/
    ├── cache_service.py
    ├── email_service.py
    └── task_status_service.py

frontend/src/
├── router/
│   ├── index.js                     # [MODIFY] 加载分模块路由
│   └── routes/
│       ├── task.js                  # [MIGRATE] 现有路由
│       └── org.js                   # [NEW] 组织架构路由
├── stores/
│   └── org.js                       # [NEW] 组织架构 Store
├── api/
│   └── org.js                       # [NEW] 组织架构 API
├── components/
│   ├── layout/
│   │   ├── MainLayout.vue           # [MODIFY] 新侧边栏 + 顶部栏
│   │   ├── Sidebar.vue              # [NEW] 统一侧边栏导航
│   │   └── TopBar.vue               # [NEW] 顶部栏（搜索+用户菜单）
│   ├── org/                         # [NEW] 组织架构组件
│   │   ├── DeptTree.vue             # 部门树组件
│   │   ├── DeptDialog.vue           # 部门创建/编辑弹窗
│   │   ├── MemberTable.vue          # 成员列表表格
│   │   └── MemberEditDialog.vue     # 成员编辑弹窗
├── views/
│   └── org/                         # [NEW]
│       ├── DeptManage.vue           # 部门管理页面
│       └── MemberRoster.vue         # 成员花名册页面
```

---

### Task 1: 创建新目录结构

**Files:**
- Create: `backend/app/middleware/__init__.py`
- Create: `backend/app/modules/__init__.py`
- Create: `backend/app/modules/task/__init__.py`
- Create: `backend/app/modules/org/__init__.py`
- Create: `backend/app/shared/__init__.py`
- Create: `frontend/src/router/routes/org.js`
- Create: `frontend/src/stores/org.js`
- Create: `frontend/src/api/org.js`
- Create: `frontend/src/components/org/` (empty dir placeholder)
- Create: `frontend/src/views/org/` (empty dir placeholder)

- [ ] **Step 1: 创建所有新目录和 __init__.py**

```bash
mkdir -p backend/app/middleware
mkdir -p backend/app/modules/task
mkdir -p backend/app/modules/org
mkdir -p backend/app/shared
mkdir -p frontend/src/router/routes
mkdir -p frontend/src/components/org
mkdir -p frontend/src/components/layout
mkdir -p frontend/src/views/org
```

- [ ] **Step 2: 创建所有 __init__.py 文件**

```bash
touch backend/app/middleware/__init__.py
touch backend/app/modules/__init__.py
touch backend/app/modules/task/__init__.py
touch backend/app/modules/org/__init__.py
touch backend/app/shared/__init__.py
```

- [ ] **Step 3: 创建前端占位文件**

`frontend/src/router/routes/org.js`:
```js
export default []
```

`frontend/src/stores/org.js`:
```js
import { defineStore } from 'pinia'

export const useOrgStore = defineStore('org', {
  state: () => ({}),
  actions: {}
})
```

`frontend/src/api/org.js`:
```js
import request from './request'

export default {}
```

- [ ] **Step 4: 验证目录结构**

Run: `ls -R backend/app/middleware backend/app/modules backend/app/shared`
Expected: 所有目录和 `__init__.py` 文件存在

- [ ] **Step 5: Commit**

```bash
git add backend/app/middleware backend/app/modules backend/app/shared frontend/src/router/routes/org.js frontend/src/stores/org.js frontend/src/api/org.js
git commit -m "feat: create modular directory structure for Phase 1"
```

---

### Task 2: 统一响应格式工具

**Files:**
- Create: `backend/app/shared/response.py`
- Test: `backend/test_response.py`

**Interfaces:**
- Produces: `success_response(data, message="success") -> dict`, `error_response(code, message, detail=None, status_code=200) -> dict`, `paginated_response(items, total, page, page_size) -> dict`

- [ ] **Step 1: 编写 shared/response.py**

```python
"""统一响应格式工具"""
from typing import Any, Optional


def success_response(data: Any = None, message: str = "success") -> dict:
    """成功响应"""
    return {
        "code": 0,
        "message": message,
        "data": data
    }


def error_response(
    code: int,
    message: str,
    detail: Optional[str] = None,
    status_code: int = 200
) -> dict:
    """错误响应 — 注意：不直接 raise HTTPException；
    由 response_handler 中间件根据 code 决定实际 HTTP status。
    业务代码使用 raise AppException(code, message, detail) 抛出异常。
    """
    body = {
        "code": code,
        "message": message,
        "data": None
    }
    if detail:
        body["detail"] = detail
    return body


def paginated_response(
    items: list,
    total: int,
    page: int,
    page_size: int
) -> dict:
    """分页响应"""
    return {
        "code": 0,
        "message": "success",
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0
        }
    }
```

- [ ] **Step 2: 编写测试**

`backend/test_response.py`:
```python
"""测试统一响应格式"""
from app.shared.response import success_response, error_response, paginated_response


def test_success_response_with_data():
    result = success_response({"name": "test"})
    assert result["code"] == 0
    assert result["message"] == "success"
    assert result["data"]["name"] == "test"


def test_success_response_no_data():
    result = success_response()
    assert result["code"] == 0
    assert result["data"] is None


def test_error_response():
    result = error_response(code=40401, message="资源不存在", detail="Task id=99 not found")
    assert result["code"] == 40401
    assert result["message"] == "资源不存在"
    assert result["detail"] == "Task id=99 not found"


def test_paginated_response():
    result = paginated_response(items=[1, 2, 3], total=30, page=2, page_size=10)
    assert result["code"] == 0
    assert result["data"]["items"] == [1, 2, 3]
    assert result["data"]["total"] == 30
    assert result["data"]["page"] == 2
    assert result["data"]["total_pages"] == 3


if __name__ == "__main__":
    test_success_response_with_data()
    test_success_response_no_data()
    test_error_response()
    test_paginated_response()
    print("All tests passed!")
```

- [ ] **Step 3: 运行测试**

Run: `cd backend && python test_response.py`
Expected: "All tests passed!"

- [ ] **Step 4: Commit**

```bash
git add backend/app/shared/response.py backend/test_response.py
git commit -m "feat: add unified response format utility"
```

---

### Task 3: 企业级异常类扩展

**Files:**
- Modify: `backend/app/core/exceptions.py`

**Interfaces:**
- Produces: `AppException(code, message, detail=None)`, 子类 `NotFoundException`, `PermissionDeniedException`, `ValidationException`, `UnauthorizedException`

- [ ] **Step 1: 重写 exceptions.py**

```python
"""企业级异常类 — 面试考点：统一的异常体系，包含错误码"""
from fastapi import HTTPException


class AppException(HTTPException):
    """应用基础异常 — 所有业务异常继承此类"""

    def __init__(self, code: int, message: str, detail: str = None):
        self.code = code
        self.message = message
        self.detail = detail
        super().__init__(status_code=200, detail={"code": code, "message": message, "detail": detail})


# ---------- 认证模块 401xx ----------
class UnauthorizedException(AppException):
    def __init__(self, detail: str = "未授权访问"):
        super().__init__(code=40101, message="未授权访问", detail=detail)


class TokenExpiredException(AppException):
    def __init__(self):
        super().__init__(code=40102, message="Token已过期", detail="请重新登录")


# ---------- 权限模块 403xx ----------
class PermissionDeniedException(AppException):
    def __init__(self, detail: str = "没有操作权限"):
        super().__init__(code=40301, message="权限不足", detail=detail)


# ---------- 资源模块 404xx ----------
class NotFoundException(AppException):
    def __init__(self, resource: str = "资源"):
        super().__init__(code=40401, message=f"{resource}不存在", detail=f"请求的{resource}未找到")


# ---------- 验证模块 422xx ----------
class ValidationException(AppException):
    def __init__(self, detail: str = "参数验证失败"):
        super().__init__(code=42201, message="参数验证失败", detail=detail)


# ---------- 业务模块 500xx ----------
class BusinessException(AppException):
    def __init__(self, message: str, detail: str = None):
        super().__init__(code=50001, message=message, detail=detail)


# ---------- 保留旧版兼容 ----------
class EmailAlreadyExistsException(HTTPException):
    def __init__(self):
        super().__init__(status_code=400, detail="邮箱已注册")


class InvalidVerifyCodeException(HTTPException):
    def __init__(self):
        super().__init__(status_code=400, detail="验证码错误或已过期")


class VerifyCodeSendTooFrequentlyException(HTTPException):
    def __init__(self):
        super().__init__(status_code=429, detail="验证码发送过于频繁，请稍后再试")
```

- [ ] **Step 2: 验证现有导入不受影响**

Run: `cd backend && python -c "from app.core.exceptions import EmailAlreadyExistsException, InvalidVerifyCodeException; print('OK')"`
Expected: "OK"

- [ ] **Step 3: Commit**

```bash
git add backend/app/core/exceptions.py
git commit -m "feat: add enterprise exception hierarchy with error codes"
```

---

### Task 4: 统一响应处理中间件

**Files:**
- Create: `backend/app/middleware/response_handler.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: `AppException` from `app.core.exceptions`
- Produces: 中间件自动将字典返回包装为统一格式，并拦截 `AppException`

- [ ] **Step 1: 编写中间件**

`backend/app/middleware/response_handler.py`:
```python
"""统一响应格式中间件"""
import json
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.exceptions import AppException


class ResponseHandlerMiddleware(BaseHTTPMiddleware):
    """统一包装所有响应为 {"code": 0, "message": "success", "data": ...} 格式"""

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)

            # 只处理 JSON 响应
            if response.headers.get("content-type") == "application/json":
                body = b""
                async for chunk in response.body_iterator:
                    body += chunk

                if body:
                    try:
                        data = json.loads(body)
                        # 已经是标准格式则直接返回（如异常处理器已包装）
                        if isinstance(data, dict) and "code" in data:
                            return Response(
                                content=json.dumps(data, ensure_ascii=False),
                                status_code=response.status_code,
                                headers=dict(response.headers),
                                media_type="application/json"
                            )
                        # 否则包装为标准格式
                        wrapped = {
                            "code": 0,
                            "message": "success",
                            "data": data
                        }
                        return Response(
                            content=json.dumps(wrapped, ensure_ascii=False),
                            status_code=response.status_code,
                            headers=dict(response.headers),
                            media_type="application/json"
                        )
                    except json.JSONDecodeError:
                        pass

                return response
            return response

        except AppException as e:
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "code": e.code,
                    "message": e.message,
                    "data": None,
                    "detail": e.detail
                }
            )
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={
                    "code": 50000,
                    "message": "服务器内部错误",
                    "data": None,
                    "detail": str(e)
                }
            )
```

- [ ] **Step 2: 注册中间件到 main.py**

在 `backend/app/main.py` 中，在 CORS 中间件之后添加：

```python
from app.middleware.response_handler import ResponseHandlerMiddleware

# 在 CORS 中间件之后
app.add_middleware(ResponseHandlerMiddleware)
```

- [ ] **Step 3: 编写验证测试**

`backend/test_middleware.py`:
```python
"""测试响应中间件"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check_wrapped():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert data["message"] == "success"
    assert data["data"]["status"] == "healthy"


def test_root_wrapped():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 0
    assert "message" in data


if __name__ == "__main__":
    test_health_check_wrapped()
    test_root_wrapped()
    print("All middleware tests passed!")
```

- [ ] **Step 4: 运行测试**

Run: `cd backend && python test_middleware.py`
Expected: "All middleware tests passed!"

- [ ] **Step 5: Commit**

```bash
git add backend/app/middleware/response_handler.py backend/app/main.py backend/test_middleware.py
git commit -m "feat: add unified response handler middleware"
```

---

### Task 5: 迁移现有模型到 modules/task/

**Files:**
- Create: `backend/app/modules/task/models.py`
- Modify: `backend/app/models/__init__.py` (添加注释说明迁移方向)
- Modify: `backend/app/db/session.py` (更新 init_db 导入)

**Interfaces:**
- Produces: `modules/task/models.py` 包含所有现有模型类（Task, Category, Tag, TaskCompletion, TaskStatus, TaskPriority, User, Workspace, WorkspaceMember, WorkspaceInvitation, WorkspaceActivity + 关联表）

- [ ] **Step 1: 聚合现有模型到 modules/task/models.py**

`backend/app/modules/task/models.py`:
```python
"""任务模块 — 聚合所有现有模型"""
# 从原位置导入所有模型，保持向后兼容
from app.models.user import User
from app.models.task import Task, TaskStatus, TaskPriority
from app.models.category import Category
from app.models.tag import Tag
from app.models.task_tags import task_tags
from app.models.task_assignee import task_assignees
from app.models.task_completion import TaskCompletion
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceInvitation, WorkspaceActivity

__all__ = [
    "User", "Task", "TaskStatus", "TaskPriority",
    "Category", "Tag", "task_tags", "task_assignees",
    "TaskCompletion",
    "Workspace", "WorkspaceMember", "WorkspaceInvitation", "WorkspaceActivity",
]
```

- [ ] **Step 2: 更新 models/__init__.py 添加迁移说明**

```python
# 注意：模型定义保留在原位置 (app/models/*.py)
# 业务模块请使用 from app.modules.task.models import X
# 未来新模块模型直接在 modules/{module}/models.py 中定义
from app.models.user import User
from app.models.category import Category
from app.models.task import Task
from app.models.tag import Tag
from app.models.task_tags import task_tags
from app.models.task_assignee import task_assignees
from app.models.task_completion import TaskCompletion
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceInvitation, WorkspaceActivity

__all__ = ["User", "Category", "Task", "Tag", "TaskCompletion", "Workspace", "WorkspaceMember", "WorkspaceInvitation", "WorkspaceActivity"]
```

- [ ] **Step 3: 验证导入**

Run: `cd backend && python -c "from app.modules.task.models import Task, User, Workspace; print('Task:', Task.__tablename__); print('OK')"`
Expected: "Task: tasks" + "OK"

- [ ] **Step 4: Commit**

```bash
git add backend/app/modules/task/models.py backend/app/models/__init__.py
git commit -m "refactor: aggregate existing models into modules/task/"
```

---

### Task 6: 迁移现有路由到 modules/task/router.py

**Files:**
- Create: `backend/app/modules/task/router.py`
- Modify: `backend/app/api/v1/__init__.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Produces: `task_router` — 包含所有现有任务相关 API 端点，可在 main.py 中统一挂载

- [ ] **Step 1: 创建 modules/task/router.py 作为聚合路由**

```python
"""任务模块路由 — 聚合所有现有 API 端点"""
from fastapi import APIRouter
from app.api.v1 import task as task_endpoints
from app.api.v1 import category as category_endpoints
from app.api.v1 import statistics as statistics_endpoints
from app.api.v1 import tag as tag_endpoints
from app.api.v1 import backup as backup_endpoints
from app.api.v1 import workspace as workspace_endpoints
from app.api.v1 import invitation as invitation_endpoints

task_router = APIRouter()

# 挂载所有现有子路由
task_router.include_router(task_endpoints.router, prefix="/tasks", tags=["tasks"])
task_router.include_router(category_endpoints.router, prefix="/categories", tags=["categories"])
task_router.include_router(statistics_endpoints.router, prefix="/statistics", tags=["statistics"])
task_router.include_router(tag_endpoints.router, prefix="/tags", tags=["tags"])
task_router.include_router(backup_endpoints.router, prefix="/backup", tags=["backup"])
task_router.include_router(workspace_endpoints.router, prefix="/workspaces", tags=["workspaces"])
task_router.include_router(invitation_endpoints.router, prefix="/invitations", tags=["invitations"])
```

- [ ] **Step 2: 更新 api/v1/__init__.py 保持兼容**

```python
from fastapi import APIRouter
from app.api.v1 import auth, profile, websocket
# 任务相关端点已迁移到 modules/task/router.py
# 此处保留向后兼容

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(profile.router, prefix="/profile", tags=["profile"])
api_router.include_router(websocket.router, tags=["websocket"])
```

- [ ] **Step 3: 更新 main.py 使用新路由结构**

在 `backend/app/main.py` 中：

```python
# 注册路由 - 模块化路由管理
from app.api.v1 import api_router
from app.modules.task.router import task_router

app.include_router(api_router, prefix="/api/v1")
app.include_router(task_router, prefix="/api/v1")
```

- [ ] **Step 4: 运行服务验证路由**

Run: `cd backend && timeout 5 python -c "from app.main import app; print('Routes:'); [print(r.path) for r in app.routes]" 2>&1 || true`
Expected: 能看到所有现有路由路径

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/task/router.py backend/app/api/v1/__init__.py backend/app/main.py
git commit -m "refactor: migrate task routes to modular structure"
```

---

### Task 7: 部门与职位数据模型

**Files:**
- Create: `backend/app/modules/org/models.py`

**Interfaces:**
- Produces: `Department` 模型（id, workspace_id, parent_id(自引用), name, leader_id, sort_order, path）, `Position` 模型（id, workspace_id, name, sort_order）

- [ ] **Step 1: 编写 org/models.py**

```python
"""组织架构模块 — 数据模型"""
from sqlalchemy import Column, String, Integer, BigInteger, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import BaseModel


class Department(BaseModel):
    """部门模型 — 支持无限层级树形结构"""
    __tablename__ = "departments"
    __table_args__ = {'extend_existing': True}

    workspace_id = Column(BigInteger, ForeignKey("workspaces.id"), nullable=False, comment="所属工作空间")
    parent_id = Column(BigInteger, ForeignKey("departments.id"), nullable=True, comment="父部门ID，NULL=根部门")
    name = Column(String(100), nullable=False, comment="部门名称")
    leader_id = Column(BigInteger, ForeignKey("users.id"), nullable=True, comment="部门负责人")
    sort_order = Column(Integer, default=0, nullable=False, comment="排序序号")
    path = Column(String(500), nullable=True, comment="物化路径，如 /1/3/15")

    # 关系
    parent = relationship("Department", remote_side="Department.id", backref="children")
    leader = relationship("User", foreign_keys=[leader_id], backref="led_departments")
    workspace = relationship("Workspace", foreign_keys=[workspace_id], backref="departments")

    def __repr__(self):
        return f"<Department(id={self.id}, name={self.name}, path={self.path})>"


class Position(BaseModel):
    """职位模型"""
    __tablename__ = "positions"
    __table_args__ = {'extend_existing': True}

    workspace_id = Column(BigInteger, ForeignKey("workspaces.id"), nullable=False, comment="所属工作空间")
    name = Column(String(50), nullable=False, comment="职位名称")
    sort_order = Column(Integer, default=0, nullable=False, comment="排序序号")

    workspace = relationship("Workspace", foreign_keys=[workspace_id], backref="positions")

    def __repr__(self):
        return f"<Position(id={self.id}, name={self.name})>"
```

- [ ] **Step 2: 更新 init_db 以创建新表**

在 `backend/app/db/session.py` 的 `init_db()` 函数末尾，在 `Base.metadata.create_all(bind=engine)` 之前添加导入：

```python
from app.modules.org.models import Department, Position
```

- [ ] **Step 3: 验证模型导入和表创建**

Run: `cd backend && python -c "from app.db.session import init_db; init_db(); print('Tables created successfully')"`
Expected: "Tables created successfully"（无报错）

- [ ] **Step 4: Commit**

```bash
git add backend/app/modules/org/models.py backend/app/db/session.py
git commit -m "feat: add Department and Position SQLAlchemy models"
```

---

### Task 8: 扩展 users 和 workspace_members 表

**Files:**
- Create: `backend/app/modules/org/alter_tables.py`
- Modify: `backend/app/models/user.py`
- Modify: `backend/app/models/workspace.py`

- [ ] **Step 1: 扩展 User 模型**

在 `backend/app/models/user.py` 的 `User` 类中添加字段：

```python
from sqlalchemy import Column, String, DateTime, BigInteger

# 在 existing fields after avatar 之后添加:
real_name = Column(String(50), nullable=True, comment="真实姓名")
mobile = Column(String(20), nullable=True, comment="手机号")
avatar_thumb = Column(String(500), nullable=True, comment="头像缩略图URL")
last_login_at = Column(DateTime, nullable=True, comment="最后登录时间")
last_login_ip = Column(String(45), nullable=True, comment="最后登录IP")
```

- [ ] **Step 2: 扩展 WorkspaceMember 模型**

在 `backend/app/models/workspace.py` 的 `WorkspaceMember` 类中添加字段：

```python
from sqlalchemy import Column, String, Integer, BigInteger, Date, Enum as SAEnum

# 在 role 字段后添加:
department_id = Column(BigInteger, ForeignKey("departments.id"), nullable=True, comment="所属部门ID")
position_id = Column(BigInteger, ForeignKey("positions.id"), nullable=True, comment="职位ID")
employee_no = Column(String(50), nullable=True, comment="工号")
real_name = Column(String(50), nullable=True, comment="真实姓名（冗余）")
mobile = Column(String(20), nullable=True, comment="手机号（冗余）")
join_date = Column(Date, nullable=True, comment="入职日期")
status = Column(String(20), default="active", nullable=False, comment="成员状态: active/leave/suspended")

department = relationship("Department", foreign_keys=[department_id], backref="members")
position = relationship("Position", foreign_keys=[position_id], backref="members")
```

- [ ] **Step 3: 创建 ALTER TABLE 迁移脚本**

`backend/app/modules/org/alter_tables.py`:
```python
"""执行表结构变更 — 添加新列"""
from sqlalchemy import text
from app.db.session import engine


def run_migration():
    conn = engine.connect()

    # users 表新增字段
    user_columns = [
        ("real_name", "VARCHAR(50) NULL COMMENT '真实姓名'"),
        ("mobile", "VARCHAR(20) NULL COMMENT '手机号'"),
        ("avatar_thumb", "VARCHAR(500) NULL COMMENT '头像缩略图'"),
        ("last_login_at", "DATETIME NULL COMMENT '最后登录时间'"),
        ("last_login_ip", "VARCHAR(45) NULL COMMENT '最后登录IP'"),
    ]
    for col_name, col_def in user_columns:
        try:
            conn.execute(text(
                f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col_name} {col_def}"
            ))
            print(f"[OK] users.{col_name} added")
        except Exception as e:
            # MySQL 5.7 不支持 IF NOT EXISTS for ADD COLUMN
            result = conn.execute(text(f"SHOW COLUMNS FROM users LIKE '{col_name}'"))
            if not result.fetchone():
                conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}"))
                print(f"[OK] users.{col_name} added")
            else:
                print(f"[SKIP] users.{col_name} already exists")

    # workspace_members 表新增字段
    member_columns = [
        ("department_id", "BIGINT NULL COMMENT '所属部门ID'"),
        ("position_id", "BIGINT NULL COMMENT '职位ID'"),
        ("employee_no", "VARCHAR(50) NULL COMMENT '工号'"),
        ("real_name", "VARCHAR(50) NULL COMMENT '真实姓名'"),
        ("mobile", "VARCHAR(20) NULL COMMENT '手机号'"),
        ("join_date", "DATE NULL COMMENT '入职日期'"),
        ("status", "VARCHAR(20) DEFAULT 'active' NOT NULL COMMENT '成员状态'"),
    ]
    for col_name, col_def in member_columns:
        try:
            conn.execute(text(
                f"ALTER TABLE workspace_members ADD COLUMN IF NOT EXISTS {col_name} {col_def}"
            ))
            print(f"[OK] workspace_members.{col_name} added")
        except Exception:
            result = conn.execute(text(f"SHOW COLUMNS FROM workspace_members LIKE '{col_name}'"))
            if not result.fetchone():
                conn.execute(text(f"ALTER TABLE workspace_members ADD COLUMN {col_name} {col_def}"))
                print(f"[OK] workspace_members.{col_name} added")
            else:
                print(f"[SKIP] workspace_members.{col_name} already exists")

    conn.commit()
    conn.close()
    print("\n[Migration complete]")


if __name__ == "__main__":
    run_migration()
```

- [ ] **Step 4: 执行迁移**

Run: `cd backend && python -m app.modules.org.alter_tables`
Expected: 各字段显示 [OK] 或 [SKIP]

- [ ] **Step 5: 验证字段存在**

Run: `cd backend && python -c "from app.models.user import User; print([c.name for c in User.__table__.columns])"`
Expected: 列表中包含 "real_name", "mobile", "avatar_thumb", "last_login_at", "last_login_ip"

- [ ] **Step 6: Commit**

```bash
git add backend/app/modules/org/alter_tables.py backend/app/models/user.py backend/app/models/workspace.py
git commit -m "feat: extend User and WorkspaceMember tables with org fields"
```

---

### Task 9: 部门 CRUD 操作

**Files:**
- Create: `backend/app/modules/org/crud.py`

**Interfaces:**
- Produces:
  - `DepartmentCRUD.get_tree(db, workspace_id) -> list[dict]` — 返回部门树
  - `DepartmentCRUD.create(db, workspace_id, name, parent_id, leader_id, sort_order) -> Department`
  - `DepartmentCRUD.update(db, dept_id, **kwargs) -> Department`
  - `DepartmentCRUD.delete(db, dept_id) -> Department` (软删除)
  - `PositionCRUD.get_list(db, workspace_id) -> list[Position]`
  - `PositionCRUD.create(db, workspace_id, name, sort_order) -> Position`
  - `PositionCRUD.delete(db, pos_id) -> Position`

- [ ] **Step 1: 编写 org/crud.py**

```python
"""组织架构模块 — CRUD 操作"""
from sqlalchemy.orm import Session
from app.modules.org.models import Department, Position
from app.core.exceptions import NotFoundException, BusinessException


class DepartmentCRUD:
    """部门 CRUD"""

    def get_tree(self, db: Session, workspace_id: int) -> list[dict]:
        """获取部门树 — 使用物化路径排序"""
        departments = (
            db.query(Department)
            .filter(
                Department.workspace_id == workspace_id,
                Department.is_active == True
            )
            .order_by(Department.sort_order, Department.id)
            .all()
        )
        return self._build_tree(departments, parent_id=None)

    def _build_tree(self, departments: list[Department], parent_id: int | None) -> list[dict]:
        """递归构建树形结构"""
        tree = []
        for dept in departments:
            if dept.parent_id == parent_id:
                node = {
                    "id": dept.id,
                    "name": dept.name,
                    "parent_id": dept.parent_id,
                    "leader_id": dept.leader_id,
                    "leader_name": dept.leader.real_name or dept.leader.nickname if dept.leader else None,
                    "sort_order": dept.sort_order,
                    "path": dept.path,
                    "member_count": len(dept.members) if dept.members else 0,
                    "children": self._build_tree(departments, parent_id=dept.id)
                }
                tree.append(node)
        return tree

    def get_by_id(self, db: Session, dept_id: int) -> Department:
        """按 ID 查询部门"""
        dept = db.query(Department).filter(
            Department.id == dept_id,
            Department.is_active == True
        ).first()
        if not dept:
            raise NotFoundException(resource="部门")
        return dept

    def create(
        self,
        db: Session,
        workspace_id: int,
        name: str,
        parent_id: int | None = None,
        leader_id: int | None = None,
        sort_order: int = 0
    ) -> Department:
        """创建部门"""
        # 验证父部门存在且属于同一 space
        if parent_id:
            parent = self.get_by_id(db, parent_id)
            if parent.workspace_id != workspace_id:
                raise BusinessException("父部门不属于当前工作空间")

        dept = Department(
            workspace_id=workspace_id,
            name=name,
            parent_id=parent_id,
            leader_id=leader_id,
            sort_order=sort_order,
            path=""  # 创建后通过 update_path 设置
        )
        db.add(dept)
        db.flush()  # 获取 dept.id

        # 设置物化路径
        if parent_id:
            parent_path = parent.path or ""
            dept.path = f"{parent_path}/{dept.id}"
        else:
            dept.path = f"/{dept.id}"

        db.commit()
        db.refresh(dept)
        return dept

    def update(self, db: Session, dept_id: int, **kwargs) -> Department:
        """更新部门"""
        dept = self.get_by_id(db, dept_id)

        # 如果变更了 parent_id，重新计算 path
        new_parent_id = kwargs.get("parent_id")
        if new_parent_id is not None and new_parent_id != dept.parent_id:
            if new_parent_id == dept_id:
                raise BusinessException("不能将部门设置为自己的子部门")
            if new_parent_id > 0:
                parent = self.get_by_id(db, new_parent_id)
                if parent.workspace_id != dept.workspace_id:
                    raise BusinessException("父部门不属于当前工作空间")
                dept.path = f"{parent.path}/{dept.id}"
            else:
                dept.path = f"/{dept.id}"

        for key, value in kwargs.items():
            if hasattr(dept, key):
                setattr(dept, key, value)

        db.commit()
        db.refresh(dept)
        return dept

    def delete(self, db: Session, dept_id: int) -> Department:
        """软删除部门及其子部门"""
        dept = self.get_by_id(db, dept_id)

        # 软删除所有子部门（物化路径前缀匹配）
        db.query(Department).filter(
            Department.workspace_id == dept.workspace_id,
            Department.path.like(f"{dept.path}/%"),
            Department.is_active == True
        ).update({"is_active": False})

        dept.is_active = False
        db.commit()
        db.refresh(dept)
        return dept


class PositionCRUD:
    """职位 CRUD"""

    def get_list(self, db: Session, workspace_id: int) -> list[Position]:
        return (
            db.query(Position)
            .filter(
                Position.workspace_id == workspace_id,
                Position.is_active == True
            )
            .order_by(Position.sort_order, Position.id)
            .all()
        )

    def get_by_id(self, db: Session, pos_id: int) -> Position:
        pos = db.query(Position).filter(
            Position.id == pos_id,
            Position.is_active == True
        ).first()
        if not pos:
            raise NotFoundException(resource="职位")
        return pos

    def create(self, db: Session, workspace_id: int, name: str, sort_order: int = 0) -> Position:
        pos = Position(workspace_id=workspace_id, name=name, sort_order=sort_order)
        db.add(pos)
        db.commit()
        db.refresh(pos)
        return pos

    def update(self, db: Session, pos_id: int, **kwargs) -> Position:
        pos = self.get_by_id(db, pos_id)
        for key, value in kwargs.items():
            if hasattr(pos, key):
                setattr(pos, key, value)
        db.commit()
        db.refresh(pos)
        return pos

    def delete(self, db: Session, pos_id: int) -> Position:
        pos = self.get_by_id(db, pos_id)
        pos.is_active = False
        db.commit()
        db.refresh(pos)
        return pos


# 单例
department_crud = DepartmentCRUD()
position_crud = PositionCRUD()
```

- [ ] **Step 2: 验证 CRUD 导入**

Run: `cd backend && python -c "from app.modules.org.crud import department_crud, position_crud; print('CRUD modules loaded')"`
Expected: "CRUD modules loaded"

- [ ] **Step 3: Commit**

```bash
git add backend/app/modules/org/crud.py
git commit -m "feat: add Department and Position CRUD with tree support"
```

---

### Task 10: 部门与职位 API 路由

**Files:**
- Create: `backend/app/modules/org/schemas.py`
- Create: `backend/app/modules/org/router.py`
- Modify: `backend/app/main.py` (注册 org 路由)

**Interfaces:**
- GET `/api/v1/org/departments?workspace_id=` — 部门树
- POST `/api/v1/org/departments` — 创建部门
- PUT `/api/v1/org/departments/{id}` — 更新部门
- DELETE `/api/v1/org/departments/{id}` — 删除部门
- GET `/api/v1/org/positions?workspace_id=` — 职位列表
- POST `/api/v1/org/positions` — 创建职位
- PUT `/api/v1/org/positions/{id}` — 更新职位
- DELETE `/api/v1/org/positions/{id}` — 删除职位
- GET `/api/v1/org/members?workspace_id=&department_id=` — 成员列表
- PUT `/api/v1/org/members/{id}` — 更新成员信息

- [ ] **Step 1: 编写 Pydantic Schemas**

`backend/app/modules/org/schemas.py`:
```python
"""组织架构模块 — Pydantic Schemas"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


# ---------- Department ----------
class DepartmentCreate(BaseModel):
    workspace_id: int = Field(..., description="工作空间ID")
    name: str = Field(..., min_length=1, max_length=100, description="部门名称")
    parent_id: Optional[int] = Field(None, description="父部门ID")
    leader_id: Optional[int] = Field(None, description="部门负责人ID")
    sort_order: int = Field(0, description="排序序号")


class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    parent_id: Optional[int] = None
    leader_id: Optional[int] = None
    sort_order: Optional[int] = None


class DepartmentResponse(BaseModel):
    id: int
    name: str
    parent_id: Optional[int]
    leader_id: Optional[int]
    leader_name: Optional[str] = None
    sort_order: int
    path: Optional[str] = None
    member_count: int = 0
    children: Optional[list["DepartmentResponse"]] = None
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}


# ---------- Position ----------
class PositionCreate(BaseModel):
    workspace_id: int
    name: str = Field(..., min_length=1, max_length=50)
    sort_order: int = 0


class PositionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    sort_order: Optional[int] = None


class PositionResponse(BaseModel):
    id: int
    workspace_id: int
    name: str
    sort_order: int
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}


# ---------- Member ----------
class MemberUpdate(BaseModel):
    department_id: Optional[int] = None
    position_id: Optional[int] = None
    employee_no: Optional[str] = Field(None, max_length=50)
    real_name: Optional[str] = Field(None, max_length=50)
    mobile: Optional[str] = Field(None, max_length=20)
    join_date: Optional[date] = None
    status: Optional[str] = None


class MemberResponse(BaseModel):
    id: int
    user_id: int
    workspace_id: int
    role: str
    department_id: Optional[int]
    department_name: Optional[str] = None
    position_id: Optional[int]
    position_name: Optional[str] = None
    employee_no: Optional[str] = None
    real_name: Optional[str] = None
    email: Optional[str] = None
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    mobile: Optional[str] = None
    join_date: Optional[str] = None
    status: str = "active"

    model_config = {"from_attributes": True}
```

- [ ] **Step 2: 编写 router.py**

`backend/app/modules/org/router.py`:
```python
"""组织架构模块 — API 路由"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import get_current_user
from app.core.permissions import get_workspace_member, require_workspace_role
from app.models.workspace import WorkspaceRole, WorkspaceMember
from app.models.user import User
from app.modules.org.crud import department_crud, position_crud
from app.modules.org.schemas import (
    DepartmentCreate, DepartmentUpdate, DepartmentResponse,
    PositionCreate, PositionUpdate, PositionResponse,
    MemberUpdate, MemberResponse,
)
from app.core.exceptions import NotFoundException, PermissionDeniedException

router = APIRouter()


# ==================== 部门管理 ====================

@router.get("/departments")
async def get_department_tree(
    workspace_id: int = Query(..., description="工作空间ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取部门树 — 需要有空间成员身份即可查看"""
    get_workspace_member(workspace_id, current_user.id, db)
    tree = department_crud.get_tree(db, workspace_id)
    return tree


@router.post("/departments", status_code=201)
async def create_department(
    dept_in: DepartmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建部门 — 需要 OWNER 或 ADMIN 权限"""
    require_workspace_role(dept_in.workspace_id, current_user.id, [WorkspaceRole.OWNER, WorkspaceRole.ADMIN], db)
    dept = department_crud.create(
        db,
        workspace_id=dept_in.workspace_id,
        name=dept_in.name,
        parent_id=dept_in.parent_id,
        leader_id=dept_in.leader_id,
        sort_order=dept_in.sort_order
    )
    return DepartmentResponse.model_validate(dept)


@router.put("/departments/{dept_id}")
async def update_department(
    dept_id: int,
    dept_in: DepartmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新部门"""
    dept = department_crud.get_by_id(db, dept_id)
    require_workspace_role(dept.workspace_id, current_user.id, [WorkspaceRole.OWNER, WorkspaceRole.ADMIN], db)
    updated = department_crud.update(db, dept_id, **dept_in.model_dump(exclude_none=True))
    return DepartmentResponse.model_validate(updated)


@router.delete("/departments/{dept_id}")
async def delete_department(
    dept_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除部门 — OWNER 或 ADMIN"""
    dept = department_crud.get_by_id(db, dept_id)
    require_workspace_role(dept.workspace_id, current_user.id, [WorkspaceRole.OWNER, WorkspaceRole.ADMIN], db)
    department_crud.delete(db, dept_id)
    return {"message": "部门已删除"}


# ==================== 职位管理 ====================

@router.get("/positions")
async def get_positions(
    workspace_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取职位列表"""
    get_workspace_member(workspace_id, current_user.id, db)
    positions = position_crud.get_list(db, workspace_id)
    return [PositionResponse.model_validate(p) for p in positions]


@router.post("/positions", status_code=201)
async def create_position(
    pos_in: PositionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建职位 — OWNER 或 ADMIN"""
    require_workspace_role(pos_in.workspace_id, current_user.id, [WorkspaceRole.OWNER, WorkspaceRole.ADMIN], db)
    pos = position_crud.create(db, pos_in.workspace_id, pos_in.name, pos_in.sort_order)
    return PositionResponse.model_validate(pos)


@router.put("/positions/{pos_id}")
async def update_position(
    pos_id: int,
    pos_in: PositionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新职位"""
    pos = position_crud.get_by_id(db, pos_id)
    require_workspace_role(pos.workspace_id, current_user.id, [WorkspaceRole.OWNER, WorkspaceRole.ADMIN], db)
    updated = position_crud.update(db, pos_id, **pos_in.model_dump(exclude_none=True))
    return PositionResponse.model_validate(updated)


@router.delete("/positions/{pos_id}")
async def delete_position(
    pos_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除职位"""
    pos = position_crud.get_by_id(db, pos_id)
    require_workspace_role(pos.workspace_id, current_user.id, [WorkspaceRole.OWNER, WorkspaceRole.ADMIN], db)
    position_crud.delete(db, pos_id)
    return {"message": "职位已删除"}


# ==================== 成员管理 ====================

@router.get("/members")
async def get_members(
    workspace_id: int = Query(...),
    department_id: int = Query(None, description="按部门筛选"),
    keyword: str = Query(None, description="姓名/邮箱/工号搜索"),
    status: str = Query(None, description="成员状态: active/leave/suspended"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取成员花名册"""
    get_workspace_member(workspace_id, current_user.id, db)

    query = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.is_active == True
    )

    if department_id:
        query = query.filter(WorkspaceMember.department_id == department_id)
    if status:
        query = query.filter(WorkspaceMember.status == status)
    if keyword:
        query = query.filter(
            (WorkspaceMember.real_name.ilike(f"%{keyword}%")) |
            (WorkspaceMember.employee_no.ilike(f"%{keyword}%"))
        )

    total = query.count()
    members = query.offset((page - 1) * page_size).limit(page_size).all()

    result = []
    for m in members:
        data = MemberResponse.model_validate(m)
        data.email = m.user.email if m.user else None
        data.nickname = m.user.nickname if m.user else None
        data.avatar = m.user.avatar if m.user else None
        if m.department:
            data.department_name = m.department.name
        if m.position:
            data.position_name = m.position.name
        result.append(data)

    return {
        "items": [item.model_dump() for item in result],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0
    }


@router.put("/members/{member_id}")
async def update_member(
    member_id: int,
    member_in: MemberUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新成员信息 — OWNER 或 ADMIN"""
    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.id == member_id,
        WorkspaceMember.is_active == True
    ).first()
    if not member:
        raise NotFoundException(resource="成员")

    require_workspace_role(member.workspace_id, current_user.id, [WorkspaceRole.OWNER, WorkspaceRole.ADMIN], db)

    for key, value in member_in.model_dump(exclude_none=True).items():
        setattr(member, key, value)

    db.commit()
    db.refresh(member)
    return {"message": "成员信息已更新"}
```

- [ ] **Step 3: 注册 org 路由到 main.py**

在 `backend/app/main.py` 的路由注册区域添加：

```python
from app.modules.org.router import router as org_router
app.include_router(org_router, prefix="/api/v1/org")
```

- [ ] **Step 4: 更新 permissions.py 添加辅助函数**

在 `backend/app/core/permissions.py` 末尾添加（检查是否已存在 `require_workspace_role`）：

```python
def require_workspace_role(workspace_id: int, user_id: int, roles: list, db) -> WorkspaceMember:
    """要求指定角色 — 如果没有权限则抛出异常"""
    member = get_workspace_member(workspace_id, user_id, db)
    if member.role not in roles:
        raise PermissionDeniedException(detail=f"需要 {roles} 权限")
    return member
```

- [ ] **Step 5: 启动服务并验证路由**

Run: `cd backend && python -c "from app.main import app; routes = [r.path for r in app.routes]; print('\n'.join(r for r in routes if 'org' in r))"`
Expected: 能看到 /api/v1/org/departments, /api/v1/org/positions, /api/v1/org/members 等路由

- [ ] **Step 6: Commit**

```bash
git add backend/app/modules/org/schemas.py backend/app/modules/org/router.py backend/app/main.py backend/app/core/permissions.py
git commit -m "feat: add Department, Position, and Member management APIs"
```

---

### Task 11: 审计日志中间件

**Files:**
- Create: `backend/app/middleware/audit_log.py`
- Create: `backend/app/modules/org/models.py` (追加 AuditLog 模型)
- Modify: `backend/app/main.py`

**Interfaces:**
- 新增模型: `AuditLog(id, workspace_id, user_id, module, action, target_type, target_id, detail, ip_address, user_agent, created_at)`
- 中间件: 拦截所有写操作 (POST/PUT/PATCH/DELETE)，自动记录审计日志

- [ ] **Step 1: 添加 AuditLog 模型**

在 `backend/app/modules/org/models.py` 末尾追加：

```python
from sqlalchemy import Column, String, Text, JSON
from sqlalchemy.dialects.mysql import LONGTEXT

class AuditLog(BaseModel):
    """全平台审计日志"""
    __tablename__ = "audit_logs"
    __table_args__ = {'extend_existing': True}

    workspace_id = Column(BigInteger, ForeignKey("workspaces.id"), nullable=True, comment="所属空间（NULL=系统级）")
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=True, comment="操作人ID（NULL=系统操作）")
    module = Column(String(50), nullable=False, comment="模块: task/im/approval/org/...")
    action = Column(String(50), nullable=False, comment="操作: create/update/delete/login/export/...")
    target_type = Column(String(50), nullable=True, comment="目标类型: task/department/member/...")
    target_id = Column(BigInteger, nullable=True, comment="目标ID")
    detail = Column(JSON, nullable=True, comment="变更详情")
    ip_address = Column(String(45), nullable=True, comment="操作IP")
    user_agent = Column(String(500), nullable=True, comment="用户设备信息")

    user = relationship("User", foreign_keys=[user_id], backref="audit_logs")
    workspace = relationship("Workspace", foreign_keys=[workspace_id], backref="audit_logs")
```

- [ ] **Step 2: 编写审计日志中间件**

`backend/app/middleware/audit_log.py`:
```python
"""审计日志中间件 — 自动记录所有写操作"""
import json
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.security import decode_token
from app.db.session import get_db_session


# 不需要记录的路径前缀
SKIP_PREFIXES = ["/docs", "/redoc", "/openapi.json", "/health", "/uploads"]


class AuditLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        response = await call_next(request)

        # 只记录写操作
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            path = request.url.path
            if not any(path.startswith(p) for p in SKIP_PREFIXES):
                self._log_async(request, response, start_time)

        return response

    def _log_async(self, request: Request, response, start_time: float):
        """异步记录审计日志 — 使用 Celery 任务或同步写入"""
        try:
            # 提取用户信息
            user_id = None
            workspace_id = None
            auth_header = request.headers.get("authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header.replace("Bearer ", "")
                payload = decode_token(token)
                if payload:
                    user_id = payload.get("user_id")

            # 提取模块和目标
            path = request.url.path
            # /api/v1/org/departments → module=org, target_type=department
            # /api/v1/tasks/123 → module=task, target_type=task
            parts = [p for p in path.split("/") if p]
            module = "system"
            target_type = None
            target_id = None

            if "api" in parts and "v1" in parts:
                idx = parts.index("v1")
                if len(parts) > idx + 1:
                    module = parts[idx + 1]  # org, task, auth, etc.
                if len(parts) > idx + 2:
                    target_type = parts[idx + 2]  # departments, tasks, etc.
                if len(parts) > idx + 3 and parts[idx + 3].isdigit():
                    target_id = int(parts[idx + 3])

            # 获取 workspace_id（从 query params）
            workspace_id = request.query_params.get("workspace_id")

            # 同步写入数据库
            db = get_db_session()
            try:
                from app.modules.org.models import AuditLog
                log = AuditLog(
                    workspace_id=int(workspace_id) if workspace_id else None,
                    user_id=user_id,
                    module=module,
                    action=request.method.lower(),
                    target_type=target_type,
                    target_id=target_id,
                    detail={
                        "method": request.method,
                        "path": path,
                        "status_code": response.status_code,
                        "duration_ms": round((time.time() - start_time) * 1000, 2)
                    },
                    ip_address=request.client.host if request.client else None,
                    user_agent=request.headers.get("user-agent", "")
                )
                db.add(log)
                db.commit()
            except Exception:
                pass  # 审计日志写入失败不影响主业务
            finally:
                db.close()

        except Exception:
            pass  # 审计日志失败静默处理
```

- [ ] **Step 3: 注册审计日志中间件**

在 `backend/app/main.py` 中，在响应中间件之后添加：

```python
from app.middleware.audit_log import AuditLogMiddleware
app.add_middleware(AuditLogMiddleware)
```

- [ ] **Step 4: 验证审计日志表创建**

Run: `cd backend && python -c "from app.db.session import init_db; init_db(); print('Audit log table ready')"`
Expected: "Audit log table ready"

- [ ] **Step 5: Commit**

```bash
git add backend/app/middleware/audit_log.py backend/app/modules/org/models.py backend/app/main.py
git commit -m "feat: add audit log middleware and model"
```

---

### Task 12: 前端 MainLayout 改造

**Files:**
- Create: `frontend/src/components/layout/Sidebar.vue`
- Create: `frontend/src/components/layout/TopBar.vue`
- Modify: `frontend/src/components/layouts/MainLayout.vue`

**Interfaces:**
- Sidebar: 接收 `menuItems` prop，支持折叠/展开
- TopBar: 包含搜索框、通知铃铛占位、用户下拉菜单
- MainLayout: 组合 Sidebar + TopBar + `<router-view>`

- [ ] **Step 1: 编写 Sidebar.vue**

```vue
<template>
  <el-menu
    :default-active="activeMenu"
    :collapse="isCollapse"
    :router="true"
    background-color="#304156"
    text-color="#bfcbd9"
    active-text-color="#409EFF"
    class="sidebar-menu"
  >
    <div class="sidebar-logo">
      <img src="@/assets/logo.png" v-if="!isCollapse" class="logo-img" />
      <span v-if="!isCollapse" class="logo-text">企业协作平台</span>
      <span v-else class="logo-text-mini">企</span>
    </div>

    <template v-for="item in menuItems" :key="item.path">
      <!-- 单层菜单 -->
      <el-menu-item v-if="!item.children" :index="item.path">
        <el-icon><component :is="item.icon" /></el-icon>
        <template #title>{{ item.title }}</template>
      </el-menu-item>

      <!-- 子菜单 -->
      <el-sub-menu v-else :index="item.path">
        <template #title>
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.title }}</span>
        </template>
        <el-menu-item
          v-for="child in item.children"
          :key="child.path"
          :index="child.path"
        >
          {{ child.title }}
        </el-menu-item>
      </el-sub-menu>
    </template>
  </el-menu>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

defineProps({
  menuItems: { type: Array, required: true },
  isCollapse: { type: Boolean, default: false }
})

const route = useRoute()
const activeMenu = computed(() => route.path)
</script>

<style scoped>
.sidebar-menu {
  height: 100%;
  border-right: none;
}
.sidebar-logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 18px;
  font-weight: bold;
  border-bottom: 1px solid rgba(255,255,255,0.1);
}
.logo-img {
  width: 32px;
  height: 32px;
  margin-right: 8px;
}
.logo-text-mini {
  font-size: 22px;
}
</style>
```

- [ ] **Step 2: 编写 TopBar.vue**

```vue
<template>
  <div class="topbar">
    <div class="topbar-left">
      <el-icon
        class="collapse-btn"
        @click="$emit('toggle-collapse')"
        :size="20"
      >
        <Fold v-if="!isCollapse" />
        <Expand v-else />
      </el-icon>
      <span class="page-title">{{ title }}</span>
    </div>

    <div class="topbar-right">
      <el-badge :value="unreadCount" :hidden="unreadCount === 0" class="notification-badge">
        <el-icon :size="20" class="bell-icon"><Bell /></el-icon>
      </el-badge>

      <el-dropdown trigger="click" @command="handleCommand">
        <span class="user-info">
          <el-avatar :size="32" :src="userAvatar" />
          <span class="user-name">{{ userName }}</span>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="profile">个人信息</el-dropdown-item>
            <el-dropdown-item command="settings">设置</el-dropdown-item>
            <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { Fold, Expand, Bell } from '@element-plus/icons-vue'

defineProps({
  isCollapse: { type: Boolean, default: false },
  title: { type: String, default: '' },
  unreadCount: { type: Number, default: 0 }
})

defineEmits(['toggle-collapse'])

const router = useRouter()
const userStore = useUserStore()

const userName = userStore.userInfo?.nickname || '用户'
const userAvatar = userStore.userInfo?.avatar || ''

function handleCommand(command) {
  if (command === 'profile') router.push('/profile')
  else if (command === 'logout') userStore.logout()
}
</script>

<style scoped>
.topbar {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}
.topbar-left { display: flex; align-items: center; gap: 12px; }
.collapse-btn { cursor: pointer; }
.page-title { font-size: 16px; font-weight: 500; }
.topbar-right { display: flex; align-items: center; gap: 20px; }
.notification-badge { cursor: pointer; }
.bell-icon { cursor: pointer; }
.user-info { display: flex; align-items: center; gap: 8px; cursor: pointer; }
.user-name { font-size: 14px; }
</style>
```

- [ ] **Step 3: 改造 MainLayout.vue**

替换原 MainLayout.vue 的模板部分，使用新的 Sidebar + TopBar：

```vue
<template>
  <div class="main-layout" :class="{ 'sidebar-collapsed': isCollapse }">
    <div class="sidebar-container" :style="{ width: isCollapse ? '64px' : '220px' }">
      <Sidebar :menu-items="menuItems" :is-collapse="isCollapse" />
    </div>
    <div class="main-container">
      <TopBar
        :is-collapse="isCollapse"
        :title="pageTitle"
        @toggle-collapse="isCollapse = !isCollapse"
      />
      <div class="main-content">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import Sidebar from './Sidebar.vue'
import TopBar from './TopBar.vue'

const route = useRoute()
const isCollapse = ref(false)
const pageTitle = computed(() => route.meta?.title || '首页')

const menuItems = [
  { path: '/dashboard', title: '工作台', icon: 'Odometer' },
  { path: '/tasks', title: '任务', icon: 'List' },
  { path: '/calendar', title: '日程', icon: 'Calendar', children: [] },
  {
    path: '/org',
    title: '组织',
    icon: 'OfficeBuilding',
    children: [
      { path: '/org/departments', title: '部门管理' },
      { path: '/org/members', title: '成员花名册' }
    ]
  },
  { path: '/statistics', title: '统计', icon: 'DataAnalysis' },
  { path: '/workspaces', title: '工作空间', icon: 'Grid' },
]
</script>

<style scoped>
.main-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}
.sidebar-container {
  transition: width 0.3s;
  overflow: hidden;
  flex-shrink: 0;
}
.main-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.main-content {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  background: #f5f7fa;
}
</style>
```

- [ ] **Step 4: 验证前端编译**

Run: `cd frontend && npm run build 2>&1 | tail -20`
Expected: 构建成功（"Build complete" 或 exit code 0）

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/layout/Sidebar.vue frontend/src/components/layout/TopBar.vue frontend/src/components/layouts/MainLayout.vue
git commit -m "feat: redesign MainLayout with Sidebar and TopBar"
```

---

### Task 13: 前端组织架构页面

**Files:**
- Create: `frontend/src/views/org/DeptManage.vue`
- Create: `frontend/src/views/org/MemberRoster.vue`
- Create: `frontend/src/components/org/DeptTree.vue`
- Create: `frontend/src/components/org/DeptDialog.vue`
- Create: `frontend/src/components/org/MemberTable.vue`
- Create: `frontend/src/components/org/MemberEditDialog.vue`
- Modify: `frontend/src/router/routes/org.js`
- Modify: `frontend/src/api/org.js`
- Modify: `frontend/src/stores/org.js`
- Modify: `frontend/src/router/routes.js` (挂载 org 路由)

**Interfaces:**
- `/org/departments` — 部门管理页面（树形 CRUD）
- `/org/members` — 成员花名册（分页表格+筛选）

- [ ] **Step 1: 编写 API 层**

`frontend/src/api/org.js`:
```js
import request from './request'

export function getDeptTree(workspaceId) {
  return request.get('/org/departments', { params: { workspace_id: workspaceId } })
}

export function createDept(data) {
  return request.post('/org/departments', data)
}

export function updateDept(id, data) {
  return request.put(`/org/departments/${id}`, data)
}

export function deleteDept(id) {
  return request.delete(`/org/departments/${id}`)
}

export function getPositions(workspaceId) {
  return request.get('/org/positions', { params: { workspace_id: workspaceId } })
}

export function createPosition(data) {
  return request.post('/org/positions', data)
}

export function updatePosition(id, data) {
  return request.put(`/org/positions/${id}`, data)
}

export function deletePosition(id) {
  return request.delete(`/org/positions/${id}`)
}

export function getMembers(params) {
  return request.get('/org/members', { params })
}

export function updateMember(id, data) {
  return request.put(`/org/members/${id}`, data)
}
```

- [ ] **Step 2: 编写路由**

`frontend/src/router/routes/org.js`:
```js
export default [
  {
    path: '/org/departments',
    name: 'OrgDepartments',
    component: () => import('@/views/org/DeptManage.vue'),
    meta: { title: '部门管理', requiresAuth: true }
  },
  {
    path: '/org/members',
    name: 'OrgMembers',
    component: () => import('@/views/org/MemberRoster.vue'),
    meta: { title: '成员花名册', requiresAuth: true }
  }
]
```

- [ ] **Step 3: 编写 DeptTree 组件**

`frontend/src/components/org/DeptTree.vue`:
```vue
<template>
  <div class="dept-tree">
    <div class="dept-tree-header">
      <span>部门结构</span>
      <el-button type="primary" size="small" @click="$emit('add', null)">+ 添加部门</el-button>
    </div>
    <el-tree
      :data="treeData"
      :props="{ children: 'children', label: 'name' }"
      node-key="id"
      default-expand-all
      highlight-current
      @node-click="handleNodeClick"
    >
      <template #default="{ data }">
        <span class="dept-node">
          <span>{{ data.name }}</span>
          <span class="dept-count">{{ data.member_count }}人</span>
          <span class="dept-actions">
            <el-button link type="primary" size="small" @click.stop="$emit('add', data)">+子部门</el-button>
            <el-button link type="primary" size="small" @click.stop="$emit('edit', data)">编辑</el-button>
            <el-button link type="danger" size="small" @click.stop="$emit('delete', data)">删除</el-button>
          </span>
        </span>
      </template>
    </el-tree>
  </div>
</template>

<script setup>
defineProps({ treeData: { type: Array, default: () => [] } })
defineEmits(['add', 'edit', 'delete', 'node-click'])

function handleNodeClick(data) {
  // 透传给父组件
}
</script>

<style scoped>
.dept-tree { padding: 10px 0; }
.dept-tree-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 10px; padding: 0 8px;
}
.dept-node { display: flex; align-items: center; gap: 8px; flex: 1; }
.dept-count { color: #909399; font-size: 12px; }
.dept-actions { margin-left: auto; }
</style>
```

- [ ] **Step 4: 编写 DeptManage.vue 页面**

`frontend/src/views/org/DeptManage.vue`:
```vue
<template>
  <div class="dept-manage">
    <el-card>
      <DeptTree
        :tree-data="treeData"
        @add="handleAdd"
        @edit="handleEdit"
        @delete="handleDelete"
      />
    </el-card>

    <DeptDialog
      v-model:visible="dialogVisible"
      :dept="editingDept"
      :parent-dept="parentDept"
      :leaders="leaderOptions"
      @submit="handleSubmit"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import DeptTree from '@/components/org/DeptTree.vue'
import DeptDialog from '@/components/org/DeptDialog.vue'
import { getDeptTree, createDept, updateDept, deleteDept } from '@/api/org'
import { useWorkspaceStore } from '@/stores/workspaceStore'

const workspaceStore = useWorkspaceStore()
const workspaceId = ref(workspaceStore.currentWorkspaceId)

const treeData = ref([])
const dialogVisible = ref(false)
const editingDept = ref(null)
const parentDept = ref(null)
const leaderOptions = ref([])

async function loadTree() {
  const res = await getDeptTree(workspaceId.value)
  treeData.value = res.data.data || res.data || []
}

function handleAdd(parent) {
  editingDept.value = null
  parentDept.value = parent
  dialogVisible.value = true
}

function handleEdit(dept) {
  editingDept.value = dept
  parentDept.value = null
  dialogVisible.value = true
}

async function handleDelete(dept) {
  await ElMessageBox.confirm(`确定删除部门"${dept.name}"及其子部门？`, '确认', {
    type: 'warning'
  })
  await deleteDept(dept.id)
  ElMessage.success('部门已删除')
  await loadTree()
}

async function handleSubmit(formData) {
  if (editingDept.value) {
    await updateDept(editingDept.value.id, formData)
    ElMessage.success('部门已更新')
  } else {
    await createDept({ ...formData, workspace_id: workspaceId.value })
    ElMessage.success('部门已创建')
  }
  dialogVisible.value = false
  await loadTree()
}

onMounted(() => { loadTree() })
</script>
```

- [ ] **Step 5: 编写 MemberRoster.vue 页面**

`frontend/src/views/org/MemberRoster.vue`:
```vue
<template>
  <div class="member-roster">
    <el-card>
      <!-- 筛选栏 -->
      <div class="filter-bar">
        <el-select v-model="filters.department_id" placeholder="按部门筛选" clearable>
          <el-option v-for="d in deptList" :key="d.id" :label="d.name" :value="d.id" />
        </el-select>
        <el-input
          v-model="filters.keyword"
          placeholder="搜索姓名/邮箱/工号"
          style="width: 250px"
          clearable
        />
        <el-select v-model="filters.status" placeholder="成员状态" clearable style="width: 120px">
          <el-option label="在职" value="active" />
          <el-option label="已离职" value="leave" />
          <el-option label="已停用" value="suspended" />
        </el-select>
        <el-button type="primary" @click="loadData">查询</el-button>
      </div>

      <!-- 表格 -->
      <el-table :data="memberList" stripe v-loading="loading" style="margin-top: 16px">
        <el-table-column prop="real_name" label="姓名" width="120" />
        <el-table-column prop="nickname" label="昵称" width="120" />
        <el-table-column prop="email" label="邮箱" min-width="200" />
        <el-table-column prop="employee_no" label="工号" width="120" />
        <el-table-column prop="department_name" label="部门" width="120" />
        <el-table-column prop="position_name" label="职位" width="120" />
        <el-table-column prop="role" label="空间角色" width="100">
          <template #default="{ row }">
            <el-tag :type="roleType(row.role)" size="small">{{ roleLabel(row.role) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
              {{ row.status === 'active' ? '在职' : row.status === 'leave' ? '离职' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        layout="total, prev, pager, next"
        @current-change="loadData"
      />
    </el-card>

    <MemberEditDialog
      v-model:visible="editVisible"
      :member="editingMember"
      :dept-list="deptList"
      :position-list="positionList"
      @submit="handleMemberUpdate"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getDeptTree, getPositions, getMembers, updateMember } from '@/api/org'
import { useWorkspaceStore } from '@/stores/workspaceStore'
import MemberEditDialog from '@/components/org/MemberEditDialog.vue'

const workspaceStore = useWorkspaceStore()
const workspaceId = ref(workspaceStore.currentWorkspaceId)

const filters = reactive({ department_id: null, keyword: '', status: 'active' })
const pagination = reactive({ page: 1, pageSize: 20, total: 0 })
const memberList = ref([])
const deptList = ref([])
const positionList = ref([])
const loading = ref(false)
const editVisible = ref(false)
const editingMember = ref(null)

async function loadData() {
  loading.value = true
  try {
    const res = await getMembers({
      workspace_id: workspaceId.value,
      ...filters,
      page: pagination.page,
      page_size: pagination.pageSize
    })
    const data = res.data.data || res.data
    memberList.value = data.items || data
    pagination.total = data.total || 0
  } finally {
    loading.value = false
  }
}

function openEdit(member) {
  editingMember.value = member
  editVisible.value = true
}

async function handleMemberUpdate(formData) {
  await updateMember(editingMember.value.id, formData)
  ElMessage.success('成员信息已更新')
  editVisible.value = false
  await loadData()
}

function roleType(role) { return role === 'owner' ? 'danger' : role === 'admin' ? 'warning' : 'info' }
function roleLabel(role) { return { owner: '拥有者', admin: '管理员', member: '成员' }[role] || role }

onMounted(async () => {
  const deptRes = await getDeptTree(workspaceId.value)
  deptList.value = deptRes.data.data || deptRes.data || []
  const posRes = await getPositions(workspaceId.value)
  positionList.value = posRes.data.data || posRes.data || []
  await loadData()
})
</script>

<style scoped>
.filter-bar { display: flex; gap: 12px; flex-wrap: wrap; }
</style>
```

- [ ] **Step 5a: 编写 DeptDialog.vue**

`frontend/src/components/org/DeptDialog.vue`:
```vue
<template>
  <el-dialog
    :model-value="visible"
    :title="dept ? '编辑部门' : (parentDept ? `在「${parentDept.name}」下创建子部门` : '创建根部门')"
    width="480px"
    @update:model-value="$emit('update:visible', $event)"
    @close="resetForm"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
      <el-form-item label="部门名称" prop="name">
        <el-input v-model="form.name" placeholder="请输入部门名称" maxlength="100" />
      </el-form-item>
      <el-form-item label="负责人" prop="leader_id">
        <el-select v-model="form.leader_id" placeholder="请选择负责人" clearable filterable>
          <el-option
            v-for="user in leaders"
            :key="user.id"
            :label="user.real_name || user.nickname"
            :value="user.id"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="排序" prop="sort_order">
        <el-input-number v-model="form.sort_order" :min="0" :max="999" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="$emit('update:visible', false)">取消</el-button>
      <el-button type="primary" @click="submit" :loading="submitting">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'

const props = defineProps({
  visible: Boolean,
  dept: Object,
  parentDept: Object,
  leaders: { type: Array, default: () => [] }
})
const emit = defineEmits(['update:visible', 'submit'])

const formRef = ref(null)
const submitting = ref(false)
const form = reactive({ name: '', leader_id: null, sort_order: 0, parent_id: null })

const rules = {
  name: [{ required: true, message: '请输入部门名称', trigger: 'blur' }]
}

watch(() => props.visible, (val) => {
  if (val) {
    form.name = props.dept?.name || ''
    form.leader_id = props.dept?.leader_id || null
    form.sort_order = props.dept?.sort_order || 0
    form.parent_id = props.parentDept?.id || null
  }
})

function resetForm() {
  formRef.value?.resetFields()
}

async function submit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    await emit('submit', { ...form })
  } finally {
    submitting.value = false
  }
}
</script>
```

- [ ] **Step 5b: 编写 MemberEditDialog.vue**

`frontend/src/components/org/MemberEditDialog.vue`:
```vue
<template>
  <el-dialog
    :model-value="visible"
    title="编辑成员信息"
    width="480px"
    @update:model-value="$emit('update:visible', $event)"
  >
    <el-form :model="form" label-width="80px">
      <el-form-item label="部门">
        <el-tree-select
          v-model="form.department_id"
          :data="deptList"
          :props="{ children: 'children', label: 'name', value: 'id' }"
          placeholder="请选择部门"
          clearable
          check-strictly
        />
      </el-form-item>
      <el-form-item label="职位">
        <el-select v-model="form.position_id" placeholder="请选择职位" clearable>
          <el-option v-for="p in positionList" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="工号">
        <el-input v-model="form.employee_no" placeholder="请输入工号" maxlength="50" />
      </el-form-item>
      <el-form-item label="手机号">
        <el-input v-model="form.mobile" placeholder="请输入手机号" maxlength="20" />
      </el-form-item>
      <el-form-item label="状态">
        <el-select v-model="form.status">
          <el-option label="在职" value="active" />
          <el-option label="离职" value="leave" />
          <el-option label="停用" value="suspended" />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="$emit('update:visible', false)">取消</el-button>
      <el-button type="primary" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, watch } from 'vue'

const props = defineProps({
  visible: Boolean,
  member: Object,
  deptList: { type: Array, default: () => [] },
  positionList: { type: Array, default: () => [] }
})
const emit = defineEmits(['update:visible', 'submit'])

const form = reactive({
  department_id: null,
  position_id: null,
  employee_no: '',
  mobile: '',
  status: 'active'
})

watch(() => props.visible, (val) => {
  if (val && props.member) {
    form.department_id = props.member.department_id || null
    form.position_id = props.member.position_id || null
    form.employee_no = props.member.employee_no || ''
    form.mobile = props.member.mobile || ''
    form.status = props.member.status || 'active'
  }
})

function submit() {
  emit('submit', { ...form })
}
</script>
```

- [ ] **Step 6: 注册前端路由**

在 `frontend/src/router/routes.js` 中导入 org 路由并合并：

```js
import orgRoutes from './routes/org'
// 在 routes 数组中添加: ...orgRoutes
```

- [ ] **Step 7: 验证前端编译**

Run: `cd frontend && npm run build 2>&1 | tail -10`
Expected: 构建成功

- [ ] **Step 8: Commit**

```bash
git add frontend/src/views/org/ frontend/src/components/org/ frontend/src/router/routes/org.js frontend/src/router/routes.js frontend/src/api/org.js frontend/src/stores/org.js
git commit -m "feat: add organization management pages (DeptTree + MemberRoster)"
```

---

### Task 14: Docker 容器化

**Files:**
- Create: `backend/Dockerfile`
- Create: `docker-compose.yml` (项目根目录)
- Create: `.dockerignore`

- [ ] **Step 1: 编写 backend/Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc default-libmysqlclient-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 8001

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
```

- [ ] **Step 2: 编写 docker-compose.yml**

```yaml
version: '3.8'

services:
  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: root123456
      MYSQL_DATABASE: personal_task_system
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
    command: --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  backend:
    build: ./backend
    ports:
      - "8001:8001"
    environment:
      DATABASE_URL: mysql+pymysql://root:root123456@mysql:3306/personal_task_system
      REDIS_URL: redis://redis:6379/0
      EMAIL_HOST: ${EMAIL_HOST}
      EMAIL_PORT: ${EMAIL_PORT}
      EMAIL_USERNAME: ${EMAIL_USERNAME}
      EMAIL_PASSWORD: ${EMAIL_PASSWORD}
      EMAIL_FROM: ${EMAIL_FROM}
      SECRET_KEY: ${SECRET_KEY:-dev-secret-key-change-in-production}
    depends_on:
      - mysql
      - redis
    volumes:
      - ./backend/uploads:/app/uploads

volumes:
  mysql_data:
  redis_data:
```

- [ ] **Step 3: 创建 .dockerignore**

```
backend/.venv
backend/__pycache__
backend/**/*.pyc
frontend/node_modules
frontend/dist
.git
```

- [ ] **Step 4: 验证 Docker 构建**

Run: `docker compose build backend 2>&1 | tail -5`
Expected: 构建成功（或跳过如果有 Docker 不可用）

- [ ] **Step 5: Commit**

```bash
git add backend/Dockerfile docker-compose.yml .dockerignore
git commit -m "feat: add Docker and docker-compose configuration"
```

---

### Task 15: 集成测试与回归验证

**Files:**
- Create: `backend/test_integration_phase1.py`

- [ ] **Step 1: 编写集成测试脚本**

`backend/test_integration_phase1.py`:
```python
"""Phase 1 集成测试 — 验证所有功能正常"""
import sys


def test_imports():
    """验证所有模块导入正常"""
    modules = [
        "app.main",
        "app.core.config",
        "app.core.security",
        "app.core.exceptions",
        "app.db.session",
        "app.db.redis_client",
        "app.modules.task.models",
        "app.modules.task.router",
        "app.modules.org.models",
        "app.modules.org.crud",
        "app.modules.org.router",
        "app.modules.org.schemas",
        "app.middleware.response_handler",
        "app.middleware.audit_log",
        "app.shared.response",
    ]
    passed = 0
    failed = 0
    for mod in modules:
        try:
            __import__(mod)
            print(f"  ✅ {mod}")
            passed += 1
        except Exception as e:
            print(f"  ❌ {mod}: {e}")
            failed += 1
    return passed, failed


def test_response_utils():
    """验证统一响应工具"""
    from app.shared.response import success_response, error_response, paginated_response

    assert success_response({"x": 1})["code"] == 0
    assert error_response(40401, "Not found")["code"] == 40401
    page = paginated_response([], 100, 1, 20)
    assert page["data"]["total_pages"] == 5
    print("  ✅ response_utils")


def test_exceptions():
    """验证异常类"""
    from app.core.exceptions import (
        NotFoundException, PermissionDeniedException, UnauthorizedException
    )
    e1 = NotFoundException(resource="部门")
    assert e1.code == 40401
    assert "部门" in e1.message

    e2 = PermissionDeniedException()
    assert e2.code == 40301

    e3 = UnauthorizedException()
    assert e3.code == 40101
    print("  ✅ exceptions")


def test_dept_model():
    """验证 Department 模型定义"""
    from app.modules.org.models import Department, Position, AuditLog
    assert Department.__tablename__ == "departments"
    assert Position.__tablename__ == "positions"
    assert AuditLog.__tablename__ == "audit_logs"
    print("  ✅ org models")


def test_api_routes():
    """验证 API 路由注册"""
    from app.main import app
    routes = [r.path for r in app.routes]

    # 检查 org 路由
    org_routes = [r for r in routes if '/org/' in r or '/org' in r]
    print(f"  Org routes found: {len(org_routes)}")
    for r in sorted(org_routes):
        print(f"    {r}")

    # 检查 task 路由保留
    task_routes = [r for r in routes if '/tasks' in r]
    print(f"  Task routes found: {len(task_routes)}")

    # 检查 auth 路由
    auth_routes = [r for r in routes if '/auth' in r]
    print(f"  Auth routes found: {len(auth_routes)}")

    assert len(org_routes) > 0, "No org routes registered"
    assert len(task_routes) > 0, "No task routes — regression!"
    assert len(auth_routes) > 0, "No auth routes — regression!"
    print("  ✅ api routes")


if __name__ == "__main__":
    print("=" * 50)
    print("Phase 1 Integration Tests")
    print("=" * 50)

    results = []

    print("\n[1/5] Module imports")
    p, f = test_imports()
    results.append(("Module imports", p, f))

    print("\n[2/5] Response utils")
    try:
        test_response_utils()
        results.append(("Response utils", 1, 0))
    except Exception as e:
        print(f"  ❌ {e}")
        results.append(("Response utils", 0, 1))

    print("\n[3/5] Exceptions")
    try:
        test_exceptions()
        results.append(("Exceptions", 1, 0))
    except Exception as e:
        print(f"  ❌ {e}")
        results.append(("Exceptions", 0, 1))

    print("\n[4/5] Org models")
    try:
        test_dept_model()
        results.append(("Org models", 1, 0))
    except Exception as e:
        print(f"  ❌ {e}")
        results.append(("Org models", 0, 1))

    print("\n[5/5] API routes")
    try:
        test_api_routes()
        results.append(("API routes", 1, 0))
    except Exception as e:
        print(f"  ❌ {e}")
        results.append(("API routes", 0, 1))

    print("\n" + "=" * 50)
    print("Summary:")
    total_passed = sum(r[1] for r in results)
    total_failed = sum(r[2] for r in results)
    for name, p, f in results:
        status = "✅" if f == 0 else "❌"
        print(f"  {status} {name}")
    print(f"\nTotal: {total_passed} passed, {total_failed} failed")

    if total_failed > 0:
        sys.exit(1)
    else:
        print("\n🎉 All Phase 1 integration tests passed!")
```

- [ ] **Step 2: 运行测试**

Run: `cd backend && python test_integration_phase1.py`
Expected: 所有测试通过

- [ ] **Step 3: 运行现有后端服务确认无回归**

Run: `cd backend && timeout 5 python -c "import uvicorn; uvicorn.run('app.main:app', host='0.0.0.0', port=8001)" 2>&1 || true`
Expected: 服务启动无报错（或至少模块导入无错误）

- [ ] **Step 4: 验证前端构建**

Run: `cd frontend && npm run build 2>&1 | tail -5`
Expected: 构建成功（exit code 0）

- [ ] **Step 5: Commit**

```bash
git add backend/test_integration_phase1.py
git commit -m "test: add Phase 1 integration tests"
```

---

## Phase 1 Completion Checklist

- [ ] `docker-compose up` 一键启动 MySQL + Redis + Backend
- [ ] 所有现有 API 端点（tasks/categories/auth 等）功能正常
- [ ] 部门树 API 返回正确的树形结构
- [ ] 部门 CRUD（创建/编辑/删除/子部门）功能正常
- [ ] 职位 CRUD 功能正常
- [ ] 成员花名册支持按部门/关键词/状态筛选和分页
- [ ] 成员信息（部门/职位/工号/状态）可编辑
- [ ] 审计日志自动记录所有写操作
- [ ] 前端部门管理页面可用
- [ ] 前端成员花名册页面可用
- [ ] 前端 MainLayout 新侧边栏+顶部栏可用
- [ ] `test_integration_phase1.py` 全部通过
