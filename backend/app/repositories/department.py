from __future__ import annotations

from sqlalchemy import func, select

from app.models.organization import Department
from app.models.user import User
from app.repositories.base import BaseRepository


class DepartmentRepository(BaseRepository[Department]):
    model = Department

    async def list_in_org(self, organization_id: int) -> list[Department]:
        stmt = (
            select(Department)
            .where(Department.organization_id == organization_id)
            .order_by(Department.id)
        )
        return list(await self.session.scalars(stmt))

    async def get_in_org(self, organization_id: int, department_id: int) -> Department | None:
        stmt = select(Department).where(
            Department.organization_id == organization_id,
            Department.id == department_id,
        )
        return await self.session.scalar(stmt)

    async def name_exists(
        self,
        organization_id: int,
        name: str,
        parent_id: int | None,
        exclude_id: int | None = None,
    ) -> bool:
        stmt = select(func.count()).select_from(Department).where(
            Department.organization_id == organization_id,
            Department.name == name,
        )
        if parent_id is None:
            stmt = stmt.where(Department.parent_id.is_(None))
        else:
            stmt = stmt.where(Department.parent_id == parent_id)
        if exclude_id:
            stmt = stmt.where(Department.id != exclude_id)
        return bool(await self.session.scalar(stmt))

    async def child_count(self, department_id: int) -> int:
        stmt = select(func.count()).select_from(Department).where(
            Department.parent_id == department_id
        )
        return int(await self.session.scalar(stmt) or 0)

    async def member_count(self, organization_id: int, department_id: int) -> int:
        stmt = select(func.count()).select_from(User).where(
            User.organization_id == organization_id,
            User.department_id == department_id,
        )
        return int(await self.session.scalar(stmt) or 0)

    async def names_by_ids(self, department_ids: list[int]) -> dict[int, str]:
        if not department_ids:
            return {}
        stmt = select(Department.id, Department.name).where(
            Department.id.in_(set(department_ids))
        )
        return {
            department_id: name
            for department_id, name in (await self.session.execute(stmt)).all()
        }

    async def member_counts(self, organization_id: int) -> dict[int, int]:
        stmt = (
            select(User.department_id, func.count(User.id))
            .where(
                User.organization_id == organization_id,
                User.department_id.is_not(None),
            )
            .group_by(User.department_id)
        )
        return {
            department_id: count
            for department_id, count in (await self.session.execute(stmt)).all()
        }
