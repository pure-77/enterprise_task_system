"""Agent 工具组 — 审批 + 组织架构 + 统计 + 文件 Tools"""
import json
import logging

from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.user import User

logger = logging.getLogger("agent.tools.misc")


# ==================== Approval ====================

def _schema_my_approvals() -> dict:
    return {
        "name": "list_my_approvals",
        "description": "查询审批实例列表（待我审批/我发起的/已处理的）。",
        "parameters": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["pending", "my", "processed"], "description": "pending=待我审批, my=我发起的, processed=已处理", "default": "pending"},
                "workspace_id": {"type": "integer", "description": "workspace ID（可选，从上下文取）"},
                "limit": {"type": "integer", "description": "条数，默认 20", "default": 20},
            },
        },
    }


def _handler_my_approvals(type: str = "pending", workspace_id: int = None, limit: int = 20, context: dict = None) -> str:
    user: User = context["user"]
    db = SessionLocal()
    try:
        if workspace_id is None:
            workspace_id = context.get("workspace_id")
        limit = min(limit, 50)
        from app.modules.approval.flow_engine import engine
        page_size = limit
        if type == "pending":
            result = engine.get_pending(db, user_id=user.id, workspace_id=workspace_id, page_size=page_size)
        elif type == "my":
            result = engine.get_my_applications(db, user_id=user.id, workspace_id=workspace_id, page_size=page_size)
        else:
            result = engine.get_processed(db, user_id=user.id, workspace_id=workspace_id, page_size=page_size)
        items = result.get("items", []) if isinstance(result, dict) else []
        return json.dumps({"success": True, "type": type, "count": len(items), "items": items[:20]}, ensure_ascii=False, default=str)
    except Exception as e:
        logger.exception("查询审批失败")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    finally:
        db.close()


# ---- 提交审批 ----

def _schema_submit_approval() -> dict:
    return {
        "name": "submit_approval",
        "description": "提交一个新的审批申请（请假、报销、用章等）。需要审批模板 ID 和标题，form_data 放具体字段。",
        "parameters": {
            "type": "object",
            "properties": {
                "template_id": {"type": "integer", "description": "审批模板 ID"},
                "title": {"type": "string", "description": "审批标题，如「张三请假申请-3天」"},
                "form_data": {"type": "object", "description": "表单字段，如 {\"leave_days\": 3, \"reason\": \"身体不适\"}"},
            },
            "required": ["template_id", "title"],
        },
    }


def _handler_submit_approval(template_id: int, title: str, form_data: dict = None, context: dict = None) -> str:
    user: User = context["user"]
    db = SessionLocal()
    try:
        from app.modules.approval.flow_engine import engine
        inst = engine.submit(db, template_id=template_id, applicant_id=user.id,
                             title=title, form_data=form_data or {})
        return json.dumps({
            "success": True,
            "instance_id": inst.id,
            "title": inst.title,
            "status": str(inst.status),
            "message": f"审批「{inst.title}」已提交（instance_id={inst.id}）",
        }, ensure_ascii=False, default=str)
    except Exception as e:
        logger.exception("提交审批失败")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    finally:
        db.close()


# ---- 审批通过/驳回 ----

def _schema_approve_approval() -> dict:
    return {
        "name": "approve_approval",
        "description": "审批通过某个待办（作为审批人）。只需 instance_id，自动找到当前用户在该实例上的待办节点。",
        "parameters": {
            "type": "object",
            "properties": {
                "instance_id": {"type": "integer", "description": "审批实例 ID"},
                "comment": {"type": "string", "description": "审批意见（可选）"},
            },
            "required": ["instance_id"],
        },
    }


def _handler_approve_approval(instance_id: int, comment: str = None, context: dict = None) -> str:
    user: User = context["user"]
    db = SessionLocal()
    try:
        from app.modules.approval.flow_engine import engine
        from app.modules.approval.models import ApprovalNode, NodeStatus, ApprovalInstance
        from app.core.permissions import get_workspace_member
        # 权限收口：先校验实例所属空间 + 当前用户是空间成员
        inst_row = db.query(ApprovalInstance).filter(ApprovalInstance.id == instance_id).first()
        if not inst_row:
            return json.dumps({"success": False, "error": f"审批实例 {instance_id} 不存在"}, ensure_ascii=False)
        get_workspace_member(inst_row.workspace_id, user.id, db)
        # 自动找当前用户在该实例上的待办节点
        node = db.query(ApprovalNode).filter(
            ApprovalNode.instance_id == instance_id,
            ApprovalNode.approver_id == user.id,
            ApprovalNode.status == NodeStatus.PENDING,
        ).first()
        if not node:
            return json.dumps({"success": False, "error": f"你在审批实例 {instance_id} 上没有待办节点"}, ensure_ascii=False)
        inst = engine.approve(db, instance_id=instance_id, node_id=node.id,
                              approver_id=user.id, comment=comment)
        return json.dumps({
            "success": True,
            "instance_id": inst.id,
            "status": str(inst.status),
            "message": f"审批已通过，当前状态: {inst.status}",
        }, ensure_ascii=False, default=str)
    except Exception as e:
        logger.exception("审批通过失败")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    finally:
        db.close()


