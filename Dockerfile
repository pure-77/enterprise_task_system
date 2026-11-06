# =============================================================================
# 前后端一体镜像（多阶段构建）
#   stage 1  Node 构建 Vue 前端 → dist
#   stage 2  Python 运行后端，并把 dist 作为静态站点输出
# 注意：不使用 nginx，前端由 FastAPI 直接托管（FRONTEND_DIST=/app/static）
# =============================================================================

# ----------------------------- 1. 前端构建 -----------------------------
FROM node:20-alpine AS frontend-build

# 国内服务器默认走 npmmirror，海外可传 --build-arg NPM_REGISTRY=https://registry.npmjs.org
ARG NPM_REGISTRY=https://registry.npmmirror.com
RUN npm config set registry ${NPM_REGISTRY}

WORKDIR /build

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund || npm install --no-audit --no-fund

COPY frontend/ ./

# 前端走同源部署：浏览器请求 /api/v1，由 FastAPI 处理
ARG VITE_API_BASE_URL=/api/v1
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

RUN npm run build

# ----------------------------- 2. 后端运行 -----------------------------
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai \
    FRONTEND_DIST=/app/static

WORKDIR /app

# 国内服务器默认走阿里云镜像，海外可覆盖两个 build-arg
ARG PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple
ARG PIP_TRUSTED_HOST=mirrors.aliyun.com

RUN sed -i 's|http://deb.debian.org|http://mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        default-libmysqlclient-dev \
        pkg-config \
        tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir \
        -i ${PIP_INDEX_URL} \
        --trusted-host ${PIP_TRUSTED_HOST} \
        -r /app/requirements.txt

COPY backend/ /app/
COPY --from=frontend-build /build/dist /app/static

# 运行时目录（compose 会用命名卷覆盖，保证重启不丢数据）
RUN mkdir -p /app/uploads /app/data/chroma /app/logs/agent_trace

EXPOSE 8001

# 单 worker：Agent 使用内存 checkpointer，且 WebSocket/Redis 订阅线程按进程启动，
# 多 worker 会导致会话状态与订阅重复，如需扩容请改用 Redis checkpointer 后再调大
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]
