"""初始化基础数据：企业、权限点、内置角色、管理员账号、示例部门。

用法（先确保表结构已创建）：
    alembic upgrade head
    python -m app.db.seed

如果还没建表，可以临时加 --create-tables 让脚本直接按模型建表：
    python -m app.db.seed --create-tables
"""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select

from app.core.config import settings
from app.core.constants import (
    PERMISSION_DEFINITIONS,
    ROLE_PRESETS,
    SUPER_ADMIN_ROLE_CODE,
)
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_engine, get_session_factory, dispose_engine
from app.models.organization import Department, Organization
from app.models.rbac import Permission, Role, RolePermission, UserRole
from app.models.user import User


async def ensure_tables() -> None:
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[seed] 已按模型创建缺失的表（生产环境建议改用 alembic upgrade head）")


async def seed_permissions(session) -> dict[str, int]:
    existing = {
        permission.code: permission
        for permission in (await session.scalars(select(Permission))).all()
    }
    for code, name, permission_type in PERMISSION_DEFINITIONS:
        if code in existing:
            existing[code].name = name
            existing[code].type = permission_type
        else:
            permission = Permission(name=name, code=code, type=permission_type)
            session.add(permission)
            existing[code] = permission
    await session.flush()
    return {code: permission.id for code, permission in existing.items()}


async def seed_roles(
    session, organization_id: int, permission_ids: dict[str, int]
) -> dict[str, Role]:
    roles = {
        role.code: role
        for role in (
            await session.scalars(
                select(Role).where(Role.organization_id == organization_id)
            )
        ).all()
    }
    for code, preset in ROLE_PRESETS.items():
        role = roles.get(code)
        if role is None:
            role = Role(
                organization_id=organization_id,
                name=preset["name"],
                code=code,
                description=preset["description"],
            )
            session.add(role)
            await session.flush()
            roles[code] = role

        wanted = (
            list(permission_ids.values())
            if preset["permissions"] is None
            else [permission_ids[item] for item in preset["permissions"] if item in permission_ids]
        )
        current = set(
            await session.scalars(
                select(RolePermission.permission_id).where(
                    RolePermission.role_id == role.id
                )
            )
        )
        for permission_id in set(wanted) - current:
            session.add(RolePermission(role_id=role.id, permission_id=permission_id))
        for permission_id in current - set(wanted):
            mapping = await session.get(RolePermission, (role.id, permission_id))
            if mapping is not None:
                await session.delete(mapping)
    await session.flush()
    return roles


async def seed_organization(session) -> Organization:
    organization = await session.scalar(
        select(Organization).where(Organization.code == settings.FIRST_ORG_CODE)
    )
    if organization is None:
        organization = Organization(
            name=settings.FIRST_ORG_NAME, code=settings.FIRST_ORG_CODE, status=1
        )
        session.add(organization)
        await session.flush()
        print(f"[seed] 创建企业: {organization.name} ({organization.code})")
    return organization


async def seed_departments(session, organization_id: int) -> list[Department]:
    exists = await session.scalar(
        select(Department.id).where(Department.organization_id == organization_id).limit(1)
    )
    if exists:
        return []

    root = Department(organization_id=organization_id, name="总公司", parent_id=None)
    session.add(root)
    await session.flush()
    children = []
    for name in ("技术部", "产品部", "市场部"):
        children.append(
            Department(organization_id=organization_id, name=name, parent_id=root.id)
        )
    session.add_all(children)
    await session.flush()
    print("[seed] 创建示例部门树: 总公司 > 技术部 / 产品部 / 市场部")
    return [root, *children]


async def seed_admin(session, organization: Organization, roles: dict[str, Role]) -> User:
    admin = await session.scalar(
        select(User).where(
            User.organization_id == organization.id,
            User.username == settings.FIRST_SUPERUSER_USERNAME,
        )
    )
    if admin is None:
        admin = User(
            organization_id=organization.id,
            username=settings.FIRST_SUPERUSER_USERNAME,
            password_hash=hash_password(settings.FIRST_SUPERUSER_PASSWORD),
            real_name=settings.FIRST_SUPERUSER_REAL_NAME,
            email=settings.FIRST_SUPERUSER_EMAIL,
            status=1,
        )
        session.add(admin)
        await session.flush()
        print(
            f"[seed] 创建管理员: {admin.username} / 初始密码: {settings.FIRST_SUPERUSER_PASSWORD}"
        )

    super_role = roles[SUPER_ADMIN_ROLE_CODE]
    mapping = await session.get(UserRole, (admin.id, super_role.id))
    if mapping is None:
        session.add(UserRole(user_id=admin.id, role_id=super_role.id))
        await session.flush()
    return admin


async def run(create_tables: bool = False) -> None:
    if create_tables:
        await ensure_tables()

    factory = get_session_factory()
    async with factory() as session:
        organization = await seed_organization(session)
        permission_ids = await seed_permissions(session)
        roles = await seed_roles(session, organization.id, permission_ids)
        await seed_departments(session, organization.id)
        await seed_admin(session, organization, roles)
        await session.commit()

        print("[seed] 完成：")
        print(f"       企业      : {organization.name} ({organization.code})")
        print(f"       权限点    : {len(permission_ids)} 个")
        print(f"       内置角色  : {', '.join(roles)}")
        print(f"       登录账号  : {settings.FIRST_SUPERUSER_USERNAME}")
        print(f"       初始密码  : {settings.FIRST_SUPERUSER_PASSWORD}")

    await dispose_engine()


def main() -> None:
    parser = argparse.ArgumentParser(description="初始化智企协同的基础数据")
    parser.add_argument(
        "--create-tables",
        action="store_true",
        help="先按模型执行 create_all（没有跑 alembic 时使用）",
    )
    args = parser.parse_args()
    asyncio.run(run(create_tables=args.create_tables))


if __name__ == "__main__":
    main()
