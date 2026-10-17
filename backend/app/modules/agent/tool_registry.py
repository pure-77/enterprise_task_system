"""Agent 模块 — 工具注册中心（Tool Registry）

设计思路：
- 每个业务 API 包装为一个 Tool：JSON Schema（描述 + 参数）+ handler（执行函数）
- handler 内部直接导入你现有项目的 CRUD 或 Service，走同一套业务逻辑
- 按模块分组管理（task_tools / calendar_tools / im_tools …）
- 提供 get_tools(module=None) 方法按需加载工具组，避免单次对话工具过多

Guardrails：
- 仅 danger_level="safe" 的工具在异常时自动 retry 一次
  （写操作 warn/danger 绝不重试，避免重复扣款/重复发送/重复删除）
- 统一的执行结果包装（确保 handler 不返回裸异常）
- handler 为同步阻塞函数，统一丢到 anyio 线程池执行，避免阻塞事件循环
"""
import json
import logging
from typing import Callable, Optional

import anyio

logger = logging.getLogger("agent.tools")


# 工具元数据表 — 给前端渲染用（图标 + 动作名 + 危险等级）
# danger_level: "safe"（只读/低风险）/ "warn"（有副作用但可恢复）/ "danger"（不可恢复或不可逆）
_TOOL_META: dict[str, dict] = {
    # task
    "create_task":          {"icon": "📋", "action": "创建任务", "danger_level": "warn"},
    "plan_tasks":           {"icon": "🗺️", "action": "生成任务规划", "danger_level": "safe"},
    "list_tasks":           {"icon": "📋", "action": "查询任务", "danger_level": "safe"},
    "get_task_detail":      {"icon": "📋", "action": "查看任务详情", "danger_level": "safe"},
    "complete_task":        {"icon": "✅", "action": "完成任务", "danger_level": "warn"},
    "update_task_status":   {"icon": "🔄", "action": "更新任务状态", "danger_level": "warn"},

    # calendar
    "list_calendar_events":     {"icon": "📅", "action": "查询日程", "danger_level": "safe"},
    "create_calendar_event":    {"icon": "📅", "action": "创建日程", "danger_level": "warn"},
    "delete_calendar_event":    {"icon": "🗑️", "action": "删除日程", "danger_level": "danger"},

    # im
    "list_im_conversations": {"icon": "💬", "action": "查询会话", "danger_level": "safe"},
    "list_im_messages":      {"icon": "💬", "action": "查询消息", "danger_level": "safe"},
    "send_im_message":       {"icon": "💬", "action": "发送消息", "danger_level": "warn"},

    # attendance
    "attendance_check_in":   {"icon": "🕐", "action": "上班打卡", "danger_level": "warn"},
    "attendance_check_out":  {"icon": "🕐", "action": "下班打卡", "danger_level": "warn"},
    "attendance_stats":      {"icon": "📊", "action": "查询考勤", "danger_level": "safe"},

    # approval
    "list_my_approvals":     {"icon": "📝", "action": "查询审批", "danger_level": "safe"},
    "submit_approval":       {"icon": "📝", "action": "提交审批", "danger_level": "warn"},
    "approve_approval":      {"icon": "✅", "action": "审批通过", "danger_level": "danger"},
    "reject_approval":       {"icon": "❌", "action": "审批驳回", "danger_level": "danger"},

    # org
    "list_workspace_members": {"icon": "👥", "action": "查询成员", "danger_level": "safe"},
    "list_departments":       {"icon": "🏢", "action": "查询部门", "danger_level": "safe"},
    "list_positions":         {"icon": "💼", "action": "查询职位", "danger_level": "safe"},

    # file
    "search_files":    {"icon": "📁", "action": "搜索文件", "danger_level": "safe"},
    "get_file_detail": {"icon": "📄", "action": "查看文件", "danger_level": "safe"},
    "delete_file":     {"icon": "🗑️", "action": "删除文件", "danger_level": "danger"},
    "create_folder":   {"icon": "📁", "action": "创建文件夹", "danger_level": "warn"},

    # notification / announcement
    "list_notifications":     {"icon": "🔔", "action": "查询通知", "danger_level": "safe"},
    "mark_notification_read": {"icon": "🔔", "action": "标记已读", "danger_level": "safe"},
    "list_announcements":    {"icon": "📢", "action": "查询公告", "danger_level": "safe"},

    # statistics
    "get_statistics_overview": {"icon": "📊", "action": "查询统计", "danger_level": "safe"},
}


