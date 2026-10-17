import requests, json, time

BASE = 'http://127.0.0.1:8001'

r = requests.post(f'{BASE}/api/v1/auth/login',
                  json={'email': '3082476730@qq.com', 'password': '123456'}, timeout=10)
tok = r.json()['data']['access_token']
h = {'Authorization': f'Bearer {tok}'}
print("登录成功")

def chat(msg, sid):
    return requests.post(f'{BASE}/api/v1/agent/chat',
                         headers={**h, 'Content-Type': 'application/json'},
                         json={'message': msg, 'workspace_id': 1, 'session_id': sid}, timeout=120)

# 清记忆
for sid in ['agent-chat-1', 'agent-chat-2']:
    requests.delete(f'{BASE}/api/v1/agent/memory', headers=h, timeout=5, params={'session_id': sid})

# 测试 1: 意图路由 - 时间词不应抢任务
print("\n=== 测试 1: 帮我明天开个任务 ===")
r = chat('帮我明天开个任务', 'agent-chat-1')
d = r.json()['data']
tc_names = [t['tool_name'] for t in d.get('tool_calls', [])]
print(f"  reply前150: {d.get('reply', '')[:150]}")
print(f"  tool_calls: {tc_names}")
print(f"  create_task 在里面: {'create_task' in tc_names}")
print(f"  success 是 bool: {all(isinstance(t['success'], bool) for t in d.get('tool_calls', []))}")

# 测试 2: 意图路由 - 日历强匹配
print("\n=== 测试 2: 帮我明天下午3点开个会 ===")
r = chat('帮我明天下午3点开个会', 'agent-chat-2')
d = r.json()['data']
tc_names = [t['tool_name'] for t in d.get('tool_calls', [])]
print(f"  reply前150: {d.get('reply', '')[:150]}")
print(f"  tool_calls: {tc_names}")

# 测试 3: general 组
print("\n=== 测试 3: 你好，你是谁 ===")
r = chat('你好，你是谁？', 'agent-chat-1')
d = r.json()['data']
print(f"  reply前150: {d.get('reply', '')[:150]}")
print(f"  不是 '没有可用的工具': {'没有可用的工具' not in d.get('reply', '')}")

# 测试 4: 完整工具链
print("\n=== 测试 4: 查待办 + 创建任务 ===")
r = chat('帮我查一下我的待办，然后创建一个任务：测试修复后的 Agent', 'agent-chat-1')
d = r.json()['data']
tc_names = [t['tool_name'] for t in d.get('tool_calls', [])]
print(f"  reply前150: {d.get('reply', '')[:150]}")
print(f"  tool_calls: {tc_names}")
print(f"  list_tasks 在: {'list_tasks' in tc_names}")
print(f"  create_task 在: {'create_task' in tc_names}")
print(f"  所有 success bool: {all(isinstance(t['success'], bool) for t in d.get('tool_calls', []))}")

# 测试 5: 多人完成追踪（简单测试 get_task_detail）
print("\n=== 测试 5: 查询任务详情 ===")
r = chat('帮我查一下任务 30 的详情', 'agent-chat-2')
d = r.json()['data']
tc_names = [t['tool_name'] for t in d.get('tool_calls', [])]
print(f"  reply前150: {d.get('reply', '')[:150]}")
print(f"  tool_calls: {tc_names}")

print("\n=== 全部测试完成 ===")
