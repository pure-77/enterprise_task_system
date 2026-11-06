"""一键启动脚本：后端三件套（FastAPI + Celery worker + Celery beat）。

- 不启动 MySQL / Redis / 前端，这些由用户在外部维护
- 从 .venv 选择 Python（无则回退当前解释器）
- 端口冲突自动清理旧进程；启动后做一次健康检查
- Agent 引擎默认切到 langgraph（P0-P6 全量验证通过）
- 按 Ctrl+C 可同时停止所有子进程

用法（项目根目录）：
    .venv\\Scripts\\python.exe start_web.py
    .venv\\Scripts\\python.exe start_web.py --no-celery     # 只起 FastAPI（纯 API 调试）
"""
import argparse
import os
import signal
import socket
import subprocess
import sys
import threading
import time

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")

VENV_PYTHON = os.path.join(ROOT_DIR, ".venv", "Scripts", "python.exe")
PYTHON = VENV_PYTHON if os.path.exists(VENV_PYTHON) else sys.executable
POOL_ARGS = ["--pool=solo"] if os.name == "nt" else []

# —— Agent 引擎：P0-P6 全量验证通过，默认切到 langgraph ——
# MCP 工具服务也一起挂载（5 个只读工具，走 /mcp）
# checkpointer 指定 memory（本机 Redis 5.0 无 RediSearch/RedisJSON，
# 用 redis 每次启动都要 warning + fallback，直接写 memory 干净）
DEFAULT_ENV = {
    "AGENT_ENGINE": "langgraph",
    "AGENT_MCP_ENABLED": "true",
    "AGENT_CHECKPOINTER": "memory",
}

