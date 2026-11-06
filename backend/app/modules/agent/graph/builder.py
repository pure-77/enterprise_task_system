"""LangGraph 图装配（P2 / P3 / P4）

拓扑：
  START → route_intent → agent ⇄ tools → END
                          │        │
                          │        └─ next_tool_step：同一条 AI 消息还有未执行工具 → 再进 tools
                          └─ should_continue：无 tool_calls 或超轮次 → END

P3：由调用方传入 checkpointer（thread_id = 会话 key），interrupt 依赖它暂存状态。
P4：tools 每个 super-step 只执行一个工具，danger 级走 interrupt()。
"""
from langgraph.graph import END, START, StateGraph

from app.modules.agent.graph import nodes
from app.modules.agent.graph.state import AgentState


def build_graph(checkpointer=None):
    g = StateGraph(AgentState)
    g.add_node("route_intent", nodes.route_intent)
    g.add_node("agent", nodes.agent_node)
    g.add_node("tools", nodes.tools_node)

    g.add_edge(START, "route_intent")
    g.add_edge("route_intent", "agent")
    g.add_conditional_edges("agent", nodes.should_continue, {"tools": "tools", "end": END})
    # 单工具 super-step：一批 tool_calls 逐个执行，全部完成后回 agent
    g.add_conditional_edges("tools", nodes.next_tool_step, {"tools": "tools", "agent": "agent"})

    return g.compile(checkpointer=checkpointer)
