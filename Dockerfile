# =============================================================================
# 前后端一体镜像（多阶段构建）
#   stage 1  Node 构建 Vue 前端 → dist
#   stage 2  Python 运行后端，并把 dist 作为静态站点输出
# 注意：不使用 nginx，前端由 FastAPI 直接托管（FRONTEND_DIST=/app/static）
# =============================================================================

# ----------------------------- 1. 前端构建 -----------------------------
FROM node:20-alpine AS frontend-build

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

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        default-libmysqlclient-dev \
        pkg-config \
        tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend/ /app/
COPY --from=frontend-build /build/dist /app/static

# 运行时目录（compose 会用命名卷覆盖，保证重启不丢数据）
RUN mkdir -p /app/uploads /app/data/chroma /app/logs/agent_trace

EXPOSE 8001

# 单 worker：Agent 使用内存 checkpointer，且 WebSocket/Redis 订阅线程按进程启动，
# 多 worker 会导致会话状态与订阅重复，如需扩容请改用 Redis checkpointer 后再调大
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]
