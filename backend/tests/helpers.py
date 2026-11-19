"""测试数据构造。每个测试都在独立的 SQLite 内存库里跑，互不影响。"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import PERMISSION_DEFINITIONS, ROLE_PRESETS, SUPER_ADMIN_ROLE_CODE
from app.core.security import hash_password
from app.models.organization import Department, Organization
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.user import User

ADMIN_PASSWORD = "Admin@123456"
MANAGER_PASSWORD = "Manager@123"
EMPLOYEE_PASSWORD = "Employee@123"


@dataclass
class SeedResult:
    org_id: int
    other_org_id: int
    admin_id: int
    manager_id: int
    employee_id: int
    other_admin_id: int
    root_dept_id: int
    tech_dept_id: int
    employee_role_id: int
    super_role_id: int


async def _create_org(session: AsyncSession, name: str, code: str) -> Organization:
    org = Organization(name=name, code=code, status=1)
    session.add(org)
    await session.flush()
    return org


async def _create_user(
    session: AsyncSession,
    org_id: int,
    username: str,
    password: str,
    real_name: str,
    department_id: int | None = None,
) -> User:
    user = User(
        organization_id=org_id,
        department_id=department_id,
        username=username,
        password_hash=hash_password(password),
        real_name=real_name,
        email=f"{username}@example.com",
        status=1,
    )
    session.add(user)
    await session.flush()
    return user


async def seed_basic(session: AsyncSession) -> SeedResult:
    permissions: dict[str, Permission] = {}
    for code, name, permission_type in PERMISSION_DEFINITIONS:
        permission = Permission(name=name, code=code, type=permission_type)
        session.add(permission)
        permissions[code] = permission
    await session.flush()

    org = await _create_org(session, "测试企业", "test")
    other_org = await _create_org(session, "另一家企业", "other")

    roles: dict[str, Role] = {}
    for code, preset in ROLE_PRESETS.items():
        role = Role(
            organization_id=org.id,
            name=preset["name"],
            code=code,
            description=preset["description"],
        )
        session.add(role)
        await session.flush()
        wanted = (
            list(permissions.values())
            if preset["permissions"] is None
            else [permissions[c] for c in preset["permissions"]]
        )
        for permission in wanted:
            session.add(RolePermission(role_id=role.id, permission_id=permission.id))
        roles[code] = role

    other_role = Role(
        organization_id=other_org.id, name="企业管理员", code="org_admin", description=None
    )
    session.add(other_role)
    await session.flush()
    for permission in permissions.values():
        session.add(RolePermission(role_id=other_role.id, permission_id=permission.id))
    await session.flush()

    root = Department(organization_id=org.id, name="总公司", parent_id=None)
    session.add(root)
    await session.flush()
    tech = Department(organization_id=org.id, name="技术部", parent_id=root.id)
    session.add(tech)
    await session.flush()

    admin = await _create_user(session, org.id, "admin", ADMIN_PASSWORD, "系统管理员")
    manager = await _create_user(
        session, org.id, "manager", MANAGER_PASSWORD, "部门经理", department_id=tech.id
    )
    employee = await _create_user(
        session, org.id, "employee", EMPLOYEE_PASSWORD, "普通员工", department_id=tech.id
    )
    other_admin = await _create_user(
        session, other_org.id, "admin", ADMIN_PASSWORD, "别家管理员"
    )

    session.add(UserRole(user_id=admin.id, role_id=roles[SUPER_ADMIN_ROLE_CODE].id))
    session.add(UserRole(user_id=manager.id, role_id=roles["dept_manager"].id))
    session.add(UserRole(user_id=employee.id, role_id=roles["employee"].id))
    session.add(UserRole(user_id=other_admin.id, role_id=other_role.id))
    await session.flush()

    return SeedResult(
        org_id=org.id,
        other_org_id=other_org.id,
        admin_id=admin.id,
        manager_id=manager.id,
        employee_id=employee.id,
        other_admin_id=other_admin.id,
        root_dept_id=root.id,
        tech_dept_id=tech.id,
        employee_role_id=roles["employee"].id,
        super_role_id=roles[SUPER_ADMIN_ROLE_CODE].id,
    )
