"""OA审批模块 — API 路由"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import get_current_user
from app.core.permissions import get_workspace_member
from app.models.user import User
from app.modules.approval.flow_engine import engine
from app.modules.approval.schemas import TemplateCreate, ApprovalSubmit, ApprovalAction, TransferAction, CCAdd
from app.core.exceptions import PermissionDeniedError, ResourceNotFoundError

router = APIRouter()


# ==================== 模板管理 ====================

@router.get("/templates")
async def get_templates(
    workspace_id: int = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_workspace_member(workspace_id, current_user.id, db)
    templates = engine.get_templates(db, workspace_id)
    return [{"id": t.id, "name": t.name, "icon": t.icon, "category": t.category,
             "description": t.description, "form_schema": t.form_schema,
             "flow_schema": t.flow_schema, "is_builtin": t.is_builtin,
             "created_at": t.created_at.isoformat() if t.created_at else None}
            for t in templates]


@router.post("/templates", status_code=201)
async def create_template(
    tmpl_in: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.models.workspace import WorkspaceRole
    member = get_workspace_member(tmpl_in.workspace_id, current_user.id, db)
    if member.role not in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN]:
        raise PermissionDeniedError(detail="需要管理员权限")

    t = engine.create_template(db, tmpl_in.workspace_id, current_user.id,
                               tmpl_in.name, tmpl_in.form_schema, tmpl_in.flow_schema,
                               tmpl_in.category, tmpl_in.description, tmpl_in.icon)
    return {"id": t.id, "name": t.name, "category": t.category}


# ==================== 审批实例 ====================

@router.post("/instances", status_code=201)
async def submit_approval(
    body: ApprovalSubmit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """提交审批 — 校验申请人是否为模板所属工作空间的成员"""
    # 先获取模板，校验工作空间成员资格
    from app.modules.approval.models import ApprovalTemplate
    tmpl = db.query(ApprovalTemplate).filter(
        ApprovalTemplate.id == body.template_id,
        ApprovalTemplate.is_active == True
    ).first()
    if not tmpl:
        raise ResourceNotFoundError(resource="审批模板")
    # 校验申请人是该工作空间成员
    get_workspace_member(tmpl.workspace_id, current_user.id, db)

    inst = engine.submit(db, body.template_id, current_user.id, body.title, body.form_data)
    return engine._format_instance(inst)


@router.get("/instances/pending")
async def pending_list(
    workspace_id: int = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_workspace_member(workspace_id, current_user.id, db)
    return engine.get_pending(db, current_user.id, workspace_id, page, page_size)


@router.get("/instances/my")
async def my_applications(
    workspace_id: int = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_workspace_member(workspace_id, current_user.id, db)
    return engine.get_my_applications(db, current_user.id, workspace_id, page, page_size)


@router.get("/instances/processed")
async def processed_list(
    workspace_id: int = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    get_workspace_member(workspace_id, current_user.id, db)
    return engine.get_processed(db, current_user.id, workspace_id, page, page_size)


@router.get("/instances/{instance_id}")
async def get_instance(
    instance_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取审批详情 — 校验查看权限（申请人/审批人/抄送人）"""
    inst = engine.get_detail(db, instance_id)
    # 权限校验：只有申请人、当前审批人、已处理审批人、抄送人可查看
    if not engine.can_view(db, inst, current_user.id):
        raise PermissionDeniedError(detail="无权查看该审批")
    return engine._format_instance(inst, current_user.id)


# ==================== 审批操作 ====================

@router.post("/instances/{instance_id}/approve")
async def approve(
    instance_id: int,
    body: ApprovalAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """通过 — 申请人不能审批自己"""
    inst = engine.approve(db, instance_id, body.node_id, current_user.id, body.comment)
    return engine._format_instance(inst)


@router.post("/instances/{instance_id}/reject")
async def reject(
    instance_id: int,
    body: ApprovalAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """驳回"""
    inst = engine.reject(db, instance_id, body.node_id, current_user.id, body.comment)
    return engine._format_instance(inst)


@router.post("/instances/{instance_id}/transfer")
async def transfer(
    instance_id: int,
    body: TransferAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """转交"""
    inst = engine.transfer(db, instance_id, body.node_id, current_user.id, body.to_user_id)
    return engine._format_instance(inst)


@router.post("/instances/{instance_id}/recall")
async def recall(
    instance_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """撤回 — 仅申请人"""
    inst = engine.recall(db, instance_id, current_user.id)
    return engine._format_instance(inst)


@router.post("/instances/{instance_id}/cancel")
async def cancel(
    instance_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """取消 — 仅申请人"""
    inst = engine.cancel(db, instance_id, current_user.id)
    return engine._format_instance(inst)


# ==================== 抄送 ====================

@router.post("/instances/{instance_id}/cc", status_code=201)
async def add_cc(
    instance_id: int,
    body: CCAdd,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """添加抄送 — 仅申请人或管理员"""
    inst = engine.get_detail(db, instance_id)
    if inst.applicant_id != current_user.id:
        # 非申请人需校验是否为管理员
        tmpl = inst.template
        if tmpl:
            member = get_workspace_member(tmpl.workspace_id, current_user.id, db)
            from app.models.workspace import WorkspaceRole
            if member.role not in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN]:
                raise PermissionDeniedError(detail="仅申请人或管理员可添加抄送")
    engine.add_cc(db, instance_id, body.user_ids)
    return {"message": "抄送已添加"}
