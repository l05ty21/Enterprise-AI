from __future__ import annotations

from httpx import AsyncClient


async def test_list_roles(client: AsyncClient, admin_headers, seeded) -> None:
    response = await client.get("/api/v1/roles", headers=admin_headers)
    assert response.status_code == 200, response.text
    roles = response.json()
    codes = {role["code"] for role in roles}
    assert {"super_admin", "org_admin", "dept_manager", "employee"} <= codes
    super_role = next(role for role in roles if role["code"] == "super_admin")
    assert super_role["permission_ids"]
    assert super_role["user_count"] == 1


async def test_list_permissions(client: AsyncClient, admin_headers) -> None:
    response = await client.get("/api/v1/permissions", headers=admin_headers)
    assert response.status_code == 200
    codes = {item["code"] for item in response.json()}
    assert "user:read" in codes
    assert "menu:dashboard" in codes


async def test_create_role_with_permissions(client: AsyncClient, admin_headers) -> None:
    permissions = await client.get("/api/v1/permissions", headers=admin_headers)
    permission_ids = [item["id"] for item in permissions.json()[:3]]

    response = await client.post(
        "/api/v1/roles",
        headers=admin_headers,
        json={
            "name": "审计员",
            "code": "auditor",
            "description": "只读角色",
            "permission_ids": permission_ids,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["code"] == "auditor"
    assert sorted(body["permission_ids"]) == sorted(permission_ids)

    duplicate = await client.post(
        "/api/v1/roles",
        headers=admin_headers,
        json={"name": "审计员2", "code": "auditor"},
    )
    assert duplicate.status_code == 409


async def test_update_role_permissions(client: AsyncClient, admin_headers, seeded) -> None:
    permissions = await client.get("/api/v1/permissions", headers=admin_headers)
    permission_ids = [item["id"] for item in permissions.json()[:2]]

    response = await client.put(
        f"/api/v1/roles/{seeded.employee_role_id}",
        headers=admin_headers,
        json={"name": "普通员工", "permission_ids": permission_ids},
    )
    assert response.status_code == 200
    assert sorted(response.json()["permission_ids"]) == sorted(permission_ids)


async def test_delete_role_in_use_conflicts(
    client: AsyncClient, admin_headers, seeded
) -> None:
    response = await client.delete(
        f"/api/v1/roles/{seeded.employee_role_id}", headers=admin_headers
    )
    assert response.status_code == 409


async def test_delete_super_admin_role_forbidden(
    client: AsyncClient, admin_headers, seeded
) -> None:
    response = await client.delete(
        f"/api/v1/roles/{seeded.super_role_id}", headers=admin_headers
    )
    assert response.status_code == 400


async def test_create_role_with_unknown_permission(
    client: AsyncClient, admin_headers
) -> None:
    response = await client.post(
        "/api/v1/roles",
        headers=admin_headers,
        json={"name": "坏角色", "code": "badrole", "permission_ids": [987654]},
    )
    assert response.status_code == 400


async def test_employee_cannot_manage_roles(client: AsyncClient, employee_headers) -> None:
    response = await client.get("/api/v1/roles", headers=employee_headers)
    assert response.status_code == 403
