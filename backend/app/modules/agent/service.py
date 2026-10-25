"""Agent 模块 — 核心服务层（主循环）

串联所有组件的大脑：
  1. 加载对话记忆
  2. 意图识别 → 路由到对应模块工具组（避免单次 tools 过多）
  3. 调用 LLM → 处理 tool_calls → 执行工具 → 把结果回喂给 LLM（最多 N 轮）
  4. 最终回复写入记忆

主循环伪代码：
  while 迭代次数 < MAX:
      resp = llm.chat(messages + system_prompt, tools=当前模块的 tools)
      if resp.tool_calls:
          for tc in resp.tool_calls:
              exec_result = ToolRegistry.execute(tc.name, tc.args, context)
              messages.append(tool_result)  # 结果回喂
      else:
          break  # LLM 给出了最终自然语言回复
"""
import json
import logging
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

import anyio
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.db.redis_client import get_redis
from app.models.user import User
from app.models.agent_audit import AgentAuditLog
from app.modules.agent.llm_provider import get_llm, DeepSeekProvider
from app.modules.agent.tool_registry import ToolRegistry
from app.modules.agent.memory import AgentMemory
from app.modules.agent.schemas import AgentToolCall, AgentChatResponse
from app.modules.agent.session_service import AgentSessionService

logger = logging.getLogger("agent.service")

# 危险操作挂起确认的 Redis TTL（用户需在有效期内确认/取消，过期自动失效）
_CONFIRM_TTL_SECONDS = 300
# 危险操作挂起在 Redis 中的 key 前缀（与 router.py 保持一致）
_CONFIRM_REDIS_PREFIX = "agent:confirm:"


# ==================== 意图识别器（轻量版） ====================
# Phase 1 用关键字匹配 + LLM 辅助，足够覆盖主要场景
# Phase 2 可替换为专用的意图分类模型或 embeddings 相似度

# 关键字 → 模块名 映射（用于快速路由）
# H3: calendar 组拆成强匹配和时间词弱匹配，避免时间词"今天/明天"抢任务意图
# 复合指令（"建任务+发消息+约会"）时多组同时命中 → 合并加载多组工具
_KEYWORD_ROUTES: list[tuple[list[str], str]] = [
    # task 模块（"规划/拆解/排期"属于任务规划意图，路由到 task 组的 plan_tasks）
    (["任务", "todo", "待办", "task", "分配", "完成任务", "改状态", "规划", "拆解", "拆成", "排期"], "task"),
    # calendar 强匹配（肯定是日历；补"开会/例会/评审会"等常见会议说法）
    (["会议", "日程", "日历", "calendar", "schedule",
      "开会", "例会", "周会", "站会", "评审会", "讨论会", "复盘会"], "calendar_strong"),
    # calendar 时间词弱匹配（"今天开任务"不应被时间词抢）
    (["今天", "明天", "星期", "几点", "后天", "下周", "周一", "周二", "周三", "周四", "周五", "周六", "周日", "早上", "下午", "晚上"], "calendar_time"),
    # im 模块
    (["聊天", "发消息", "im", "消息", "群聊", "会话", "通知谁", "告诉"], "im"),
    # approval 模块
    (["审批", "请假", "报销", "申请", "approval"], "approval"),
    # attendance 模块
    (["打卡", "考勤", "上班", "下班", "attendance", "checkin"], "attendance"),
    # notification 模块
    (["通知", "提醒", "notification", "notif"], "notification"),
    # statistics 模块
    (["统计", "完成率", "趋势", "报表", "overview", "stats"], "statistics"),
    # summary 模块（数据洞察：总结 + 图表生成；"趋势图/图表"等带"图"字的归这里，纯"趋势"归 statistics）
    # 注意：不含"日报/周报"——"写周报"是创建任务的内容而非总结意图，单独出现时交给 Level 2 LLM 判断
    (["总结", "汇总", "进展", "图表", "柱状图", "饼图", "折线图", "趋势图", "盘点一下", "复盘一下"], "summary"),
    # file 模块
    (["文件", "文档", "file", "上传", "下载"], "file"),
    # org 模块
    (["成员", "部门", "同事", "组织", "架构", "org"], "org"),
    # announcement 模块
    (["公告", "通知公告", "announcement"], "announcement"),
    # knowledge 模块（RAG 知识库语义检索：文件/公告/聊天记录内容）
    # 注意：不含"资料"单字（"把资料发给张三"是 IM 意图），保留完整检索意图短语（查/搜/找+资料）
    (["知识库", "资料库", "资料里", "资料中", "文档里", "文件里", "公告里", "聊天里", "聊天记录里",
      "规章制度",
      "查资料", "搜资料", "找资料",
      "查一下资料", "搜一下资料", "找一下资料",
      "查下资料", "搜下资料", "找下资料",
      "knowledge"], "knowledge"),
]


