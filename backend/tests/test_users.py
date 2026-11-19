from __future__ import annotations

from httpx import AsyncClient


async def test_list_users_requires_permission(client: AsyncClient, employee_headers) -> None:
    response = await client.get("/api/v1/users", headers=employee_headers)
    assert response.status_code == 403
    assert response.json()["code"] == "forbidden"


async def test_list_users(client: AsyncClient, admin_headers, seeded) -> None:
    response = await client.get("/api/v1/users", headers=admin_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 3
    assert body["page"] == 1
    assert len(body["items"]) == 3
    usernames = {item["username"] for item in body["items"]}
    assert usernames == {"admin", "manager", "employee"}


async def test_list_users_keyword_and_department(
    client: AsyncClient, admin_headers, seeded
) -> None:
    response = await client.get(
        "/api/v1/users",
        headers=admin_headers,
        params={"keyword": "manager"},
    )
    assert response.status_code == 200
    assert response.json()["total"] == 1

    response = await client.get(
        "/api/v1/users",
        headers=admin_headers,
        params={"department_id": seeded.tech_dept_id},
    )
    assert response.json()["total"] == 2


async def test_create_user(client: AsyncClient, admin_headers, seeded) -> None:
    payload = {
        "username": "newbie",
        "password": "Newbie@123",
        "real_name": "新同事",
        "email": "newbie@example.com",
        "department_id": seeded.tech_dept_id,
        "role_ids": [seeded.employee_role_id],
    }
    response = await client.post("/api/v1/users", headers=admin_headers, json=payload)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["username"] == "newbie"
    assert body["department_name"] == "技术部"
    assert body["roles"][0]["code"] == "employee"

    duplicate = await client.post("/api/v1/users", headers=admin_headers, json=payload)
    assert duplicate.status_code == 409


async def test_create_user_invalid_password(client: AsyncClient, admin_headers) -> None:
    response = await client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={"username": "weakpwd", "password": "abcdefgh"},
    )
    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"


async def test_create_user_with_other_org_role(
    client: AsyncClient, admin_headers, seeded
) -> None:
    response = await client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "username": "crossrole",
            "password": "Cross@123",
            "role_ids": [999999],
        },
    )
    assert response.status_code == 400


async def test_update_user_and_roles(client: AsyncClient, admin_headers, seeded) -> None:
    response = await client.put(
        f"/api/v1/users/{seeded.employee_id}",
        headers=admin_headers,
        json={"real_name": "改名了", "role_ids": [seeded.employee_role_id]},
    )
    assert response.status_code == 200, response.text
    assert response.json()["real_name"] == "改名了"


async def test_cannot_disable_self(client: AsyncClient, admin_headers, seeded) -> None:
    response = await client.delete(
        f"/api/v1/users/{seeded.admin_id}", headers=admin_headers
    )
    assert response.status_code == 400


async def test_disable_user_blocks_login(
    client: AsyncClient, admin_headers, seeded
) -> None:
    from tests.helpers import EMPLOYEE_PASSWORD

    response = await client.delete(
        f"/api/v1/users/{seeded.employee_id}", headers=admin_headers
    )
    assert response.status_code == 200

    login = await client.post(
        "/api/v1/auth/login",
        json={
            "username": "employee",
            "password": EMPLOYEE_PASSWORD,
            "organization_code": "test",
        },
    )
    assert login.status_code == 401
    assert "禁用" in login.json()["message"]
