"""5 个只读工具的 MCP Adapter（P1 收敛范围）

规则：Adapter 只做参数透传和身份装配，绝不复制 handler 内部逻辑。
入选标准：纯读、无副作用、可重复调用（写操作一律不对外暴露，见迁移方案 6.3）。
结果统一按 AGENT_MCP_MAX_TOOL_RESULTS 截断，防止撑爆客户端上下文。
"""
from app.core.config import settings
from app.modules.agent.mcp.server import mcp
from app.modules.agent.mcp.auth import resolve_context
from app.modules.agent.tools.task_tools import _handler_list_tasks, _handler_get_task_detail
from app.modules.agent.tools.misc_tools import _handler_get_stats
from app.modules.agent.tools.knowledge_tools import _handler_search_knowledge
from app.modules.agent.tools.summary_tools import _handler_summarize_week_progress


def _truncate(result: str) -> str:
    limit = settings.AGENT_MCP_MAX_TOOL_RESULTS
    if isinstance(result, str) and len(result) > limit:
        return result[:limit] + f"...(已截断，原始长度 {len(result)})"
    return result


@mcp.tool(name="list_tasks", description="查询当前用户的任务列表，支持按状态/负责人/关键词过滤与分页")
def list_tasks(workspace_id: int = None, status: str = None, assignee_id: int = None,
               keyword: str = None, page: int = 1, page_size: int = 20) -> str:
    ctx = resolve_context(workspace_id)
    return _truncate(_handler_list_tasks(
        workspace_id=ctx["workspace_id"], status=status, assignee_id=assignee_id,
        keyword=keyword, page=page, page_size=page_size, context=ctx,
    ))


@mcp.tool(name="get_task_detail", description="根据任务 ID 查询任务详情；仅能查看有权限的任务")
def get_task_detail(task_id: int) -> str:
    return _truncate(_handler_get_task_detail(task_id=task_id, context=resolve_context()))


@mcp.tool(name="get_statistics_overview", description="查询指定工作区的任务统计概览（总数/完成率/逾期数）")
def get_statistics_overview(workspace_id: int = None) -> str:
    ctx = resolve_context(workspace_id)
    return _truncate(_handler_get_stats(workspace_id=ctx["workspace_id"], context=ctx))


@mcp.tool(name="search_knowledge", description="在工作区文件、公告、聊天记录中做语义检索，返回最相关的片段")
def search_knowledge(query: str, top_k: int = None, source_types: list = None) -> str:
    return _truncate(_handler_search_knowledge(
        query=query, top_k=top_k, source_types=source_types, context=resolve_context(),
    ))


@mcp.tool(name="summarize_week_progress", description="汇总本周任务完成率、逾期项与打卡情况")
def summarize_week_progress() -> str:
    return _truncate(_handler_summarize_week_progress(context=resolve_context()))
