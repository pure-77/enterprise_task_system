"""Agent 工具组 — 数据洞察 Tools（方案 4：一键总结 + 图表生成）

4 个工具：
- summarize_today_work   当日总结：完成任务 / 待办 / 打卡 / 日程
- summarize_week_progress 本周进展：完成率 / 逾期项 / 打卡情况
- summarize_task_status  任务状态分布（按范围统计，产出适合画图表的结构化数据）
- generate_chart         把数据渲染成图表（输出 ECharts option，前端直接挂载）

设计原则：
- 前 3 个是纯 SELECT 聚合查询（safe），不做任何写操作；
  返回结构化 dict，由 LLM 组织自然语言，也可以直接喂给 generate_chart 画图。
- generate_chart 也是 safe：不查库，只做确定性参数校验 + ECharts option 构造；
  数据由 LLM 从之前的查询结果中提取传入。
- 查询范围 = 当前空间内「当前用户可见」的任务，权限口径与 list_tasks 一致：
  个人空间 = 自己创建/被分配的任务；工作区普通成员 = 自己创建/被分配/团队公开；
  工作区 owner/admin = 空间全部任务。
"""
import json
import logging
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import or_, and_, case
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.user import User
from app.models.task import Task, TaskStatus, TaskPriority
from app.models.task_assignee import task_assignees

logger = logging.getLogger("agent.tools.summary")

# generate_chart 的规模上限（防止 LLM 传入过大的数据把结果撑爆 / 前端渲染卡顿）
_CHART_MAX_CATEGORIES = 24
_CHART_MAX_SERIES = 6


# ============================================================
# 公共查询辅助
# ============================================================

def _visible_task_query(db: Session, user: User, workspace_id):
    """构造「当前空间内当前用户可见」的任务查询（权限口径对齐 list_tasks / HTTP 层）

    Returns:
        (query, ws) — query 已应用空间 + 可见性过滤；ws 为归一化后的 workspace_id（None=个人空间）
    """
    ws = workspace_id if (workspace_id and workspace_id > 0) else None
    q = db.query(Task).filter(Task.is_active == True)

    if ws is None:
        # 个人空间：只看自己的个人任务
        q = q.filter(Task.workspace_id.is_(None))
        q = q.filter(or_(Task.user_id == user.id, Task.assignee_id == user.id))
    else:
        from app.core.permissions import get_workspace_member
        from app.models.workspace import WorkspaceRole
        member = get_workspace_member(ws, user.id, db)  # 非成员直接抛权限异常
        q = q.filter(Task.workspace_id == ws)
        if member.role == WorkspaceRole.MEMBER:
            # 普通成员：自己创建 / 分配给自己（单值+M2M）/ 团队公开
            q = q.filter(or_(
                Task.user_id == user.id,
                Task.assignee_id == user.id,
                Task.is_team_wide == True,
                Task.id.in_(
                    db.query(task_assignees.c.task_id).filter(task_assignees.c.user_id == user.id)
                ),
            ))
    return q, ws


def _task_brief(t: Task) -> dict:
    """任务简要信息（给 LLM 参考用）"""
    return {
        "id": t.id,
        "title": t.title,
        "status": t.status.value if hasattr(t.status, "value") else str(t.status),
        "priority": t.priority.value if hasattr(t.priority, "value") else str(t.priority) if t.priority else None,
        "deadline": t.due_date.strftime("%Y-%m-%d %H:%M") if t.due_date else None,
    }


# ============================================================
# 工具 1：summarize_today_work — 今日工作总结
# ============================================================

def _schema_summarize_today_work() -> dict:
    return {
        "name": "summarize_today_work",
        "description": "汇总用户今天的工作情况：已完成任务、进行中/待办任务、打卡记录、今日日程。"
                       "用户问「今天干了什么 / 总结一下今天 / 今日进展」时调用。",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    }