class ToolRegistry:
    """工具注册中心 — 全局单例"""

    _registry: dict[str, dict] = {}
    _groups: dict[str, list[str]] = {}
    _initialized: bool = False
    _max_retry: int = 1

    # -------------- 元数据 --------------

    @classmethod
    def get_tool_meta(cls, tool_name: str) -> dict:
        """获取工具元数据（icon / action / danger_level），找不到返回默认值"""
        return _TOOL_META.get(tool_name, {"icon": "🔧", "action": tool_name, "danger_level": "safe"})

    # -------------- 注册 --------------

    @classmethod
    def register(
        cls,
        name: str,
        schema: dict,
        handler: Callable,
        group: str = "general",
    ):
        if name in cls._registry:
            logger.warning(f"[ToolRegistry] 工具 {name} 已注册，跳过重复注册")
            return

        cls._registry[name] = {
            "schema": schema,
            "handler": handler,
            "group": group,
        }

        if group not in cls._groups:
            cls._groups[group] = []
        cls._groups[group].append(name)

        logger.info(f"[ToolRegistry] 已注册工具: {name} (group={group})")

    # -------------- 查询 --------------

    @classmethod
    def get_all_schemas(cls) -> list[dict]:
        return [
            {"type": "function", "function": v["schema"]}
            for v in cls._registry.values()
        ]

    @classmethod
    def get_schemas_by_group(cls, group: str) -> list[dict]:
        names = cls._groups.get(group, [])
        return [
            {"type": "function", "function": cls._registry[n]["schema"]}
            for n in names
        ]

    @classmethod
    def get_schemas_by_groups(cls, groups: list[str]) -> list[dict]:
        """合并多个工具组的 schemas（复合指令路由用），按注册顺序去重"""
        seen: set[str] = set()
        result: list[dict] = []
        for group in groups:
            for name in cls._groups.get(group, []):
                if name not in seen:
                    seen.add(name)
                    result.append({"type": "function", "function": cls._registry[name]["schema"]})
        return result

    @classmethod
    def get_group_names(cls) -> list[str]:
        return list(cls._groups.keys())

    @classmethod
    def list_tools(cls) -> list[dict]:
        """列出所有已注册工具的简要信息（用于调试 / 前端展示）"""
        return [
            {
                "name": name,
                "description": info["schema"].get("description", ""),
                "group": info["group"],
                "meta": cls.get_tool_meta(name),
            }
            for name, info in cls._registry.items()
        ]

    # -------------- 执行 --------------

    @classmethod
    async def execute(cls, tool_name: str, arguments: str | dict, context: dict) -> str:
        """执行一个工具（带 Guardrails）"""
        if tool_name not in cls._registry:
            return json.dumps(
                {"success": False, "error": f"未知工具: {tool_name}，可用工具: {list(cls._registry.keys())}"},
                ensure_ascii=False,
            )

        if isinstance(arguments, str):
            try:
                args = json.loads(arguments)
            except json.JSONDecodeError:
                return json.dumps(
                    {"success": False, "error": f"参数 JSON 解析失败: {arguments[:100]}"},
                    ensure_ascii=False,
                )
        else:
            args = arguments

        handler = cls._registry[tool_name]["handler"]
        last_error: Optional[Exception] = None

        # 仅只读（safe）工具允许重试；写操作（warn/danger）失败即返回，
        # 防止"创建/发送/删除"类副作用被重复执行
        danger_level = cls.get_tool_meta(tool_name).get("danger_level", "safe")
        max_attempts = cls._max_retry + 1 if danger_level == "safe" else 1

        for attempt in range(1, max_attempts + 1):
            try:
                # handler 是同步阻塞函数，丢到线程池执行，避免阻塞事件循环
                result = await anyio.to_thread.run_sync(lambda: handler(**args, context=context))
                if not isinstance(result, str):
                    result = json.dumps(result, ensure_ascii=False, default=str)
                if attempt > 1:
                    logger.info(f"[ToolRegistry] 工具 {tool_name} 在第 {attempt} 次 retry 后成功")
                return result
            except Exception as e:
                last_error = e
                logger.warning(f"[ToolRegistry] 工具 {tool_name} 第 {attempt} 次执行失败: {e}")
                if attempt < max_attempts:
                    continue
                logger.exception(f"[ToolRegistry] 工具 {tool_name} 执行失败（danger_level={danger_level}）")

        return json.dumps(
            {"success": False, "error": f"工具 {tool_name} 执行失败: {str(last_error)}"},
            ensure_ascii=False,
        )
