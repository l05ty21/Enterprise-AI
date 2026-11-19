"""跨企业数据隔离：A 企业用户绝对不能读到 B 企业的数据。"""

from __future__ import annotations

from httpx import AsyncClient


async def test_other_org_cannot_read_foreign_user(
    client: AsyncClient, other_admin_headers, seeded
) -> None:
    response = await client.get(
        f"/api/v1/users/{seeded.admin_id}", headers=other_admin_headers
    )
    assert response.status_code == 404


async def test_other_org_user_list_is_scoped(
    client: AsyncClient, other_admin_headers, seeded
) -> None:
    response = await client.get("/api/v1/users", headers=other_admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["username"] == "admin"
    assert body["items"][0]["organization_id"] == seeded.other_org_id


async def test_other_org_cannot_update_foreign_user(
    client: AsyncClient, other_admin_headers, seeded
) -> None:
    response = await client.put(
        f"/api/v1/users/{seeded.employee_id}",
        headers=other_admin_headers,
        json={"real_name": "越权修改"},
    )
    assert response.status_code == 404


async def test_other_org_cannot_assign_foreign_role(
    client: AsyncClient, other_admin_headers, seeded
) -> None:
    response = await client.post(
        "/api/v1/users",
        headers=other_admin_headers,
        json={
            "username": "intruder",
            "password": "Intruder@123",
            "role_ids": [seeded.super_role_id],
        },
    )
    assert response.status_code == 400


async def test_other_org_departments_are_isolated(
    client: AsyncClient, other_admin_headers, seeded
) -> None:
    response = await client.get("/api/v1/departments", headers=other_admin_headers)
    assert response.status_code == 200
    assert response.json() == []