def _handler_summarize_today_work(context: dict = None) -> str:
    user: User = context["user"]
    db: Session = SessionLocal()
    try:
        now = datetime.now()
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        q, ws = _visible_task_query(db, user, context.get("workspace_id"))

        # 今日完成任务（按更新时间近似：今日被置为 completed 的任务）
        done_today = q.filter(
            Task.status == TaskStatus.COMPLETED,
            Task.updated_at >= day_start,
        ).order_by(Task.updated_at.desc()).limit(10).all()

        # 进行中 + 待办（当前快照）
        in_progress = q.filter(Task.status == TaskStatus.IN_PROGRESS)\
            .order_by(Task.due_date.asc()).limit(10).all()
        pending_count = q.filter(Task.status == TaskStatus.PENDING).count()

        # 今日打卡（个人空间通常无考勤规则，查不到即说明）
        from app.modules.attendance.models import AttendanceRecord
        att = db.query(AttendanceRecord).filter(
            AttendanceRecord.user_id == user.id,
            AttendanceRecord.date == now.date(),
        ).first()
        attendance = None
        if att:
            attendance = {
                "check_in": str(att.check_in_time)[:5] if att.check_in_time else None,
                "check_out": str(att.check_out_time)[:5] if att.check_out_time else None,
                "check_in_type": att.check_in_type.value if att.check_in_type else None,
            }

        # 今日日程（我创建的或我参与的）
        from app.modules.calendar.models import Event, EventAttendee
        day_end = day_start + timedelta(days=1)
        events = db.query(Event).filter(
            Event.start_time >= day_start,
            Event.start_time < day_end,
            or_(
                Event.created_by == user.id,
                Event.id.in_(
                    db.query(EventAttendee.event_id).filter(EventAttendee.user_id == user.id)
                ),
            ),
        ).order_by(Event.start_time.asc()).limit(10).all()

        return json.dumps({
            "success": True,
            "date": now.strftime("%Y-%m-%d"),
            "done_today_count": len(done_today),
            "done_today": [_task_brief(t) for t in done_today],
            "in_progress": [_task_brief(t) for t in in_progress],
            "pending_count": pending_count,
            "attendance": attendance,
            "events_today": [
                {"title": e.title, "start": e.start_time.strftime("%H:%M"), "location": e.location}
                for e in events
            ],
        }, ensure_ascii=False, default=str)
    except Exception as e:
        logger.exception("今日工作总结查询失败")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    finally:
        db.close()


# ============================================================
# 工具 2：summarize_week_progress — 本周进展
# ============================================================

def _schema_summarize_week_progress() -> dict:
    return {
        "name": "summarize_week_progress",
        "description": "汇总用户本周（周一至今）的工作进展：任务完成率、逾期任务、打卡出勤。"
                       "用户问「本周进展 / 这周做得怎么样 / 周报素材」时调用。",
        "parameters": {
            "type": "object",
            "properties": {},
        },
    }


def _handler_summarize_week_progress(context: dict = None) -> str:
    user: User = context["user"]
    db: Session = SessionLocal()
    try:
        now = datetime.now()
        week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)

        q, ws = _visible_task_query(db, user, context.get("workspace_id"))

        # 本周完成任务数（按更新时间近似）
        done_count = q.filter(
            Task.status == TaskStatus.COMPLETED,
            Task.updated_at >= week_start,
        ).count()
        # 本周新创建任务数
        created_count = q.filter(Task.created_at >= week_start).count()
        # 未完成任务数（用于算完成率的分母）
        open_count = q.filter(Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS])).count()
        completion_rate = round(done_count / (done_count + open_count) * 100, 1) if (done_count + open_count) else 0.0

        # 逾期任务：截止已过且未完成
        overdue = q.filter(
            Task.due_date.isnot(None),
            Task.due_date < now,
            Task.status.notin_([TaskStatus.COMPLETED, TaskStatus.CANCELLED]),
        ).order_by(Task.due_date.asc()).limit(5).all()

        # 本周打卡（考勤仅工作区有；个人空间查不到记录）
        from app.modules.attendance.models import AttendanceRecord, CheckInType
        records = db.query(AttendanceRecord).filter(
            AttendanceRecord.user_id == user.id,
            AttendanceRecord.date >= week_start.date(),
            AttendanceRecord.date <= now.date(),
        ).all()
        attendance = {
            "days": len(records),
            "late": sum(1 for r in records if r.check_in_type == CheckInType.LATE),
            "early_leave": sum(1 for r in records if r.check_out_type == CheckInType.EARLY),
        } if records else None

        return json.dumps({
            "success": True,
            "week_start": week_start.strftime("%Y-%m-%d"),
            "week_end": now.strftime("%Y-%m-%d"),
            "done_count": done_count,
            "created_count": created_count,
            "open_count": open_count,
            "completion_rate": completion_rate,
            "overdue_count": len(overdue),
            "overdue_top": [_task_brief(t) for t in overdue],
            "attendance": attendance,
        }, ensure_ascii=False, default=str)
    except Exception as e:
        logger.exception("本周进展查询失败")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    finally:
        db.close()


# ============================================================
# 工具 3：summarize_task_status — 任务状态/优先级分布（图表友好）
# ============================================================

