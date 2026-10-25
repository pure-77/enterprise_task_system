"""直接用 TestClient 复现分配问题"""
from fastapi.testclient import TestClient
import sys
sys.path.insert(0, ".")
from app.main import app
from app.core.security import create_access_token
from app.db.session import SessionLocal

db = SessionLocal()
client = TestClient(app)

def get_token(user_id):
    return create_access_token({"user_id": user_id, "sub": f"user{user_id}"}, db=db)

h = {"Authorization": f"Bearer {get_token(1)}"}

# 取 workspace 1 的分类
r = client.get("/api/v1/categories", headers=h, params={"workspace_id": 1})
print("cats:", r.status_code, r.text[:200])
cats = r.json()
data = cats.get("data", cats) if isinstance(cats, dict) else cats
cat_id = None
if isinstance(data, list) and data:
    cat_id = data[0]["id"]
print("cat_id:", cat_id)

if not cat_id:
    r = client.post("/api/v1/categories", headers=h, json={"name": "测试", "workspace_id": 1})
    print("create cat:", r.status_code, r.text[:200])
    cat_id = r.json()["id"]

# 创建一个 workspace 1 非团队公开任务（个人任务），不分配给任何人
payload = {
    "title": "复现-个人任务待分配",
    "category_id": cat_id,
    "workspace_id": 1,
    "is_team_wide": False,
    "priority": "medium"
}
r = client.post("/api/v1/tasks", headers=h, json=payload)
print("create task:", r.status_code, r.text[:300])
task = r.json()
if isinstance(task, dict) and "data" in task:
    task = task["data"]
task_id = task["id"]
print(f"task_id={task_id} assignee_id={task.get('assignee_id')} is_team_wide={task.get('is_team_wide')}")

# 尝试分配给 user 2
r = client.put(f"/api/v1/tasks/{task_id}", headers=h, json={
    "assignee_id": 2,
    "assignee_ids": [2]
})
print(f"\n=== 分配给 user2 ===")
print("status:", r.status_code)
print("response:", r.text[:500])

db.close()