def _route_intent(user_message: str) -> list[str] | str:
    """
    轻量意图识别 — 二级路由（支持复合指令多组命中）

    Level 1: 关键字匹配（零 LLM 调用）
    Level 2: LLM 兜底分类（标记 "llm_classify"，由主循环 await）

    返回值：
    - list[str]：命中的 1~N 个工具组（多组命中时主循环合并加载工具）
    - "llm_classify"：Level1 未命中任何关键字，需要 LLM 兜底

    H3 改进：时间词（今天/明天/几点）是弱信号，单独处理：
      - 先扫 task 强词 → 命中即收集 task
      - 再扫 calendar 强词（会议/日程/日历）→ 命中即收集 calendar
      - 时间词只有在「没有任何其他强信号」时才单独映射到 calendar，
        避免"明天建任务并发消息"被时间词稀释，也避免给复合句强塞日历工具
    """
    msg_lower = user_message.lower()
    matched: list[str] = []

    def _hit(keywords: list[str]) -> Optional[str]:
        for kw in keywords:
            if kw.lower() in msg_lower:
                return kw
        return None

    # Step 1: task 强词
    for keywords, group in _KEYWORD_ROUTES:
        if group == "task":
            kw = _hit(keywords)
            if kw:
                logger.info(f"[Intent] Level1-task强词 -> task (kw={kw})")
                matched.append("task")
            break

    # Step 2: calendar 强匹配
    for keywords, group in _KEYWORD_ROUTES:
        if group == "calendar_strong":
            kw = _hit(keywords)
            if kw:
                logger.info(f"[Intent] Level1-calendar强匹配 -> calendar (kw={kw})")
                matched.append("calendar")
            break

    # "通知张三，…/通知李四并…"是"给某人发消息"（IM），而不是"查看通知"。
    # 用正则识别人名式宾语；命中后归 im，并在下面跳过 notification 的泛化"通知"词。
    notify_person = bool(re.search(r"通知[\u4e00-\u9fa5]{1,3}(，|,|并|然后|一下|$)", msg_lower))
    if notify_person:
        logger.info("[Intent] Level1-通知+人名 -> im")
        matched.append("im")

    # Step 3: 其余业务组正常收集（复合指令可同时命中多个）
    for keywords, group in _KEYWORD_ROUTES:
        if group in ("task", "calendar_strong", "calendar_time"):
            continue
        # "通知张三"已归 im，泛化"通知"不再重复拉 notification 组
        if group == "notification" and notify_person and "通知" in msg_lower:
            keywords = [k for k in keywords if k != "通知"]
        kw = _hit(keywords)
        if kw:
            target = group
            logger.info(f"[Intent] Level1-关键字匹配 -> {target} (kw={kw})")
            matched.append(target)

    # Step 4: 没有任何强信号时，时间词弱匹配才生效（归一化成 calendar）
    if not matched:
        for keywords, group in _KEYWORD_ROUTES:
            if group == "calendar_time" and _hit(keywords):
                logger.info("[Intent] Level1-仅时间词弱匹配 -> calendar")
                return ["calendar"]

    if matched:
        # 去重保序
        seen: set[str] = set()
        return [g for g in matched if not (g in seen or seen.add(g))]

    # Level 2: LLM 兜底分类（异步调用需在外层 await）
    logger.info("[Intent] Level1 未命中，需要 Level2-LLM 兜底")
    return "llm_classify"


