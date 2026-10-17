---
name: python-venv
description: Use the project's local .venv Python interpreter for all Python execution
---

# Python venv Interpreter

Always use the project's local virtual environment Python interpreter when running any Python code, scripts, or commands for this project.

## Interpreter Path

```
.venv/Scripts/python.exe
```

Full absolute path (for reference):
```
D:\Python Note\web_server\personal_task_system\.venv\Scripts\python.exe
```

## Usage

When executing Python commands via Bash, always prefix with the venv interpreter:

```bash
# Running Python scripts
.venv/Scripts/python.exe script.py

# Running Python one-liners
.venv/Scripts/python.exe -c "print('hello')"

# Running module tests
.venv/Scripts/python.exe -m pytest tests/

# Running management commands
.venv/Scripts/python.exe -m uvicorn app.main:app --reload

# pip install (use the venv's pip)
.venv/Scripts/python.exe -m pip install package_name
```

## Important Notes

- **Never** use the system `python` or `python3` command directly — the Windows Store stub at `WindowsApps/python` returns exit code 49 and does not work.
- If a command needs to run from a specific subdirectory (e.g., `backend/`), use `cd` first, then invoke the interpreter with a relative path to `.venv`:
  ```bash
  cd backend && ../.venv/Scripts/python.exe -c "import app"
  ```
- The venv path `.venv` is relative to the project root: `D:\Python Note\web_server\personal_task_system`
