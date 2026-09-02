# Personal Task System — 企业协作办公平台

从「个人任务管理系统」逐步演进而来的全功能企业协作平台，支持多工作空间、任务管理、即时通讯、OA 审批、考勤打卡、日程日历等模块。

## 功能概览

| 模块 | 说明 |
|------|------|
| **任务管理** | 任务增删改查、状态流转、优先级、截止日期、多指派人、分类/标签 |
| **工作空间** | 多空间隔离、三级角色（Owner/Admin/Member）、邀请机制、活动日志 |
| **即时通讯** | 空间内会话、文字/图片/文件消息、已读回执、免打扰、WebSocket 实时推送 |
| **OA 审批** | 可配置审批模板、多级审批流、转交/抄送、流程引擎 |
| **考勤打卡** | 管理员定义考勤规则、员工签到/签退 |
| **日程日历** | 事件创建、重复事件自动展开、参与人管理 |
| **企业公告** | 公告发布与详情查看 |
| **文件管理** | 文件夹层级、文件上传/下载/移动/删除 |
| **组织架构** | 部门管理、职位管理、成员花名册 |
| **通知中心** | 多类型通知聚合、未读计数、WebSocket 实时推送 |
| **统计面板** | 任务完成率、趋势图表（ECharts） |
| **数据备份** | Excel 异步导出/JSON 导入（Celery 后台任务） |
| **用户系统** | 邮箱注册（验证码）、JWT 认证、头像上传、密码找回 |

## 技术栈

### 后端

- **框架**：FastAPI
- **ORM**：SQLAlchemy
- **数据库**：MySQL 8.0
- **缓存**：Redis 7
- **异步任务**：Celery + Redis Broker
- **认证**：JWT（access + refresh token）
- **实时通信**：WebSocket（Redis Pub/Sub）
- **部署**：Gunicorn + Supervisor / Docker Compose

### 前端

- **框架**：Vue 3 + Vite 5
- **UI 组件库**：Element Plus
- **状态管理**：Pinia
- **路由**：Vue Router 4
- **图表**：ECharts 5
- **HTTP 客户端**：Axios

## 项目结构

```
personal_task_system/
├── backend/                          # 后端
│   └── app/
│       ├── api/v1/                   # REST API 路由
│       │   ├── auth.py               # 注册 / 登录 / 验证码 / 刷新 token
│       │   ├── task.py               # 任务 CRUD / 状态变更
│       │   ├── category.py           # 分类管理
│       │   ├── tag.py                # 标签管理
│       │   ├── statistics.py         # 统计数据
│       │   ├── workspace.py          # 工作空间
│       │   ├── invitation.py         # 邀请
│       │   ├── profile.py            # 用户资料
│       │   ├── backup.py             # 备份恢复
│       │   └── websocket.py          # WebSocket 连接
│       ├── modules/                  # 功能模块
│       │   ├── task/                 # 任务模块
│       │   ├── im/                   # 即时通讯
│       │   ├── approval/             # OA 审批
│       │   ├── attendance/           # 考勤打卡
│       │   ├── calendar/             # 日程日历
│       │   ├── announcement/         # 企业公告
│       │   ├── file/                 # 文件管理
│       │   ├── notification/         # 通知中心
│       │   └── org/                  # 组织架构
│       ├── core/                     # 配置 / 安全 / 异常
│       ├── crud/                     # 数据库操作层
│       ├── db/                       # 数据库连接 / Redis 客户端
│       ├── middleware/               # 中间件（响应格式化 / 审计日志 / 静态鉴权）
│       ├── models/                   # SQLAlchemy 数据模型
│       ├── schemas/                  # Pydantic 请求/响应模型
│       ├── services/                 # 业务逻辑（缓存 / 邮件 / 任务状态）
│       └── tasks/                    # Celery 异步任务
├── frontend/                         # 前端
│   └── src/
│       ├── api/                      # API 调用封装
│       ├── components/               # 通用组件
│       ├── layouts/                  # 布局组件
│       ├── pinia/                    # 状态管理
│       ├── router/                   # 路由配置
│       ├── views/                    # 页面视图
│       └── utils/                    # 工具函数
├── docker-compose.yml                # Docker 编排
└── docs/                             # 项目文档
```

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- MySQL 8.0
- Redis 7

### 方式一：Docker Compose（推荐）

```bash
# 启动 MySQL + Redis + 后端
docker-compose up -d

# 前端单独启动（开发模式）
cd frontend
npm install
npm run dev
```

### 方式二：手动启动

#### 1. 后端

```bash
cd backend

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量（在 backend/ 下创建 .env 文件）
# 需要配置：DATABASE_URL, REDIS_URL, SECRET_KEY, 邮箱相关变量等

# 初始化数据库
python init_db.py

# 启动开发服务器
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# 启动 Celery Worker（Windows 需加 --pool=solo）
celery -A app.core.celery_config worker --loglevel=info --pool=solo
```

#### 2. 前端

```bash
cd frontend

npm install
npm run dev
```

访问 http://localhost:3000 即可。

### 生产部署

```bash
# 后端
gunicorn -c gunicorn.conf.py app.main:app

# 使用 Supervisor 管理进程
sudo cp backend/supervisor.conf /etc/supervisor/conf.d/
sudo supervisorctl reread && sudo supervisorctl update

# 前端构建
cd frontend
npm run build  # 产物在 dist/ 目录
```

## 权限模型

| 操作 | Owner | Admin | Member |
|------|:-----:|:-----:|:------:|
| 修改空间信息 | ✔ | ✔ | ✘ |
| 解散空间 | ✔ | ✘ | ✘ |
| 管理成员 | ✔ | ✔ | ✘ |
| 创建/编辑自己的任务 | ✔ | ✔ | ✔ |
| 编辑他人的任务 | ✔ | ✔ | ✘ |
| 管理分类/标签 | ✔ | ✔ | ✔ |

## API 文档

启动后端后访问：

- Swagger UI：http://localhost:8001/docs
- ReDoc：http://localhost:8001/redoc

## License

MIT