def _schema_reject_approval() -> dict:
    return {
        "name": "reject_approval",
        "description": "驳回某个待办审批。只需 instance_id，自动找到当前用户的待办节点。",
        "parameters": {
            "type": "object",
            "properties": {
                "instance_id": {"type": "integer", "description": "审批实例 ID"},
                "comment": {"type": "string", "description": "驳回理由（可选）"},
            },
            "required": ["instance_id"],
        },
    }


def _handler_reject_approval(instance_id: int, comment: str = None, context: dict = None) -> str:
    user: User = context["user"]
    db = SessionLocal()
    try:
        from app.modules.approval.flow_engine import engine
        from app.modules.approval.models import ApprovalNode, NodeStatus, ApprovalInstance
        from app.core.permissions import get_workspace_member
        # 权限收口：先校验实例所属空间 + 当前用户是空间成员
        inst_row = db.query(ApprovalInstance).filter(ApprovalInstance.id == instance_id).first()
        if not inst_row:
            return json.dumps({"success": False, "error": f"审批实例 {instance_id} 不存在"}, ensure_ascii=False)
        get_workspace_member(inst_row.workspace_id, user.id, db)
        node = db.query(ApprovalNode).filter(
            ApprovalNode.instance_id == instance_id,
            ApprovalNode.approver_id == user.id,
            ApprovalNode.status == NodeStatus.PENDING,
        ).first()
        if not node:
            return json.dumps({"success": False, "error": f"你在审批实例 {instance_id} 上没有待办节点"}, ensure_ascii=False)
        inst = engine.reject(db, instance_id=instance_id, node_id=node.id,
                             approver_id=user.id, comment=comment)
        return json.dumps({
            "success": True,
            "instance_id": inst.id,
            "status": str(inst.status),
            "message": f"审批已驳回",
        }, ensure_ascii=False, default=str)
    except Exception as e:
        logger.exception("驳回审批失败")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    finally:
        db.close()


def register_approval_tools():
    from app.modules.agent.tool_registry import ToolRegistry
    ToolRegistry.register("list_my_approvals", _schema_my_approvals(), _handler_my_approvals, group="approval")
    ToolRegistry.register("submit_approval", _schema_submit_approval(), _handler_submit_approval, group="approval")
    ToolRegistry.register("approve_approval", _schema_approve_approval(), _handler_approve_approval, group="approval")
    ToolRegistry.register("reject_approval", _schema_reject_approval(), _handler_reject_approval, group="approval")
    logger.info("[Agent] approval 模块 4 个工具已注册")


# ==================== Statistics ====================

def _schema_get_stats() -> dict:
    return {
        "name": "get_statistics_overview",
        "description": "获取用户数据统计概览（任务完成率、数量分布等）。",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "integer", "description": "workspace ID（可选）"},
            },
        },
    }


def _handler_get_stats(workspace_id: int = None, context: dict = None) -> str:
    user: User = context["user"]
    db = SessionLocal()
    try:
        if workspace_id is None:
            workspace_id = context.get("workspace_id")
        from app.crud.statistics import statistics_crud
        data = statistics_crud.get_overview(db, user_id=user.id, workspace_id=workspace_id)
        return json.dumps({"success": True, "data": data}, ensure_ascii=False, default=str)
    except Exception as e:
        logger.exception("统计查询失败")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    finally:
        db.close()


def register_statistics_tools():
    from app.modules.agent.tool_registry import ToolRegistry
    ToolRegistry.register("get_statistics_overview", _schema_get_stats(), _handler_get_stats, group="statistics")
    logger.info("[Agent] statistics 模块 1 个工具已注册")


# ==================== Org ====================

def _schema_list_members() -> dict:
    return {
        "name": "list_workspace_members",
        "description": "查询 workspace 的成员列表（姓名、角色）。",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "integer", "description": "workspace ID（可选，从上下文取）"},
            },
        },
    }