async def _llm_classify_intent(user_message: str) -> Optional[list[str]]:
    """
    异步意图分类 — 让 LLM 在已注册的工具组中选择匹配的分组（支持复合句返回多个）

    候选集必须来自「实际已注册的工具分组」（ToolRegistry.get_group_names），
    而不是 _KEYWORD_ROUTES 里的内部别名（calendar_strong/calendar_time 等），
    否则模型回答 calendar 时会因为不在候选集里被判为无效，路由白做。

    返回：
    - ["task", "im"] 等 1~N 个有效组名
    - None：无法判断（调用方降级为全量 tools）
    """
    registered_groups = ToolRegistry.get_group_names()
    intent_groups = sorted(set(registered_groups) | {"general"})
    candidates = ", ".join(intent_groups)

    prompt = f"""请判断用户意图匹配哪些模块分组？回答 1 个或多个组名（多个用英文逗号分隔），不能加引号。
候选分组: {candidates}
用户输入: "{user_message}"
判定规则：
- 创建/查询/更新/规划/拆解任务 → task
- 看/创建会议日程 → calendar
- 发消息/聊天 → im
- 打卡/查考勤 → attendance
- 看通知/提醒 → notification
- 查审批/请假/报销 → approval
- 看统计数据 → statistics
- 今日/本周工作总结、日报周报、把数据画成图表 → summary
- 找文件/文档 → file
- 查成员/部门 → org
- 查公告 → announcement
- 在文档/公告/聊天记录里找内容、查资料、规章制度 → knowledge
- 只有一句话包含多个不同操作（复合指令）时才返回多个组，例如"建任务并发消息再约会议"→ task, im, calendar
- 不确定就回答 general（给全量 tools）
只输出组名，不要解释。"""

    try:
        llm = DeepSeekProvider()
        resp = await llm.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,  # 低温度更稳定
        )
        raw = (resp.choices[0].message.content or "").strip().lower()
        # 兼容中英文逗号、顿号分隔
        parts = [p.strip() for p in raw.replace("，", ",").replace("、", ",").split(",") if p.strip()]
        groups = [p for p in parts if p in intent_groups and p != "general"]
        if groups:
            # 去重保序
            seen: set[str] = set()
            groups = [g for g in groups if not (g in seen or seen.add(g))]
            logger.info(f"[Intent] Level2-LLM 分类 -> groups={groups}")
            return groups
        logger.info(f"[Intent] Level2-LLM 返回 {raw} 无有效候选，降级为 all")
        return None
    except Exception as e:
        logger.warning(f"[Intent] Level2-LLM 分类失败: {e}，降级为 all")
        return None


# ==================== Agent 主服务 ====================

