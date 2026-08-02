"""OA审批模块 — 审批流引擎 + CRUD"""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from app.modules.approval.models import (
    ApprovalTemplate, ApprovalInstance, ApprovalNode, ApprovalCC,
    ApprovalStatus, NodeStatus
)
from app.core.exceptions import ResourceNotFoundError, PermissionDeniedError, BusinessError
from app.db.base import get_beijing_time


# ==================== 内置审批模板（按分类预置表单字段） ====================
# form_schema 字段类型: input/textarea/number/date/datetime/select/money
BUILTIN_TEMPLATES = [
    {
        "name": "请假审批",
        "icon": "Calendar",
        "category": "leave",
        "description": "事假/病假/年假/婚假/产假等假期申请",
        "form_schema": {
            "fields": [
                {"key": "leave_type", "label": "请假类型", "type": "select",
                 "options": ["事假", "病假", "年假", "婚假", "产假", "调休"], "required": True},
                {"key": "start_time", "label": "开始时间", "type": "datetime", "required": True},
                {"key": "end_time", "label": "结束时间", "type": "datetime", "required": True},
                {"key": "days", "label": "请假天数", "type": "number", "required": True, "placeholder": "0.5"},
                {"key": "reason", "label": "请假事由", "type": "textarea", "required": True},
            ]
        },
    },
    {
        "name": "报销审批",
        "icon": "Money",
        "category": "expense",
        "description": "费用报销申请",
        "form_schema": {
            "fields": [
                {"key": "expense_type", "label": "报销类型", "type": "select",
                 "options": ["差旅费", "交通费", "餐饮费", "办公费", "招待费", "其他"], "required": True},
                {"key": "amount", "label": "报销金额(元)", "type": "money", "required": True},
                {"key": "expense_date", "label": "发生日期", "type": "date", "required": True},
                {"key": "detail", "label": "费用明细", "type": "textarea", "required": True},
            ]
        },
    },
    {
        "name": "出差审批",
        "icon": "Position",
        "category": "travel",
        "description": "出差申请",
        "form_schema": {
            "fields": [
                {"key": "destination", "label": "出差目的地", "type": "input", "required": True},
                {"key": "start_date", "label": "出发日期", "type": "date", "required": True},
                {"key": "end_date", "label": "返回日期", "type": "date", "required": True},
                {"key": "purpose", "label": "出差事由", "type": "textarea", "required": True},
                {"key": "budget", "label": "预计费用(元)", "type": "money", "required": False},
            ]
        },
    },
    {
        "name": "加班审批",
        "icon": "Clock",
        "category": "overtime",
        "description": "加班申请",
        "form_schema": {
            "fields": [
                {"key": "overtime_date", "label": "加班日期", "type": "date", "required": True},
                {"key": "start_time", "label": "开始时间", "type": "datetime", "required": True},
                {"key": "end_time", "label": "结束时间", "type": "datetime", "required": True},
                {"key": "hours", "label": "加班时长(小时)", "type": "number", "required": True},
                {"key": "reason", "label": "加班事由", "type": "textarea", "required": True},
            ]
        },
    },
    {
        "name": "通用审批",
        "icon": "Document",
        "category": "custom",
        "description": "通用事项审批",
        "form_schema": {
            "fields": [
                {"key": "content", "label": "申请内容", "type": "textarea", "required": True},
                {"key": "remark", "label": "备注说明", "type": "textarea", "required": False},
            ]
        },
    },
]