def _handler_list_members(workspace_id: int = None, context: dict = None) -> str:
    db = SessionLocal()
    try:
        if workspace_id is None:
            workspace_id = context.get("workspace_id")
        if workspace_id is None:
            return json.dumps({"success": False, "error": "缺少 workspace_id"}, ensure_ascii=False)

        # H1: 先校验成员身份
        from app.core.permissions import get_workspace_member
        user: User = context["user"]
        get_workspace_member(workspace_id, user.id, db)  # 非成员会抛异常

        from app.models.workspace import WorkspaceMember
        members = db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.is_active == True,
        ).all()
        result = []
        for m in members or []:
            user_obj = db.query(User).filter(User.id == m.user_id).first()
            display_name = None
            if user_obj:
                display_name = user_obj.nickname or user_obj.real_name or user_obj.email
            result.append({
                "user_id": m.user_id,
                "name": display_name or "未知用户",
                "email": user_obj.email if user_obj else None,
                "role": m.role,
            })
        return json.dumps({"success": True, "workspace_id": workspace_id, "count": len(result), "items": result}, ensure_ascii=False)
    except Exception as e:
        logger.exception("查询成员失败")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    finally:
        db.close()


# ---- 部门列表 ----

def _schema_list_departments() -> dict:
    return {
        "name": "list_departments",
        "description": "查询 workspace 的部门树（层级结构）。",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "integer", "description": "workspace ID（可选，从上下文取）"},
            },
        },
    }


def _handler_list_departments(workspace_id: int = None, context: dict = None) -> str:
    db = SessionLocal()
    try:
        if workspace_id is None:
            workspace_id = context.get("workspace_id")
        if workspace_id is None:
            return json.dumps({"success": False, "error": "缺少 workspace_id"}, ensure_ascii=False)

        # H1: 先校验成员身份
        from app.core.permissions import get_workspace_member
        user: User = context["user"]
        get_workspace_member(workspace_id, user.id, db)

        from app.modules.org.crud import department_crud
        tree = department_crud.get_tree(db, workspace_id=workspace_id)
        return json.dumps({"success": True, "workspace_id": workspace_id, "tree": tree}, ensure_ascii=False, default=str)
    except Exception as e:
        logger.exception("查询部门失败")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    finally:
        db.close()


# ---- 职位列表 ----

def _schema_list_positions() -> dict:
    return {
        "name": "list_positions",
        "description": "查询 workspace 的职位列表。",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "integer", "description": "workspace ID（可选，从上下文取）"},
            },
        },
    }


def _handler_list_positions(workspace_id: int = None, context: dict = None) -> str:
    db = SessionLocal()
    try:
        if workspace_id is None:
            workspace_id = context.get("workspace_id")
        if workspace_id is None:
            return json.dumps({"success": False, "error": "缺少 workspace_id"}, ensure_ascii=False)

        # H1: 先校验成员身份
        from app.core.permissions import get_workspace_member
        user: User = context["user"]
        get_workspace_member(workspace_id, user.id, db)

        from app.modules.org.crud import position_crud
        positions = position_crud.get_list(db, workspace_id=workspace_id)
        items = [{"id": p.id, "name": p.name, "sort_order": p.sort_order} for p in positions]
        return json.dumps({"success": True, "workspace_id": workspace_id, "items": items}, ensure_ascii=False)
    except Exception as e:
        logger.exception("查询职位失败")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    finally:
        db.close()


def register_org_tools():
    from app.modules.agent.tool_registry import ToolRegistry
    ToolRegistry.register("list_workspace_members", _schema_list_members(), _handler_list_members, group="org")
    ToolRegistry.register("list_departments", _schema_list_departments(), _handler_list_departments, group="org")
    ToolRegistry.register("list_positions", _schema_list_positions(), _handler_list_positions, group="org")
    logger.info("[Agent] org 模块 3 个工具已注册")


# ==================== File ====================

def _schema_search_files() -> dict:
    return {
        "name": "search_files",
        "description": "列出 workspace 下的文件（支持关键词过滤）。",
        "parameters": {
            "type": "object",
            "properties": {
                "workspace_id": {"type": "integer", "description": "workspace ID（可选）"},
                "keyword": {"type": "string", "description": "搜索文件名关键词（可选）"},
                "limit": {"type": "integer", "description": "条数，默认 20", "default": 20},
            },
        },
    }


def _handler_search_files(workspace_id: int = None, keyword: str = None, limit: int = 20, context: dict = None) -> str:
    db = SessionLocal()
    try:
        if workspace_id is None:
            workspace_id = context.get("workspace_id")
        ws = workspace_id if (workspace_id and workspace_id > 0) else None
        if ws is None:
            return json.dumps({"success": False, "error": "查询文件需要指定工作空间"}, ensure_ascii=False)
        # 权限收口：必须是该空间成员
        from app.core.permissions import get_workspace_member
        user: User = context["user"]
        get_workspace_member(ws, user.id, db)
        limit = min(limit, 50)
        from app.modules.file.crud import file_crud
        result = file_crud.get_files(db, workspace_id=ws, page_size=limit)
        items = result.get("items", []) if isinstance(result, dict) else []
        if keyword:
            items = [f for f in items if keyword.lower() in (f.get("name", "") or "").lower()]
        return json.dumps({"success": True, "count": len(items), "items": items[:limit]}, ensure_ascii=False, default=str)
    except Exception as e:
        logger.exception("搜索文件失败")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    finally:
        db.close()


