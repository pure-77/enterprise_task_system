"""组织架构模块 — CRUD 操作"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.modules.org.models import Department, Position
from app.models.workspace import WorkspaceMember
from app.core.exceptions import ResourceNotFoundError, BusinessError


class DepartmentCRUD:
    """部门 CRUD"""

    def get_tree(self, db: Session, workspace_id: int) -> list[dict]:
        """获取部门树 — 一次性查询所有部门 + 一次聚合统计成员数，避免 N+1"""
        # 1. 查询所有部门
        departments = (
            db.query(Department)
            .filter(
                Department.workspace_id == workspace_id,
                Department.is_active == True
            )
            .order_by(Department.sort_order, Department.id)
            .all()
        )

        # 2. 一次性聚合每个部门的成员数（通过 workspace_members.department_id）
        member_counts = dict(
            db.query(
                WorkspaceMember.department_id,
                func.count(WorkspaceMember.user_id)
            )
            .filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.department_id.isnot(None),
                WorkspaceMember.is_active == True
            )
            .group_by(WorkspaceMember.department_id)
            .all()
        )

        # 3. 一次查询所有部门负责人（避免懒加载触发 N+1）
        leader_ids = {d.leader_id for d in departments if d.leader_id}
        leaders = {}
        if leader_ids:
            from app.models.user import User
            for u in db.query(User).filter(User.id.in_(leader_ids)).all():
                leaders[u.id] = u

        # 4. 用 dict 索引构建树，O(n) 复杂度（替代原 O(n²) 递归）
        return self._build_tree_optimized(departments, member_counts, leaders)

    def _build_tree_optimized(
        self,
        departments: list[Department],
        member_counts: dict,
        leaders: dict
    ) -> list[dict]:
        """使用 dict 索引构建树形结构 — O(n) 复杂度"""
        # 第一遍：建立 id -> node 字典
        node_map = {}
        for dept in departments:
            leader = leaders.get(dept.leader_id)
            node_map[dept.id] = {
                "id": dept.id,
                "name": dept.name,
                "parent_id": dept.parent_id,
                "leader_id": dept.leader_id,
                "leader_name": (
                    leader.real_name or leader.nickname
                ) if leader else None,
                "sort_order": dept.sort_order,
                "path": dept.path,
                "member_count": member_counts.get(dept.id, 0),
                "children": []
            }

        # 第二遍：挂载父子关系（与排序无关，确保父节点已存在于 map 中）
        tree = []
        for dept in departments:
            node = node_map[dept.id]
            if dept.parent_id and dept.parent_id in node_map:
                node_map[dept.parent_id]["children"].append(node)
            else:
                tree.append(node)

        # 第三遍：自底向上汇总 — 父部门人数 = 本部门人数 + 所有子部门人数之和
        def _aggregate(node):
            for child in node["children"]:
                node["member_count"] += _aggregate(child)
            return node["member_count"]

        for root in tree:
            _aggregate(root)
        return tree

    def get_by_id(self, db: Session, dept_id: int) -> Department:
        """按 ID 查询部门"""
        dept = db.query(Department).filter(
            Department.id == dept_id,
            Department.is_active == True
        ).first()
        if not dept:
            raise ResourceNotFoundError(resource="部门")
        return dept

    def create(
        self,
        db: Session,
        workspace_id: int,
        name: str,
        parent_id: int | None = None,
        leader_id: int | None = None,
        sort_order: int = 0
    ) -> Department:
        """创建部门"""
        parent = None
        if parent_id:
            parent = self.get_by_id(db, parent_id)
            if parent.workspace_id != workspace_id:
                raise BusinessError("父部门不属于当前工作空间")

        dept = Department(
            workspace_id=workspace_id,
            name=name,
            parent_id=parent_id,
            leader_id=leader_id,
            sort_order=sort_order,
            path=""
        )
        db.add(dept)
        db.flush()  # 获取 dept.id

        if parent:
            parent_path = parent.path or ""
            dept.path = f"{parent_path}/{dept.id}"
        else:
            dept.path = f"/{dept.id}"

        db.commit()
        db.refresh(dept)
        return dept

    def update(self, db: Session, dept_id: int, **kwargs) -> Department:
        """更新部门"""
        dept = self.get_by_id(db, dept_id)

        new_parent_id = kwargs.get("parent_id")
        if new_parent_id is not None and new_parent_id != dept.parent_id:
            if new_parent_id == dept_id:
                raise BusinessError("不能将部门设置为自己的子部门")
            if new_parent_id > 0:
                parent = self.get_by_id(db, new_parent_id)
                if parent.workspace_id != dept.workspace_id:
                    raise BusinessError("父部门不属于当前工作空间")
                dept.path = f"{parent.path}/{dept.id}"
            else:
                dept.path = f"/{dept.id}"

        for key, value in kwargs.items():
            if hasattr(dept, key):
                setattr(dept, key, value)

        db.commit()
        db.refresh(dept)
        return dept

    def delete(self, db: Session, dept_id: int) -> Department:
        """软删除部门及其子部门（物化路径前缀匹配）"""
        dept = self.get_by_id(db, dept_id)

        db.query(Department).filter(
            Department.workspace_id == dept.workspace_id,
            Department.path.like(f"{dept.path}/%"),
            Department.is_active == True
        ).update({"is_active": False})

        dept.is_active = False
        db.commit()
        db.refresh(dept)
        return dept


class PositionCRUD:
    """职位 CRUD"""

    def get_list(self, db: Session, workspace_id: int) -> list[Position]:
        return (
            db.query(Position)
            .filter(
                Position.workspace_id == workspace_id,
                Position.is_active == True
            )
            .order_by(Position.sort_order, Position.id)
            .all()
        )

    def get_by_id(self, db: Session, pos_id: int) -> Position:
        pos = db.query(Position).filter(
            Position.id == pos_id,
            Position.is_active == True
        ).first()
        if not pos:
            raise ResourceNotFoundError(resource="职位")
        return pos

    def create(self, db: Session, workspace_id: int, name: str, sort_order: int = 0) -> Position:
        pos = Position(workspace_id=workspace_id, name=name, sort_order=sort_order)
        db.add(pos)
        db.commit()
        db.refresh(pos)
        return pos

    def update(self, db: Session, pos_id: int, **kwargs) -> Position:
        pos = self.get_by_id(db, pos_id)
        for key, value in kwargs.items():
            if hasattr(pos, key):
                setattr(pos, key, value)
        db.commit()
        db.refresh(pos)
        return pos

    def delete(self, db: Session, pos_id: int) -> Position:
        pos = self.get_by_id(db, pos_id)
        pos.is_active = False
        db.commit()
        db.refresh(pos)
        return pos


department_crud = DepartmentCRUD()
position_crud = PositionCRUD()
