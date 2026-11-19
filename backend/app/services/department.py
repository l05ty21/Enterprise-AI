from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestError, ConflictError, NotFoundError
from app.models.organization import Department
from app.repositories.department import DepartmentRepository
from app.repositories.user import UserRepository
from app.schemas.department import DepartmentCreate, DepartmentRead, DepartmentUpdate


class DepartmentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.departments = DepartmentRepository(session)
        self.users = UserRepository(session)

    async def _build_tree(self, organization_id: int) -> list[DepartmentRead]:
        rows = await self.departments.list_in_org(organization_id)
        member_counts = await self.departments.member_counts(organization_id)
        leader_ids = [row.leader_id for row in rows if row.leader_id]
        leader_names = await self.users.names_by_ids([int(leader_id) for leader_id in leader_ids])

        nodes: dict[int, DepartmentRead] = {}
        for row in rows:
            nodes[row.id] = DepartmentRead(
                id=row.id,
                organization_id=row.organization_id,
                parent_id=row.parent_id,
                name=row.name,
                leader_id=row.leader_id,
                leader_name=leader_names.get(row.leader_id or 0),
                member_count=member_counts.get(row.id, 0),
                created_at=row.created_at,
                children=[],
            )

        roots: list[DepartmentRead] = []
        for node in nodes.values():
            parent = nodes.get(node.parent_id) if node.parent_id else None
            if parent is None:
                roots.append(node)
            else:
                parent.children.append(node)
        return roots

    async def tree(self, organization_id: int) -> list[DepartmentRead]:
        return await self._build_tree(organization_id)

    async def _validate_parent(
        self, organization_id: int, parent_id: int | None, *, self_id: int | None = None
    ) -> None:
        if parent_id is None:
            return
        parent = await self.departments.get_in_org(organization_id, parent_id)
        if parent is None:
            raise BadRequestError("上级部门不存在或不属于当前企业")
        if self_id is None:
            return
        # 防止把部门挂到自己的子孙节点下造成环
        cursor: Department | None = parent
        seen: set[int] = set()
        while cursor is not None:
            if cursor.id == self_id:
                raise BadRequestError("不能把部门移动到自己的子部门下")
            if cursor.id in seen:
                break
            seen.add(cursor.id)
            cursor = (
                await self.departments.get(cursor.parent_id)
                if cursor.parent_id
                else None
            )

    async def create(
        self, organization_id: int, payload: DepartmentCreate
    ) -> DepartmentRead:
        await self._validate_parent(organization_id, payload.parent_id)
        if await self.departments.name_exists(
            organization_id, payload.name, payload.parent_id
        ):
            raise ConflictError("同级部门下已存在同名部门")

        department = Department(
            organization_id=organization_id,
            parent_id=payload.parent_id,
            name=payload.name,
            leader_id=payload.leader_id,
        )
        await self.departments.add(department)
        await self.session.commit()
        return DepartmentRead(
            id=department.id,
            organization_id=department.organization_id,
            parent_id=department.parent_id,
            name=department.name,
            leader_id=department.leader_id,
            member_count=0,
            created_at=department.created_at,
            children=[],
        )

    async def update(
        self, organization_id: int, department_id: int, payload: DepartmentUpdate
    ) -> DepartmentRead:
        department = await self.departments.get_in_org(organization_id, department_id)
        if department is None:
            raise NotFoundError("部门不存在")

        data = payload.model_dump(exclude_unset=True)
        if "parent_id" in data:
            await self._validate_parent(organization_id, data["parent_id"], self_id=department.id)
        if "name" in data:
            parent_id = data.get("parent_id", department.parent_id)
            if await self.departments.name_exists(
                organization_id, data["name"], parent_id, exclude_id=department.id
            ):
                raise ConflictError("同级部门下已存在同名部门")

        for field, value in data.items():
            setattr(department, field, value)
        await self.session.commit()

        return DepartmentRead(
            id=department.id,
            organization_id=department.organization_id,
            parent_id=department.parent_id,
            name=department.name,
            leader_id=department.leader_id,
            member_count=await self.departments.member_count(organization_id, department.id),
            created_at=department.created_at,
            children=[],
        )

    async def delete(self, organization_id: int, department_id: int) -> None:
        department = await self.departments.get_in_org(organization_id, department_id)
        if department is None:
            raise NotFoundError("部门不存在")
        if await self.departments.child_count(department.id) > 0:
            raise ConflictError("该部门下还有子部门，请先删除或调整子部门")
        if await self.departments.member_count(organization_id, department.id) > 0:
            raise ConflictError("该部门下还有成员，请先调整成员归属")
        await self.departments.delete(department)
        await self.session.commit()