class AgentService:
    """Agent 核心服务 — 单次对话的编排器"""

    def __init__(
        self,
        user: User,
        workspace_id: Optional[int] = None,
        session_id: Optional[str] = None,
    ):
        self.user = user
        self.workspace_id = workspace_id
        self.session_id = session_id
        self.memory = AgentMemory(workspace_id, user.id, session_id)
        self.context = {"user": user, "workspace_id": workspace_id}

    # ============================================================
    # B2: chat_stream — 真正的 async generator，边跑边 yield 事件
    # ============================================================
    async def chat_stream(self, user_message: str, image_url: Optional[str] = None):
        """
        流式执行 Agent 对话，逐事件 yield：
          - {"event": "tool_call_start", "data": {...}}
          - {"event": "tool_call_done", "data": {...}}
          - {"event": "message", "data": "字符chunk"}
          - {"event": "done", "data": {...}}  # 带完整 _full 给 chat() 构造 response
          - {"event": "error", "data": {...}}
        """
        # ---------- 审计日志计时 ----------
        start_time = time.time()
        tool_calls_record: list[AgentToolCall] = []
        max_iterations = settings.AGENT_MAX_TOOL_ITERATIONS
        intent_group = None

        # ---------- Step 1: 加载记忆 + 构造 messages ----------
        history = await self.memory.load_with_summary()
        messages: list[dict] = []

        # System Prompt + 上下文注入
        now = datetime.now()
        weekdays = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        workspace_context = f"当前操作空间: workspace_id={self.workspace_id} (0=个人模式)"
        system_prompt = settings.AGENT_SYSTEM_PROMPT + f"""

【上下文】
- 现在时间: {now.strftime('%Y-%m-%d %H:%M:%S')} ({weekdays[now.weekday()]})
- 用户ID: {self.user.id}
- {workspace_context}
- 日期推断: 用户说"明天"=今天+1天, "后天"=+2天, "下周"=本周一+7天, 直接使用上面的"现在时间"推算即可, 不要询问用户。
- 时间推断: 用户说"6点"/"下午6点"=18:00, "早上6点"=06:00, "中午12点"=12:00。
- 所有工具调用都在这个空间范围内执行，无需询问用户要在哪个空间操作。"""
        messages.append({"role": "system", "content": system_prompt})

        # 历史对话（过滤脏消息：必须有合法 role，且无损坏的 tool_calls 结构）
        VALID_ROLES = {"system", "user", "assistant", "tool"}
        cleaned_history = []
        for h in history:
            if not isinstance(h, dict):
                continue
            if h.get("role") not in VALID_ROLES:
                continue
            # assistant 消息如果带了 tool_calls，检查每个元素必须有 id + type + function
            if h["role"] == "assistant" and h.get("tool_calls"):
                valid_tcs = []
                for tc in h["tool_calls"]:
                    if (isinstance(tc, dict)
                            and tc.get("id")
                            and tc.get("type") == "function"
                            and isinstance(tc.get("function"), dict)
                            and tc["function"].get("name")):
                        valid_tcs.append(tc)
                if valid_tcs:
                    h["tool_calls"] = valid_tcs
                elif "tool_calls" in h:
                    # tool_calls 全坏了，删掉 tool_calls 字段只保留 content
                    del h["tool_calls"]
            cleaned_history.append(h)
        messages.extend(cleaned_history)

        # 当前用户输入（多模态：图片走 OpenAI content parts 格式，不能作为顶层 key）
        current_user_msg = {"role": "user", "content": user_message}
        if image_url:
            current_user_msg["content"] = [
                {"type": "text", "text": user_message},
                {"type": "image_url", "image_url": {"url": image_url}},
            ]
        messages.append(current_user_msg)

        # ---------- Step 2: 意图识别 → 加载对应模块的 tools（支持复合指令多组） ----------
        intent_groups = _route_intent(user_message)

        # Level 2: LLM 兜底分类（关键字完全没命中时）
        if intent_groups == "llm_classify":
            intent_groups = await _llm_classify_intent(user_message)

        if not intent_groups:
            # 不确定意图时加载全部 tools
            tools = ToolRegistry.get_all_schemas()
            intent_group = "all"
        elif len(intent_groups) == 1:
            group = intent_groups[0]
            if group in ("general", "unknown"):
                tools = ToolRegistry.get_all_schemas()
                intent_group = "all"
            else:
                tools = ToolRegistry.get_schemas_by_group(group)
                if not tools:
                    # 分组为空（注册失败/分组名不匹配）时降级为全量 tools，避免死路
                    logger.warning(f"[Agent] 分组 {group} 无已注册工具，降级为全量 tools")
                    tools = ToolRegistry.get_all_schemas()
                    intent_group = "all"
                else:
                    intent_group = group
        else:
            # 复合指令：合并多个工具组，按注册顺序去重
            tools = ToolRegistry.get_schemas_by_groups(intent_groups)
            intent_group = "multi:" + "+".join(intent_groups)
            if not tools:
                logger.warning(f"[Agent] 分组 {intent_groups} 均无已注册工具，降级为全量 tools")
                tools = ToolRegistry.get_all_schemas()
                intent_group = "all"

        if not tools:
            # 极端情况：没有任何 tools 注册
            logger.warning("[Agent] 没有已注册的 tools")
            yield {"event": "done", "data": {
                "session_id": self.session_id or f"user:{self.user.id}",
                "model_used": "none",
                "total_tool_calls": 0,
                "_full": {
                    "reply": "抱歉，当前没有可用的工具，请联系管理员。",
                    "tool_calls": [],
                    "thinking": "",
                    "session_id": self.session_id or f"user:{self.user.id}",
                    "model_used": "none",
                }
            }}
            return

        # ---------- Step 3: 多模态检测 → 选择 LLM ----------
        # 把本轮实际可用的工具清单注入 system prompt，避免模型臆造未加载的工具名
        tool_names = [t["function"]["name"] for t in tools]
        if tool_names:
            messages[0]["content"] += (
                "\n\n【本轮可用工具】\n"
                + ", ".join(tool_names)
                + "\n只允许调用上面列出的工具；如果用户需要的能力不在其中，"
                  "请如实告知当前不具备该能力，不要臆造工具名。"
            )

        llm = get_llm(has_image=bool(image_url))
        logger.info(f"[Agent] 使用 LLM: {llm.model_name}, tools_count={len(tools)}, intent_group={intent_group}")

        # ---------- Step 4: 主循环 — LLM 推理 → 工具调用 → 结果回喂 ----------
        iteration = 0
        thinking_fragments: list[str] = []
        final_reply = ""

        while iteration < max_iterations:
            iteration += 1
            thinking_fragments.append(f"--- 第 {iteration} 轮 ---")

            # 调 LLM
            try:
                resp = await llm.chat(messages=messages, tools=tools)
            except Exception as e:
                logger.error(f"[Agent] LLM 调用失败 (iter={iteration}): {e}")
                # 如果 DS 失败，尝试降级到千问
                if "deepseek" in llm.model_name.lower():
                    logger.info("[Agent] 尝试降级到千问")
                    from app.modules.agent.llm_provider import QwenTextProvider
                    llm = QwenTextProvider()
                    try:
                        resp = await llm.chat(messages=messages, tools=tools)
                    except Exception as e2:
                        logger.error(f"[Agent] 千问也失败: {e2}")
                        final_reply = f"抱歉，AI 引擎暂时不可用，请稍后重试。\n(错误信息: {e})"
                        break
                else:
                    final_reply = f"抱歉，AI 引擎暂时不可用，请稍后重试。\n(错误信息: {e})"
                    break

            message = resp.choices[0].message
            thinking_fragments.append(f"LLM 回复: {message.content or '(tool_call)'}")

            # Case A: LLM 要调工具
            if message.tool_calls:
                # 把 assistant 的 tool_call 消息追加进 messages（OpenAI 要求格式）
                messages.append({
                    "role": "assistant",
                    "content": message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                        }
                        for tc in message.tool_calls
                    ],
                })

                # 逐个执行工具
                for tc in message.tool_calls:
                    tool_name = tc.function.name
                    tool_args = tc.function.arguments
                    parsed_args = json.loads(tool_args) if tool_args else {}
                    danger_level = ToolRegistry.get_tool_meta(tool_name).get("danger_level", "safe")

                    # ---- P1 方案3：danger 级工具执行前中断，挂起等待用户二次确认 ----
                    if danger_level == "danger":
                        thinking_fragments.append(f"⛔ 高风险工具挂起待确认: {tool_name}")
                        confirm_id = uuid.uuid4().hex[:16]
                        pending_action = {
                            "confirm_id": confirm_id,
                            "session_key": self.session_id or f"user:{self.user.id}",
                            "user_id": self.user.id,
                            "workspace_id": self.workspace_id or 0,
                            "tool_name": tool_name,
                            "tool_args": parsed_args,
                            "status": "pending",
                            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        }
                        try:
                            get_redis().setex(
                                f"{_CONFIRM_REDIS_PREFIX}{confirm_id}",
                                _CONFIRM_TTL_SECONDS,
                                json.dumps(pending_action, ensure_ascii=False),
                            )
                            # 实时推送确认请求（前端可即时渲染确认卡片）
                            yield {"event": "confirm_request", "data": {
                                "confirm_id": confirm_id,
                                "tool_name": tool_name,
                                "tool_args": parsed_args,
                                "meta": ToolRegistry.get_tool_meta(tool_name),
                                "expires_in_seconds": _CONFIRM_TTL_SECONDS,
                            }}
                            exec_result = json.dumps({
                                "success": False,
                                "pending_confirmation": True,
                                "confirm_id": confirm_id,
                                "tool_name": tool_name,
                                "expires_in_seconds": _CONFIRM_TTL_SECONDS,
                                "message": "该操作为高风险操作，已暂停并等待用户在确认卡片上确认。"
                                           "请告知用户：确认后才会执行；用户取消或超时未处理则不会执行。",
                            }, ensure_ascii=False)
                        except Exception as e:
                            # Redis 不可用 → 无法挂起确认流程，出于安全原则拒绝执行危险操作
                            logger.error(f"[Agent] 危险操作挂起失败（Redis 不可用），拒绝执行 {tool_name}: {e}")
                            exec_result = json.dumps({
                                "success": False,
                                "error": "确认服务暂不可用（存储未连接），出于安全考虑该高风险操作未执行，请稍后重试",
                            }, ensure_ascii=False)

                        tc_record = AgentToolCall(
                            tool_name=tool_name,
                            arguments=parsed_args,
                            result=exec_result[:4000],
                            success=False,
                        )
                        tool_calls_record.append(tc_record)
                        yield {"event": "tool_call_done", "data": {
                            "tool_name": tool_name,
                            "iteration": iteration,
                            "success": False,
                            "tool_call": tc_record.model_dump(),
                        }}
                        # 回喂 LLM：让它组织语言告知用户需要确认（而不是继续盲目推进）
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": exec_result,
                        })
                        continue

                    thinking_fragments.append(f"🔧 执行工具: {tool_name}")

                    # === B2: yield tool_call_start 事件 ===
                    yield {"event": "tool_call_start", "data": {
                        "tool_name": tool_name,
                        "iteration": iteration,
                        "tool_args": json.loads(tool_args) if tool_args else {},
                    }}

                    exec_result = await ToolRegistry.execute(tool_name, tool_args, self.context)

                    # 记录
                    # H2: 解析 JSON 看 success 字段，fallback 看 error 字段
                    is_success = True
                    try:
                        parsed = json.loads(exec_result or "{}")
                        if "success" in parsed:
                            is_success = bool(parsed["success"])
                        elif "error" in parsed:
                            is_success = False
                    except (json.JSONDecodeError, TypeError):
                        # 不是 JSON 字符串的兜底：有 "error" 字样就判失败
                        is_success = "error" not in (exec_result or "").lower()
                    tc_record = AgentToolCall(
                        tool_name=tool_name,
                        arguments=json.loads(tool_args) if tool_args else {},
                        result=exec_result[:4000],  # 截断太长的结果（4000 以容纳 ECharts option 图表配置）
                        success=is_success,
                    )
                    tool_calls_record.append(tc_record)

                    # === B2: yield tool_call_done 事件 ===
                    yield {"event": "tool_call_done", "data": {
                        "tool_name": tool_name,
                        "iteration": iteration,
                        "success": is_success,
                        "tool_call": tc_record.model_dump(),
                    }}

                    # 把工具结果回喂给 LLM
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": exec_result,
                    })

            # Case B: LLM 给出了最终自然语言回复
            else:
                final_reply = message.content or ""
                thinking_fragments.append(f"✅ 最终回复")
                break

        # ---------- Step 5: 如果耗尽迭代轮次还没拿到回复 ----------
        else:
            logger.warning(f"[Agent] 达到最大迭代次数 {max_iterations}，强制返回最后结果")
            final_reply = message.content or "抱歉，我处理了很多步骤但还是没能完全回答你的问题。你能说得更具体一些吗？"

        # ---------- Step 6: 保存记忆 ----------
        # 同步 Redis/DB 操作放到线程池执行，避免阻塞事件循环
        await anyio.to_thread.run_sync(lambda: self.memory.save(user_message, final_reply, image_url))

        # ---------- Step 7: 持久化到 MySQL（会话列表 + 完整消息历史）----------
        resolved_session_key = self.session_id or f"user:{self.user.id}"

        def _persist_to_mysql() -> Optional[int]:
            db = SessionLocal()
            try:
                session_title = user_message[:20] if len(user_message) >= 20 else user_message
                db_session = AgentSessionService.get_or_create_session(
                    db,
                    user=self.user,
                    workspace_id=self.workspace_id or 0,
                    session_key=resolved_session_key,
                    title=session_title,
                )
                AgentSessionService.append_message(
                    db, db_session,
                    role="user", content=user_message,
                    image_url=image_url,
                )
                AgentSessionService.append_message(
                    db, db_session,
                    role="assistant", content=final_reply,
                    tool_calls=[tc.model_dump() for tc in tool_calls_record] if tool_calls_record else None,
                    thinking=thinking_fragments[-1] if thinking_fragments else None,
                )
                db_session.model_used = llm.model_name
                db.commit()
                return db_session.id
            finally:
                db.close()

        try:
            _db_session_id = await anyio.to_thread.run_sync(_persist_to_mysql)
            logger.info(f"[AgentSession] 已持久化 session={_db_session_id}")
        except Exception as e:
            logger.warning(f"[AgentSession] MySQL 持久化失败（不影响主流程）: {e}")

        # ---------- Step 8: 写入审计日志 ----------
        duration_ms = int((time.time() - start_time) * 1000)
        success_count = sum(1 for tc in tool_calls_record if tc.success)
        fail_count = len(tool_calls_record) - success_count

        def _write_audit() -> None:
            db = SessionLocal()
            try:
                audit_log = AgentAuditLog(
                    user_id=self.user.id,
                    workspace_id=self.workspace_id or 0,
                    # 存 resolved session_key，与 MySQL AgentSession.session_key 语义一致
                    session_id=resolved_session_key[:64],
                    user_message=user_message,
                    tool_calls=[tc.model_dump() for tc in tool_calls_record],
                    tool_call_count=len(tool_calls_record),
                    success_count=success_count,
                    fail_count=fail_count,
                    reply=final_reply[:2000],
                    model_used=llm.model_name,
                    intent_group=intent_group or "unknown",
                    duration_ms=duration_ms,
                )
                db.add(audit_log)
                db.commit()
            finally:
                db.close()

        try:
            await anyio.to_thread.run_sync(_write_audit)
            logger.info(f"[AgentAudit] 已记录: tool_calls={len(tool_calls_record)}, duration={duration_ms}ms, intent={intent_group}")
        except Exception as e:
            logger.warning(f"[AgentAudit] 写入失败（不影响主流程）: {e}")

        # === B2: yield 最终回复（逐 chunk，供 SSE 打字机效果）===
        chunk_size = 2
        for i in range(0, len(final_reply), chunk_size):
            yield {"event": "message", "data": final_reply[i:i + chunk_size]}

        # === B2: yield done 事件，带完整 _full 给 chat() 构造 AgentChatResponse ===
        yield {"event": "done", "data": {
            "session_id": self.session_id or f"user:{self.user.id}",
            "model_used": llm.model_name,
            "total_tool_calls": len(tool_calls_record),
            "_full": {
                "reply": final_reply,
                "tool_calls": [tc.model_dump() for tc in tool_calls_record],
                "thinking": "\n".join(thinking_fragments),
                "session_id": self.session_id or f"user:{self.user.id}",
                "model_used": llm.model_name,
            }
        }}

    # ============================================================
    # chat — 非流式，内部调用 chat_stream 收集完整结果
    # ============================================================
    async def chat(self, user_message: str, image_url: Optional[str] = None) -> AgentChatResponse:
        """执行一次完整的 Agent 对话（非流式）"""
        final_reply = ""
        final_data = None
        final_tool_calls: list[AgentToolCall] = []

        async for event in self.chat_stream(user_message, image_url):
            ev = event["event"]
            if ev == "tool_call_done":
                final_tool_calls.append(AgentToolCall(**event["data"]["tool_call"]))
            elif ev == "message":
                final_reply += event["data"]
            elif ev == "done":
                final_data = event["data"]["_full"]

        if final_data is None:
            # 理论上不会走到，chat_stream 一定会 yield done
            return AgentChatResponse(
                reply=final_reply or "抱歉，处理失败，请重试。",
                tool_calls=final_tool_calls,
                session_id=self.session_id or f"user:{self.user.id}",
                model_used="unknown",
            )

        return AgentChatResponse(
            reply=final_data["reply"],
            tool_calls=final_tool_calls or [AgentToolCall(**tc) for tc in final_data["tool_calls"]],
            thinking=final_data["thinking"],
            session_id=final_data["session_id"],
            model_used=final_data["model_used"],
        )