def _schema_summarize_task_status() -> dict:
    return {
        "name": "summarize_task_status",
        "description": "统计任务的状态分布和优先级分布，返回结构化计数（适合直接喂给 generate_chart 画饼图/柱状图）。"
                       "用户问「任务都什么状态 / 待办有多少 / 优先级分布」或要画任务统计图表时调用。",
        "parameters": {
            "type": "object",
            "properties": {
                "scope": {
                    "type": "string",
                    "enum": ["mine", "created_by_me", "all"],
                    "description": "统计范围：mine=分配给我的（默认）；created_by_me=我创建的；all=当前空间内我可见的全部",
                },
            },
        },
    }


def _handler_summarize_task_status(scope: str = "mine", context: dict = None) -> str:
    user: User = context["user"]
    db: Session = SessionLocal()
    try:
        q, ws = _visible_task_query(db, user, context.get("workspace_id"))

        # scope 过滤（在可见性基础上再收窄）
        if scope == "mine":
            q = q.filter(or_(
                Task.assignee_id == user.id,
                Task.id.in_(db.query(task_assignees.c.task_id).filter(task_assignees.c.user_id == user.id)),
            ))
        elif scope == "created_by_me":
            q = q.filter(Task.user_id == user.id)
        # scope == "all" 不再额外过滤（可见性查询已按角色收口）

        now = datetime.now()
        rows = q.with_entities(Task.status, Task.priority, Task.due_date).all()

        status_labels = {
            TaskStatus.PENDING: "待办",
            TaskStatus.IN_PROGRESS: "进行中",
            TaskStatus.COMPLETED: "已完成",
            TaskStatus.CANCELLED: "已取消",
            TaskStatus.OVERDUE: "已逾期",
        }
        priority_labels = {
            TaskPriority.LOW: "低",
            TaskPriority.MEDIUM: "中",
            TaskPriority.HIGH: "高",
            TaskPriority.URGENT: "紧急",
        }
        by_status: dict[str, int] = {}
        by_priority: dict[str, int] = {}
        overdue_open = 0
        for status_val, priority_val, due_date in rows:
            s_label = status_labels.get(status_val, str(status_val))
            by_status[s_label] = by_status.get(s_label, 0) + 1
            p_label = priority_labels.get(priority_val, str(priority_val))
            by_priority[p_label] = by_priority.get(p_label, 0) + 1
            # 逾期口径：截止已过且未完成/未取消（含状态本身已标 overdue 的）
            if due_date and due_date < now and status_val not in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
                overdue_open += 1

        return json.dumps({
            "success": True,
            "scope": scope,
            "total": len(rows),
            "by_status": by_status,
            "by_priority": by_priority,
            "overdue_open": overdue_open,
        }, ensure_ascii=False, default=str)
    except Exception as e:
        logger.exception("任务状态分布统计失败")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    finally:
        db.close()


# ============================================================
# 工具 4：generate_chart — 生成图表（ECharts option，前端直接渲染）
# ============================================================

def _schema_generate_chart() -> dict:
    return {
        "name": "generate_chart",
        "description": "把统计数据渲染成图表。调用前先通过查询/总结工具拿到数据，再把数据整理为 "
                       "categories（类目）+ series（数值序列）传入。返回 ECharts 配置，前端会自动渲染成图表卡片。",
        "parameters": {
            "type": "object",
            "properties": {
                "chart_type": {
                    "type": "string",
                    "enum": ["bar", "line", "pie"],
                    "description": "图表类型：bar=柱状图（对比）；line=折线图（趋势）；pie=饼图（占比分布）",
                },
                "title": {
                    "type": "string",
                    "description": "图表标题，如「任务状态分布」",
                },
                "categories": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": f"类目列表（x 轴标签 / 饼图分项名），最多 {_CHART_MAX_CATEGORIES} 项，如 [\"待办\",\"进行中\",\"已完成\"]",
                },
                "series": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "序列名，如「任务数」"},
                            "data": {
                                "type": "array",
                                "items": {"type": "number"},
                                "description": "数值列表，长度必须与 categories 完全一致",
                            },
                        },
                        "required": ["name", "data"],
                    },
                    "description": f"数值序列，最多 {_CHART_MAX_SERIES} 个；饼图只使用第一个序列",
                },
            },
            "required": ["chart_type", "title", "categories", "series"],
        },
    }