class ApprovalEngine:

    # ==================== 模板管理 ====================

    def get_templates(self, db: Session, workspace_id: int) -> list[ApprovalTemplate]:
        """获取模板列表 — 若空间尚无任何模板，自动种子内置模板（路由到空间所有者审批）"""
        existing = db.query(ApprovalTemplate).filter(
            ApprovalTemplate.workspace_id == workspace_id,
            ApprovalTemplate.is_active == True
        ).count()
        if existing == 0:
            self.seed_builtin_templates(db, workspace_id)
        return db.query(ApprovalTemplate).filter(
            ApprovalTemplate.workspace_id == workspace_id,
            ApprovalTemplate.is_active == True
        ).order_by(ApprovalTemplate.id).all()

    def seed_builtin_templates(self, db: Session, workspace_id: int) -> list[ApprovalTemplate]:
        """为工作空间种子内置审批模板 — 默认审批人设为空间所有者"""
        from app.models.workspace import Workspace
        ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
        owner_id = ws.owner_id if ws else None
        # owner_id 为 None 时无法建外键，跳过种子（调用方应保证空间存在）
        if not owner_id:
            return []
        # flow_schema: 单节点审批，审批人为空间所有者
        flow_schema = {"nodes": [{"sort": 1, "name": "空间所有者审批", "approver_ids": [owner_id]}]}
        created = []
        for spec in BUILTIN_TEMPLATES:
            t = ApprovalTemplate(
                workspace_id=workspace_id,
                name=spec["name"],
                icon=spec.get("icon"),
                description=spec.get("description"),
                form_schema=spec["form_schema"],
                flow_schema=flow_schema,
                category=spec["category"],
                is_builtin=True,
                created_by=owner_id,
            )
            db.add(t)
            created.append(t)
        db.commit()
        for t in created:
            db.refresh(t)
        return created

    def get_template(self, db: Session, template_id: int) -> ApprovalTemplate:
        t = db.query(ApprovalTemplate).filter(
            ApprovalTemplate.id == template_id,
            ApprovalTemplate.is_active == True
        ).first()
        if not t:
            raise ResourceNotFoundError(resource="审批模板")
        return t

    def create_template(self, db: Session, workspace_id: int, created_by: int,
                        name: str, form_schema: dict, flow_schema: dict,
                        category: str = "custom", description: str = None,
                        icon: str = None) -> ApprovalTemplate:
        """创建模板 — flow_schema 示例:
        {"nodes": [{"sort": 1, "name": "直属上级", "approver_ids": [5]},
                   {"sort": 2, "name": "财务", "approver_ids": [12]}]}
        """
        t = ApprovalTemplate(
            workspace_id=workspace_id,
            name=name,
            icon=icon,
            description=description,
            form_schema=form_schema,
            flow_schema=flow_schema,
            category=category,
            created_by=created_by
        )
        db.add(t)
        db.commit()
        db.refresh(t)
        return t

    # ==================== 提交审批 ====================

    def submit(self, db: Session, template_id: int, applicant_id: int,
               title: str, form_data: dict) -> ApprovalInstance:
        template = self.get_template(db, template_id)
        flow_nodes = template.flow_schema.get("nodes", []) if template.flow_schema else []

        if not flow_nodes:
            # 无审批节点 → 直接通过
            inst = ApprovalInstance(
                template_id=template_id,
                workspace_id=template.workspace_id,
                applicant_id=applicant_id,
                title=title,
                form_data=form_data,
                status=ApprovalStatus.APPROVED,
                submitted_at=get_beijing_time().isoformat(),
                completed_at=get_beijing_time().isoformat(),
                current_node_sort=0
            )
            db.add(inst)
            db.commit()
            db.refresh(inst)
            return inst

        inst = ApprovalInstance(
            template_id=template_id,
            workspace_id=template.workspace_id,
            applicant_id=applicant_id,
            title=title,
            form_data=form_data,
            current_node_sort=1,
            submitted_at=get_beijing_time().isoformat()
        )
        db.add(inst)
        db.flush()

        # 创建第一个节点的待审批记录
        first_node = flow_nodes[0]
        approver_ids = first_node.get("approver_ids", [])
        for aid in approver_ids:
            db.add(ApprovalNode(
                instance_id=inst.id,
                node_name=first_node.get("name", "审批节点"),
                approver_id=aid,
                sort_order=1
            ))

        db.commit()
        db.refresh(inst)
        return inst

    # ==================== 审批操作 ====================

    def approve(self, db: Session, instance_id: int, node_id: int, approver_id: int,
                comment: str = None) -> ApprovalInstance:
        """审批通过 — 推进到下一节点或完成（使用行锁防止并发推进）
        禁止申请人审批自己的申请（除非流程明确指定申请人为审批人）
        """
        # 锁定实例，防止并行审批时重复推进节点
        inst = db.query(ApprovalInstance).filter(
            ApprovalInstance.id == instance_id,
            ApprovalInstance.is_active == True
        ).with_for_update().first()
        if not inst:
            raise ResourceNotFoundError(resource="审批实例")
        if inst.status != ApprovalStatus.PENDING:
            raise BusinessError("该审批已结束")

        node = db.query(ApprovalNode).filter(
            ApprovalNode.id == node_id,
            ApprovalNode.instance_id == instance_id
        ).first()
        if not node:
            raise ResourceNotFoundError(resource="审批节点")
        if node.approver_id != approver_id:
            raise PermissionDeniedError(detail="你不是该节点的审批人")
        if node.status != NodeStatus.PENDING:
            raise BusinessError("该节点已处理")

        # 安全校验：申请人不能审批自己的申请（除非节点明确指定申请人为审批人）
        # 这种情况罕见但合法（如自审环节），通过 flow_schema 配置控制
        if inst.applicant_id == approver_id:
            raise BusinessError("不能审批自己提交的申请")

        node.status = NodeStatus.APPROVED
        node.comment = comment
        node.acted_at = get_beijing_time().isoformat()

        # 检查同节点是否有其他人未审批
        pending_same_sort = db.query(ApprovalNode).filter(
            ApprovalNode.instance_id == instance_id,
            ApprovalNode.sort_order == inst.current_node_sort,
            ApprovalNode.status == NodeStatus.PENDING
        ).count()

        if pending_same_sort == 0:
            # 当前节点全部完成 → 推进
            flow_nodes = inst.template.flow_schema.get("nodes", []) if inst.template.flow_schema else []
            # 使用 flow_nodes 的最大 sort 值判断，而非 len()，避免 sort 不连续导致越界
            max_sort = max([n.get("sort", i + 1) for i, n in enumerate(flow_nodes)], default=0)
            next_sort = inst.current_node_sort + 1

            if next_sort > max_sort:
                # 全部通过
                inst.status = ApprovalStatus.APPROVED
                inst.completed_at = get_beijing_time().isoformat()
            else:
                # 找到下一个 sort 对应的节点定义
                next_node_def = next((n for n in flow_nodes if n.get("sort") == next_sort), None)
                if not next_node_def:
                    # 节点定义缺失，直接结束
                    inst.status = ApprovalStatus.APPROVED
                    inst.completed_at = get_beijing_time().isoformat()
                else:
                    inst.current_node_sort = next_sort
                    for aid in next_node_def.get("approver_ids", []):
                        db.add(ApprovalNode(
                            instance_id=inst.id,
                            node_name=next_node_def.get("name", ""),
                            approver_id=aid,
                            sort_order=next_sort
                        ))

        db.commit()
        db.refresh(inst)
        return inst

    def reject(self, db: Session, instance_id: int, node_id: int, approver_id: int,
               comment: str = None) -> ApprovalInstance:
        """驳回"""
        inst = self._get_instance(db, instance_id)
        if inst.status != ApprovalStatus.PENDING:
            raise BusinessError("该审批已结束")

        node = db.query(ApprovalNode).filter(
            ApprovalNode.id == node_id,
            ApprovalNode.instance_id == instance_id
        ).first()
        if not node:
            raise ResourceNotFoundError(resource="审批节点")
        if node.approver_id != approver_id:
            raise PermissionDeniedError(detail="你不是该节点的审批人")

        node.status = NodeStatus.REJECTED
        node.comment = comment
        node.acted_at = get_beijing_time().isoformat()

        inst.status = ApprovalStatus.REJECTED
        inst.completed_at = get_beijing_time().isoformat()

        db.commit()
        db.refresh(inst)
        return inst

    def transfer(self, db: Session, instance_id: int, node_id: int, from_user_id: int,
                 to_user_id: int) -> ApprovalInstance:
        """转交审批"""
        node = db.query(ApprovalNode).filter(
            ApprovalNode.id == node_id,
            ApprovalNode.instance_id == instance_id,
            ApprovalNode.approver_id == from_user_id,
            ApprovalNode.status == NodeStatus.PENDING
        ).first()
        if not node:
            raise ResourceNotFoundError(resource="审批节点")
        if node.approver_id != from_user_id:
            raise PermissionDeniedError(detail="你不是该节点的审批人")

        node.status = NodeStatus.TRANSFERRED
        node.acted_at = get_beijing_time().isoformat()

        db.add(ApprovalNode(
            instance_id=instance_id,
            node_name=node.node_name + "(转交)",
            approver_id=to_user_id,
            sort_order=node.sort_order
        ))

        db.commit()
        return self._get_instance(db, instance_id)

    def recall(self, db: Session, instance_id: int, applicant_id: int) -> ApprovalInstance:
        """撤回"""
        inst = self._get_instance(db, instance_id)
        if inst.applicant_id != applicant_id:
            raise PermissionDeniedError(detail="只能撤回自己的申请")
        if inst.status != ApprovalStatus.PENDING:
            raise BusinessError("只能撤回审批中的申请")
        inst.status = ApprovalStatus.RECALLED
        inst.completed_at = get_beijing_time().isoformat()
        db.commit()
        db.refresh(inst)
        return inst

    def cancel(self, db: Session, instance_id: int, applicant_id: int) -> ApprovalInstance:
        """取消"""
        inst = self._get_instance(db, instance_id)
        if inst.applicant_id != applicant_id:
            raise PermissionDeniedError(detail="只能取消自己的申请")
        if inst.status not in [ApprovalStatus.PENDING]:
            raise BusinessError("只能取消审批中的申请")
        inst.status = ApprovalStatus.CANCELLED
        inst.completed_at = get_beijing_time().isoformat()
        db.commit()
        db.refresh(inst)
        return inst

    # ==================== 查询 ====================

    def get_pending(self, db: Session, user_id: int, workspace_id: int,
                    page: int = 1, page_size: int = 20) -> dict:
        """我的待办"""
        query = db.query(ApprovalInstance).join(ApprovalNode).filter(
            ApprovalInstance.workspace_id == workspace_id,
            ApprovalInstance.status == ApprovalStatus.PENDING,
            ApprovalNode.approver_id == user_id,
            ApprovalNode.status == NodeStatus.PENDING,
            ApprovalInstance.is_active == True
        ).distinct()
        total = query.count()
        items = query.order_by(desc(ApprovalInstance.created_at)).offset(
            (page - 1) * page_size).limit(page_size).all()
        return {"items": [self._format_instance(i, user_id) for i in items],
                "total": total, "page": page, "page_size": page_size}

    def get_my_applications(self, db: Session, user_id: int, workspace_id: int,
                            page: int = 1, page_size: int = 20) -> dict:
        """我发起的"""
        query = db.query(ApprovalInstance).filter(
            ApprovalInstance.workspace_id == workspace_id,
            ApprovalInstance.applicant_id == user_id,
            ApprovalInstance.is_active == True
        )
        total = query.count()
        items = query.order_by(desc(ApprovalInstance.created_at)).offset(
            (page - 1) * page_size).limit(page_size).all()
        return {"items": [self._format_instance(i) for i in items],
                "total": total, "page": page, "page_size": page_size}

    def get_processed(self, db: Session, user_id: int, workspace_id: int,
                      page: int = 1, page_size: int = 20) -> dict:
        """我已审批的"""
        query = db.query(ApprovalInstance).join(ApprovalNode).filter(
            ApprovalInstance.workspace_id == workspace_id,
            ApprovalNode.approver_id == user_id,
            ApprovalNode.status.in_([NodeStatus.APPROVED, NodeStatus.REJECTED])
        ).distinct()
        total = query.count()
        items = query.order_by(desc(ApprovalInstance.created_at)).offset(
            (page - 1) * page_size).limit(page_size).all()
        return {"items": [self._format_instance(i, user_id) for i in items],
                "total": total, "page": page, "page_size": page_size}

    def get_detail(self, db: Session, instance_id: int) -> ApprovalInstance:
        return self._get_instance(db, instance_id)

    def can_view(self, db: Session, inst: ApprovalInstance, user_id: int) -> bool:
        """校验用户是否有权查看该审批 — 申请人/审批人/抄送人/管理员可见"""
        # 申请人
        if inst.applicant_id == user_id:
            return True
        # 当前审批人或已处理审批人
        for node in inst.nodes:
            if node.approver_id == user_id:
                return True
        # 抄送人
        for cc in inst.cc_list:
            if cc.user_id == user_id:
                return True
        # 工作空间管理员可见
        tmpl = inst.template
        if tmpl:
            from app.core.permissions import get_workspace_member
            from app.models.workspace import WorkspaceRole
            try:
                member = get_workspace_member(tmpl.workspace_id, user_id, db)
                if member.role in [WorkspaceRole.OWNER, WorkspaceRole.ADMIN]:
                    return True
            except Exception:
                pass
        return False

    # ==================== 抄送 ====================

    def add_cc(self, db: Session, instance_id: int, user_ids: list[int]):
        inst = self._get_instance(db, instance_id)
        for uid in user_ids:
            db.add(ApprovalCC(instance_id=instance_id, user_id=uid))
        db.commit()

    # ==================== 内部方法 ====================

    def _get_instance(self, db: Session, instance_id: int) -> ApprovalInstance:
        inst = db.query(ApprovalInstance).filter(
            ApprovalInstance.id == instance_id,
            ApprovalInstance.is_active == True
        ).first()
        if not inst:
            raise ResourceNotFoundError(resource="审批实例")
        return inst

    def _format_instance(self, inst: ApprovalInstance, viewer_id: int = None) -> dict:
        nodes = []
        for n in inst.nodes:
            nodes.append({
                "id": n.id,
                "node_name": n.node_name,
                "approver_id": n.approver_id,
                "approver_name": n.approver.nickname if n.approver else None,
                "status": n.status.value,
                "comment": n.comment,
                "acted_at": n.acted_at,
                "sort_order": n.sort_order
            })

        cc_users = []
        for cc in inst.cc_list:
            cc_users.append({
                "user_id": cc.user_id,
                "name": cc.user.nickname if cc.user else None,
                "is_read": cc.is_read
            })

        return {
            "id": inst.id,
            "template_id": inst.template_id,
            "template_name": inst.template.name if inst.template else None,
            "template_category": inst.template.category if inst.template else None,
            "template_icon": inst.template.icon if inst.template else None,
            "form_schema": inst.template.form_schema if inst.template else None,
            "title": inst.title,
            "applicant_id": inst.applicant_id,
            "applicant_name": inst.applicant.nickname if inst.applicant else None,
            "form_data": inst.form_data,
            "status": inst.status.value,
            "current_node_sort": inst.current_node_sort,
            "nodes": nodes,
            "cc_users": cc_users,
            "submitted_at": inst.submitted_at,
            "completed_at": inst.completed_at,
            "created_at": inst.created_at.isoformat() if inst.created_at else None,
        }


engine = ApprovalEngine()
