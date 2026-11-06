"""LangGraph 编排引擎（迁移方案 P2）

与 legacy 引擎行为对齐，通过 AGENT_ENGINE=langgraph 灰度切换。
节点编排收敛为图：route_intent → agent ⇄ tools → END，
工具注册表、危险等级、确认流程等单一事实来源仍由 legacy.tool_registry 持有。
"""
