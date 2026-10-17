"""一键启动脚本：FastAPI 服务 + Celery worker + Celery beat。

用法（在项目根目录执行）：
    .venv\\Scripts\\python.exe start_web.py

按 Ctrl+C 可同时停止所有子进程。
"""
import os
import subprocess
import sys
import threading

# 项目根目录（本文件所在目录）
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT_DIR, "backend")

# 选择虚拟环境解释器：优先使用根目录 .venv，否则回退当前解释器
VENV_PYTHON = os.path.join(ROOT_DIR, ".venv", "Scripts", "python.exe")
PYTHON = VENV_PYTHON if os.path.exists(VENV_PYTHON) else sys.executable

# Celery 在 Windows 下必须使用 solo 线程池
POOL_ARGS = ["--pool=solo"] if os.name == "nt" else []

# 需要启动的进程：(名称, 命令, 输出颜色标记)
PROCESSES = [
    (
        "fastapi",
        [PYTHON, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"],
    ),
    (
        "celery-worker",
        [PYTHON, "-m", "celery", "-A", "app.core.celery_config", "worker", "--loglevel=info", *POOL_ARGS],
    ),
    (
        "celery-beat",
        [PYTHON, "-m", "celery", "-A", "app.core.celery_config", "beat", "--loglevel=info"],
    ),
]


def _stream_output(name, pipe):
    """逐行读取子进程输出，并加上进程名前缀。"""
    for line in iter(pipe.readline, ""):
        sys.stdout.write(f"[{name}] {line}")
        sys.stdout.flush()
    pipe.close()


def main():
    if not os.path.isdir(BACKEND_DIR):
        print(f"未找到后端目录: {BACKEND_DIR}")
        sys.exit(1)

    print(f"使用解释器: {PYTHON}")
    print(f"工作目录  : {BACKEND_DIR}")

    # 复用同一个环境变量副本（Windows 下避免各进程互相干扰）
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("PYTHONUNBUFFERED", "1")

    children = []
    try:
        for name, cmd in PROCESSES:
            print(f"启动 {name}: {' '.join(cmd)}")
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
            children.append((name, proc))
            threading.Thread(
                target=_stream_output, args=(name, proc.stdout), daemon=True
            ).start()

        print("\n所有服务已启动。访问 http://localhost:8001/docs ，按 Ctrl+C 停止。\n")
        # 阻塞等待，直到任一进程退出
        for name, proc in children:
            proc.wait()
            print(f"[{name}] 进程已退出（退出码 {proc.returncode}）")
            break
    except KeyboardInterrupt:
        print("\n收到中断信号，正在停止所有服务...")
    finally:
        for name, proc in children:
            if proc.poll() is None:
                proc.terminate()
        for name, proc in children:
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        print("所有服务已停止。")


if __name__ == "__main__":
    main()
