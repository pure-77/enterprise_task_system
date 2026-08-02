# 个人任务管理系统后端

## 项目结构

```
backend/
├── app/                          # 核心应用目录
│   ├── api/                      # 接口路由层（按模块拆分）
│   │   ├── dependencies.py       # 通用依赖（如登录校验、权限校验）
│   │   ├── v1/                   # API v1版本（便于迭代）
│   │   │   ├── auth.py           # 认证接口（注册/登录/验证码/刷新token）
│   │   │   ├── task.py           # 任务核心接口（增删改查/状态修改）
│   │   │   ├── category.py       # 任务分类接口
│   │   │   ├── statistics.py     # 统计接口（完成率/趋势）
│   │   │   └── user.py           # 用户信息接口
│   ├── core/                     # 核心配置层
│   │   ├── config.py             # 全局配置（数据库/Redis/邮件/腾讯云）
│   │   ├── security.py           # 安全工具（JWT生成/校验、密码加密）
│   │   └── exceptions.py         # 自定义异常及处理
│   ├── crud/                     # 数据库操作层（CRUD）
│   │   ├── base.py               # 基础CRUD封装（复用）
│   │   ├── task.py               # 任务CRUD
│   │   ├── category.py           # 分类CRUD
│   │   └── user.py               # 用户CRUD
│   ├── db/                       # 数据库初始化
│   │   ├── base.py               # 模型基类
│   │   ├── session.py            # 数据库会话（同步/异步可选）
│   │   └── redis_client.py       # Redis客户端初始化
│   ├── models/                   # 数据模型（数据库表结构）
│   │   ├── user.py               # 用户表（id/邮箱/密码/昵称/创建时间）
│   │   ├── task.py               # 任务表（关联用户/分类）
│   │   └── category.py           # 分类表（关联用户）
│   ├── schemas/                  # 数据校验/返回模型（Pydantic）
│   │   ├── user.py               # 用户请求/响应模型（注册/登录/验证码）
│   │   ├── task.py               # 任务模型
│   │   └── category.py           # 分类模型
│   ├── services/                 # 业务逻辑层（复杂逻辑封装）
│   │   ├── email_service.py      # 邮件发送服务（验证码）
│   │   ├── cache_service.py      # Redis缓存服务
│   │   └── task_service.py       # 任务业务逻辑
│   └── main.py                   # 项目入口（创建FastAPI实例、注册路由/中间件）
├── .env                          # 环境变量（敏感配置：数据库地址/Redis/邮箱密钥/JWT密钥）
├── .env.example                  # 环境变量示例（提交代码用）
├── requirements.txt              # 依赖清单
├── gunicorn.conf.py              # Gunicorn配置（部署用）
├── supervisor.conf               # Supervisor配置（进程守护）
└── README.md                     # 项目说明（含部署步骤）
```

## 部署步骤

1. **安装依赖**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **配置环境变量**
   - 复制 `.env.example` 为 `.env`
   - 修改 `.env` 中的配置项

3. **启动开发服务器**
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```

4. **部署到生产环境**
   - 使用 Gunicorn 作为 WSGI 服务器
   - 使用 Supervisor 管理进程

   ```bash
   # 启动 Gunicorn
   gunicorn -c gunicorn.conf.py app.main:app
   
   # 配置 Supervisor
   sudo cp supervisor.conf /etc/supervisor/conf.d/
   sudo supervisorctl reread
   sudo supervisorctl update
   sudo supervisorctl start personal_task_system
   ```

## 技术栈

- **框架**: FastAPI
- **数据库**: PostgreSQL
- **缓存**: Redis
- **认证**: JWT
- **部署**: Gunicorn + Supervisor