PROCESSES = [
    (
        "fastapi",
        [PYTHON, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"],
        8001,
    ),
    (
        "celery-worker",
        [PYTHON, "-m", "celery", "-A", "app.core.celery_config", "worker", "--loglevel=info", *POOL_ARGS],
        None,
    ),
    (
        "celery-beat",
        [PYTHON, "-m", "celery", "-A", "app.core.celery_config", "beat", "--loglevel=info"],
        None,
    ),
]


def _port_free(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False


def _kill_port(port: int) -> None:
    """Windows 下用 netstat 找进程再 taskkill 掉（旧的 uvicorn 进程可能残留）"""
    if os.name != "nt":
        return
    try:
        out = subprocess.check_output(
            ["netstat", "-ano"], stderr=subprocess.DEVNULL, text=True, encoding="gbk", errors="replace"
        )
    except Exception:
        return
    pids = set()
    for line in out.splitlines():
        if f":{port}" in line and "LISTENING" in line:
            parts = line.split()
            if parts:
                try:
                    pids.add(int(parts[-1]))
                except ValueError:
                    pass
    for pid in pids:
        if pid == os.getpid():
            continue
        print(f"  → 清理占用 {port} 端口的进程 PID={pid}")
        try:
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
    # 给端口腾出来一点时间
    time.sleep(0.5)


def _wait_port(port: int, timeout: float = 20.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if not _port_free(port):
            return True
        time.sleep(0.5)
    return False


def _wait_http(url: str, timeout: float = 25.0) -> bool:
    """FastAPI 起来后还得等 app startup 钩子跑完（工具注册 / MCP session_manager / Redis 订阅），
    端口占用不代表真的能用 —— 发一次 GET /docs 确认 200。"""
    import urllib.request
    import urllib.error
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            req = urllib.request.Request(url, method="HEAD")
            with urllib.request.urlopen(req, timeout=3) as resp:
                if 200 <= resp.status < 500:
                    return True
        except (urllib.error.URLError, ConnectionRefusedError, OSError):
            pass
        time.sleep(0.5)
    return False


def _stream_output(name: str, pipe) -> None:
    for line in iter(pipe.readline, ""):
        sys.stdout.write(f"[{name}] {line}")
        sys.stdout.flush()
    pipe.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="一键启动后端三件套")
    parser.add_argument("--no-celery", action="store_true", help="只起 FastAPI（调试 API 时用）")
    parser.add_argument("--no-kill", action="store_true", help="不自动清理端口占用（保留已有进程）")
    parser.add_argument("--engine", choices=["legacy", "langgraph"],
                        help="覆盖 AGENT_ENGINE（默认 langgraph）")
    parser.add_argument("--no-mcp", action="store_true", help="不挂载 /mcp 工具服务")
    args = parser.parse_args()

    if not os.path.isdir(BACKEND_DIR):
        print(f"未找到后端目录: {BACKEND_DIR}")
        return 1

    # 组装环境变量：DEFAULT_ENV + 用户显式覆盖 + 进程现有环境（env vars > .env）
    env = os.environ.copy()
    for k, v in DEFAULT_ENV.items():
        env.setdefault(k, v)
    if args.engine:
        env["AGENT_ENGINE"] = args.engine
    if args.no_mcp:
        env["AGENT_MCP_ENABLED"] = "false"
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUNBUFFERED", "1")

    engine = env["AGENT_ENGINE"]
    mcp = env.get("AGENT_MCP_ENABLED", "false")
    cp = env.get("AGENT_CHECKPOINTER", "")

    print("=" * 60)
    print(f"  项目  : {os.path.basename(ROOT_DIR)}")
    print(f"  Python: {PYTHON}")
    print(f"  cwd   : {BACKEND_DIR}")
    print(f"  Agent : engine={engine}  mcp={mcp}  checkpointer={cp or 'default'}")
    print("=" * 60)

    # —— 端口清理 ——
    if not args.no_kill:
        for name, cmd, port in PROCESSES:
            if port is not None and not _port_free(port):
                print(f"[warn] 端口 {port} 已被占用，尝试清理...")
                _kill_port(port)

    # —— 裁剪掉 --no-celery 时的 celery 进程 ——
    to_start = PROCESSES
    if args.no_celery:
        to_start = [(n, c, p) for (n, c, p) in PROCESSES if n == "fastapi"]

    children: list[tuple[str, subprocess.Popen, int | None]] = []
    try:
        for name, cmd, port in to_start:
            print(f"\n启动 {name}: {' '.join(cmd)}")
            proc = subprocess.Popen(
                cmd,
                cwd=BACKEND_DIR,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
            children.append((name, proc, port))
            threading.Thread(target=_stream_output, args=(name, proc.stdout), daemon=True).start()

            # FastAPI 做一次启动就绪等待
            if name == "fastapi" and port is not None:
                if _wait_port(port, timeout=15):
                    print(f"[ok] 端口 {port} 已监听，等待应用就绪...")
                else:
                    print(f"[warn] 端口 {port} 未在 15s 内监听，继续观察")
                    continue
                if _wait_http(f"http://127.0.0.1:{port}/docs", timeout=25):
                    print(f"[ok] FastAPI 就绪（http://127.0.0.1:{port}/docs）")
                else:
                    print(f"[warn] FastAPI /docs 未在 25s 内响应，可能是启动耗时较长或进程异常")

        print("\n" + "-" * 60)
        print("所有服务已启动。按 Ctrl+C 停止。")
        if any(n == "fastapi" for n, _, _ in children):
            print("  API 文档  : http://127.0.0.1:8001/docs")
        print("  Agent 引擎: " + engine)
        print("  MCP 服务  : " + (f"http://127.0.0.1:8001/mcp  (token 鉴权)" if mcp == "true" else "disabled"))
        print("  前端      : 请在 frontend/ 目录另行启动（npm run dev）")
        print("-" * 60 + "\n")

        # 阻塞等待，任一进程退出就触发整体清理
        while True:
            for name, proc, _ in children:
                if proc.poll() is not None:
                    print(f"\n[{name}] 进程已退出（码 {proc.returncode}），停止全部服务...")
                    raise KeyboardInterrupt  # 复用 finally 的清理逻辑
            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\n收到中断信号，正在停止所有服务...")
    finally:
        for name, proc, _ in children:
            if proc.poll() is None:
                try:
                    if os.name == "nt":
                        # Windows subprocess.Popen.terminate() 常常杀不掉 Python 子进程树
                        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                                       check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    else:
                        proc.terminate()
                except Exception:
                    pass
        # 等待全部收尸
        deadline = time.time() + 5
        for name, proc, _ in children:
            while proc.poll() is None and time.time() < deadline:
                time.sleep(0.2)
            if proc.poll() is None:
                print(f"  → 强杀 {name}")
                try:
                    proc.kill()
                except Exception:
                    pass
        print("所有服务已停止。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
