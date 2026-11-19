"""企业自助注册的测试。"""

from __future__ import annotations

import pytest
from sqlalchemy import func, select

from app.models.organization import Department, Organization
from app.models.rbac import Role
from app.models.user import User

REGISTER_PAYLOAD = {
    "organization_name": "星河科技有限公司",
    "organization_code": "xinghe",
    "username": "boss",
    "password": "Xinghe@2026",
    "real_name": "张星河",
    "email": "boss@xinghe.com",
}


async def test_register_creates_org_roles_and_admin(client, session_factory) -> None:
    resp = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"

    # 令牌可直接用
    headers = {"Authorization": f"Bearer {body['access_token']}"}
    me = await client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    profile = me.json()
    assert profile["username"] == "boss"
    assert profile["organization_name"] == "星河科技有限公司"
    # 自助注册拿到的是企业管理员，不是平台超管
    assert profile["is_superuser"] is False
    assert [role["code"] for role in profile["roles"]] == ["org_admin"]
    assert "user:read" in profile["permissions"]
    assert "system:config" in profile["permissions"]

    async with session_factory() as session:
        org = await session.scalar(
            select(Organization).where(Organization.code == "xinghe")
        )
        assert org is not None
        # 三个内置角色（不含 super_admin）
        roles = list(
            await session.scalars(
                select(Role.code).where(Role.organization_id == org.id)
            )
        )
        assert sorted(roles) == ["dept_manager", "employee", "org_admin"]
        # 默认部门
        depts = list(
            await session.scalars(
                select(Department.name).where(Department.organization_id == org.id)
            )
        )
        assert depts == ["总公司"]
        users = await session.scalar(
            select(func.count()).select_from(User).where(User.organization_id == org.id)
        )
        assert users == 1


async def test_register_then_login(client) -> None:
    created = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    assert created.status_code == 201

    login = await client.post(
        "/api/v1/auth/login",
        json={
            "username": REGISTER_PAYLOAD["username"],
            "password": REGISTER_PAYLOAD["password"],
            "organization_code": REGISTER_PAYLOAD["organization_code"],
        },
    )
    assert login.status_code == 200, login.text
    assert login.json()["access_token"]


async def test_register_duplicate_org_code_conflicts(client) -> None:
    first = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    assert first.status_code == 201

    second = await client.post(
        "/api/v1/auth/register",
        json={**REGISTER_PAYLOAD, "username": "other"},
    )
    assert second.status_code == 409
    assert second.json()["code"] == "conflict"


@pytest.mark.parametrize(
    "bad_field,bad_value",
    [
        ("password", "12345678"),        # 纯数字
        ("password", "abcdefgh"),        # 纯字母
        ("password", "Ab1"),             # 太短
        ("organization_code", "XINGHE"), # 含大写
        ("organization_code", "1abc"),   # 数字开头
        ("username", "a"),               # 太短
    ],
)
async def test_register_validation(client, bad_field, bad_value) -> None:
    payload = {**REGISTER_PAYLOAD, bad_field: bad_value}
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 422, resp.text


async def test_new_org_is_isolated_from_seeded_org(client, admin_headers) -> None:
    """新注册企业看不到示例企业的用户。"""
    created = await client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    headers = {"Authorization": f"Bearer {created.json()['access_token']}"}

    listing = await client.get("/api/v1/users", headers=headers)
    assert listing.status_code == 200
    assert listing.json()["total"] == 1  # 只有自己

    # 示例企业里有 admin / manager / employee 三个
    seeded = await client.get("/api/v1/users", headers=admin_headers)
    assert seeded.json()["total"] == 3
