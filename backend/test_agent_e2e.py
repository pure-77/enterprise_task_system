"""Agent 端到端测试脚本

使用方法：
1. 下面 LOGIN_EMAIL 和 LOGIN_PASSWORD 填你的账号密码
2. 确保后端已启动（端口 8001）
3. 运行: .venv\Scripts\python.exe test_agent_e2e.py
"""
import os
import sys
import json

# ============== 你的登录信息（必填）==============
LOGIN_EMAIL = "3082476730@qq.com"
LOGIN_PASSWORD = "123456"
WORKSPACE_ID = 2  # 你的 workspace ID
BASE_URL = "http://localhost:8001"
# ===============================================

import httpx

def pp(obj):
    """漂亮打印 JSON"""
    print(json.dumps(obj, ensure_ascii=False, indent=2))

# ---------------- Step 1: 登录获取 JWT ----------------
print("=" * 60)
print("[Step 1] 登录获取 JWT Token")
print("=" * 60)

try:
    resp = httpx.post(
        f"{BASE_URL}/api/v1/auth/login",
        json={"email": LOGIN_EMAIL, "password": LOGIN_PASSWORD},
        timeout=10,
    )
    if resp.status_code != 200:
        print(f"❌ 登录失败: {resp.status_code}")
        pp(resp.json())
        sys.exit(1)

    token = resp.json()["data"]["access_token"]
    print(f"✅ 登录成功，user_id 已获取")
except Exception as e:
    print(f"❌ 登录异常: {e}")
    sys.exit(1)

headers = {"Authorization": f"Bearer {token}"}

# ---------------- Step 2: 查看已注册的工具 ----------------
print()
print("=" * 60)
print("[Step 2] 查看已注册的 Agent 工具")
print("=" * 60)

resp = httpx.get(f"{BASE_URL}/api/v1/agent/tools", headers=headers, timeout=10)
pp(resp.json())

# ---------------- Step 3: 端到端测试 ----------------
print()
print("=" * 60)
print("[Step 3] 端到端 Agent 对话测试")
print("=" * 60)

test_cases = [
    # 测试 1: 纯自然语言问答（不触发工具调用）
    {
        "label": "测试 1: 纯自然语言问候",
        "payload": {
            "message": "你好，你是谁？",
            "workspace_id": WORKSPACE_ID,
        },
    },
    # 测试 2: 创建任务（触发 tool_call）
    {
        "label": "测试 2: 创建任务（Function Calling）",
        "payload": {
            "message": f"帮我创建一个任务，标题是【写周报】，截止明天下午6点，优先级 medium",
            "workspace_id": WORKSPACE_ID,
        },
    },
    # 测试 3: 查询日程
    {
        "label": "测试 3: 查询日程",
        "payload": {
            "message": "我今天和明天有什么会议？",
            "workspace_id": WORKSPACE_ID,
        },
    },
]

for tc in test_cases:
    print()
    print(f"▶️  {tc['label']}")
    print(f"   输入: {tc['payload']['message']}")
    print()

    try:
        resp = httpx.post(
            f"{BASE_URL}/api/v1/agent/chat",
            json=tc["payload"],
            headers=headers,
            timeout=60,  # LLM 调用可能慢
        )

        if resp.status_code != 200:
            print(f"❌ HTTP {resp.status_code}")
            pp(resp.json())
            continue

        data = resp.json()
        result = data.get("data", data)  # 你的后端有统一响应包装

        print(f"   🤖 Agent 回复: {result.get('reply', '（无回复）')}")
        print(f"   📦 使用模型: {result.get('model_used')}")

        tool_calls = result.get("tool_calls", [])
        if tool_calls:
            print(f"   🔧 工具调用 ({len(tool_calls)} 次):")
            for tc_item in tool_calls:
                status = "✅" if tc_item.get("success") else "❌"
                print(f"      {status} {tc_item['tool_name']}({tc_item['arguments']})")
                if tc_item.get("result"):
                    print(f"         → {tc_item['result'][:200]}")
        else:
            print("   🔧 无工具调用（纯推理回复）")

        thinking = result.get("thinking")
        if thinking:
            print(f"   💭 思考过程: (已记录，可在调试模式查看)")

    except httpx.TimeoutException:
        print(f"❌ 请求超时（LLM 调用可能较慢，可增大 timeout）")
    except Exception as e:
        print(f"❌ 异常: {e}")

print()
print("=" * 60)
print("🎉 测试完成！")
print("=" * 60)