def _build_echarts_option(chart_type: str, title: str, categories: list, series: list) -> dict:
    """确定性构造 ECharts option（不耗 LLM）"""
    option: dict = {
        "title": {"text": title, "left": "center", "textStyle": {"fontSize": 14}},
        "tooltip": {"trigger": "item" if chart_type == "pie" else "axis"},
        "legend": {"bottom": 0, "textStyle": {"fontSize": 12}},
        "color": ["#5470c6", "#91cc75", "#fac858", "#ee6666", "#73c0de", "#3ba272"],
    }
    if chart_type == "pie":
        s0 = series[0]
        option["series"] = [{
            "name": s0["name"],
            "type": "pie",
            "radius": ["35%", "65%"],
            "data": [{"name": c, "value": v} for c, v in zip(categories, s0["data"])],
            "label": {"formatter": "{b}: {c} ({d}%)"},
        }]
    else:
        option["grid"] = {"left": 45, "right": 20, "top": 45, "bottom": 45}
        option["xAxis"] = {"type": "category", "data": categories}
        option["yAxis"] = {"type": "value"}
        built = []
        for s in series:
            item = {"name": s["name"], "type": chart_type, "data": s["data"]}
            if chart_type == "line":
                item["smooth"] = True
                item["areaStyle"] = {"opacity": 0.12}
            elif chart_type == "bar":
                item["barMaxWidth"] = 36
                item["itemStyle"] = {"borderRadius": [4, 4, 0, 0]}
            built.append(item)
        option["series"] = built
    return option


def _handler_generate_chart(
    chart_type: str,
    title: str,
    categories: list,
    series: list,
    context: dict = None,
) -> str:
    """生成图表的 handler — 纯确定性校验 + option 构造，不查库"""
    try:
        # ---- 参数校验（LLM 传参可能不规范，逐条给出可纠正的错误信息）----
        if chart_type not in ("bar", "line", "pie"):
            return json.dumps({"success": False, "error": f"不支持的图表类型: {chart_type}（仅支持 bar/line/pie）"}, ensure_ascii=False)
        if not title or not str(title).strip():
            return json.dumps({"success": False, "error": "图表标题 title 不能为空"}, ensure_ascii=False)
        if not isinstance(categories, list) or not categories:
            return json.dumps({"success": False, "error": "categories 必须是非空数组"}, ensure_ascii=False)
        if len(categories) > _CHART_MAX_CATEGORIES:
            return json.dumps({"success": False, "error": f"类目过多（{len(categories)} 个），请合并到 {_CHART_MAX_CATEGORIES} 项以内"}, ensure_ascii=False)
        if not isinstance(series, list) or not series:
            return json.dumps({"success": False, "error": "series 必须是非空数组"}, ensure_ascii=False)
        if len(series) > _CHART_MAX_SERIES:
            return json.dumps({"success": False, "error": f"序列过多（{len(series)} 个），最多 {_CHART_MAX_SERIES} 个"}, ensure_ascii=False)

        clean_categories = [str(c) for c in categories]
        clean_series = []
        for i, s in enumerate(series):
            if not isinstance(s, dict) or "data" not in s:
                return json.dumps({"success": False, "error": f"series[{i}] 缺少 data 字段"}, ensure_ascii=False)
            data = s["data"]
            if not isinstance(data, list) or len(data) != len(clean_categories):
                return json.dumps({
                    "success": False,
                    "error": f"series[{i}]「{s.get('name', '?')}」的 data 长度（{len(data) if isinstance(data, list) else '非数组'}）"
                             f"与 categories 长度（{len(clean_categories)}）不一致，请修正后重试",
                }, ensure_ascii=False)
            try:
                clean_data = [float(v) for v in data]
            except (TypeError, ValueError):
                return json.dumps({"success": False, "error": f"series[{i}] 的 data 含非数值项，请只传数字"}, ensure_ascii=False)
            clean_series.append({"name": str(s.get("name") or f"序列{i + 1}"), "data": clean_data})

        option = _build_echarts_option(chart_type, str(title).strip(), clean_categories, clean_series)
        # compact JSON：结果要进 tool_call 记录（截断 4000），压缩体积给大数据留余量
        return json.dumps({
            "success": True,
            "result_type": "chart",
            "chart_type": chart_type,
            "title": str(title).strip(),
            "option": option,
            "message": f"图表「{title}」已生成，前端将自动渲染",
        }, ensure_ascii=False, separators=(",", ":"))
    except Exception as e:
        logger.exception("生成图表失败")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


# ============================================================
# 注册
# ============================================================

def register_summary_tools():
    from app.modules.agent.tool_registry import ToolRegistry

    ToolRegistry.register("summarize_today_work", _schema_summarize_today_work(), _handler_summarize_today_work, group="summary")
    ToolRegistry.register("summarize_week_progress", _schema_summarize_week_progress(), _handler_summarize_week_progress, group="summary")
    ToolRegistry.register("summarize_task_status", _schema_summarize_task_status(), _handler_summarize_task_status, group="summary")
    ToolRegistry.register("generate_chart", _schema_generate_chart(), _handler_generate_chart, group="summary")