# ---- 文件详情 ----

def _schema_get_file_detail() -> dict:
    return {
        "name": "get_file_detail",
        "description": "查询文件详情（文件名、大小、上传者、下载链接）。需要文件 ID。",
        "parameters": {
            "type": "object",
            "properties": {
                "file_id": {"type": "integer", "description": "文件 ID"},
            },
            "required": ["file_id"],
        },
    }


def _handler_get_file_detail(file_id: int, context: dict = None) -> str:
    db = SessionLocal()
    try:
        from app.modules.file.crud import file_crud
        from app.core.permissions import get_workspace_member
        user: User = context["user"]
        f = file_crud.get_file(db, file_id=file_id)
        # 权限收口：必须是文件所属空间的成员，否则可读任意文件元数据
        get_workspace_member(f.workspace_id, user.id, db)
        return json.dumps({
            "success": True,
            "id": f.id,
            "name": f.name,
            "size": f.size,
            "mime_type": f.mime_type,
            "version": f.version,
            "folder_id": f.folder_id,
            "workspace_id": f.workspace_id,
            "uploader_id": f.uploader_id,
            "url": f"/uploads/files/{f.workspace_id}/{f.path}",
            "created_at": f.created_at.isoformat() if f.created_at else None,
        }, ensure_ascii=False, default=str)
    except Exception as e:
        logger.exception("查询文件详情失败")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    finally:
        db.close()


# ---- 删除文件 ----

def _schema_delete_file() -> dict:
    return {
        "name": "delete_file",
        "description": "删除一个文件（软删除 + 物理删除存储）。",
        "parameters": {
            "type": "object",
            "properties": {
                "file_id": {"type": "integer", "description": "文件 ID"},
            },
            "required": ["file_id"],
        },
    }


def _handler_delete_file(file_id: int, context: dict = None) -> str:
    db = SessionLocal()
    user: User = context["user"]
    try:
        from app.modules.file.crud import file_crud
        from app.core.permissions import get_workspace_member
        f = file_crud.get_file(db, file_id=file_id)
        # 权限收口：必须是文件所属空间的成员 + 上传者本人
        get_workspace_member(f.workspace_id, user.id, db)
        if f.uploader_id != user.id:
            return json.dumps({"success": False, "error": "只有上传者可以删除该文件"}, ensure_ascii=False)
        file_crud.delete_file(db, file_id=file_id)
        return json.dumps({"success": True, "message": f"文件「{f.name}」已删除"}, ensure_ascii=False)
    except Exception as e:
        logger.exception("删除文件失败")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    finally:
        db.close()


# ---- 创建文件夹 ----

def _schema_create_folder() -> dict:
    return {
        "name": "create_folder",
        "description": "在 workspace 下创建一个文件夹。",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "文件夹名称"},
                "workspace_id": {"type": "integer", "description": "workspace ID（可选，从上下文取）"},
                "parent_id": {"type": "integer", "description": "父文件夹 ID，NULL=根目录"},
            },
            "required": ["name"],
        },
    }


def _handler_create_folder(name: str, workspace_id: int = None, parent_id: int = None, context: dict = None) -> str:
    db = SessionLocal()
    user: User = context["user"]
    try:
        if workspace_id is None:
            workspace_id = context.get("workspace_id")
        ws = workspace_id if (workspace_id and workspace_id > 0) else None
        if ws is None:
            return json.dumps({"success": False, "error": "创建文件夹需要指定工作空间"}, ensure_ascii=False)
        # 权限收口：必须是该空间成员
        from app.core.permissions import get_workspace_member
        get_workspace_member(ws, user.id, db)
        from app.modules.file.crud import file_crud
        folder = file_crud.create_folder(db, workspace_id=ws, name=name,
                                         parent_id=parent_id, created_by=user.id)
        return json.dumps({
            "success": True,
            "folder_id": folder.id,
            "name": folder.name,
            "message": f"文件夹「{folder.name}」已创建",
        }, ensure_ascii=False)
    except Exception as e:
        logger.exception("创建文件夹失败")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)
    finally:
        db.close()


def register_file_tools():
    from app.modules.agent.tool_registry import ToolRegistry
    ToolRegistry.register("search_files", _schema_search_files(), _handler_search_files, group="file")
    ToolRegistry.register("get_file_detail", _schema_get_file_detail(), _handler_get_file_detail, group="file")
    ToolRegistry.register("delete_file", _schema_delete_file(), _handler_delete_file, group="file")
    ToolRegistry.register("create_folder", _schema_create_folder(), _handler_create_folder, group="file")
    logger.info("[Agent] file 模块 4 个工具已注册")
