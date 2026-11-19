from __future__ import annotations

from httpx import AsyncClient


async def test_department_tree(client: AsyncClient, admin_headers, seeded) -> None:
    response = await client.get("/api/v1/departments", headers=admin_headers)
    assert response.status_code == 200, response.text
    tree = response.json()
    assert len(tree) == 1
    root = tree[0]
    assert root["name"] == "总公司"
    assert len(root["children"]) == 1
    tech = root["children"][0]
    assert tech["name"] == "技术部"
    assert tech["member_count"] == 2


async def test_create_child_department(client: AsyncClient, admin_headers, seeded) -> None:
    response = await client.post(
        "/api/v1/departments",
        headers=admin_headers,
        json={"name": "前端组", "parent_id": seeded.tech_dept_id, "leader_id": seeded.manager_id},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "前端组"
    assert body["parent_id"] == seeded.tech_dept_id

    tree = (await client.get("/api/v1/departments", headers=admin_headers)).json()
    tech = tree[0]["children"][0]
    assert any(child["name"] == "前端组" for child in tech["children"])


async def test_duplicate_sibling_name(client: AsyncClient, admin_headers, seeded) -> None:
    response = await client.post(
        "/api/v1/departments",
        headers=admin_headers,
        json={"name": "技术部", "parent_id": seeded.root_dept_id},
    )
    assert response.status_code == 409


async def test_cannot_move_department_under_its_child(
    client: AsyncClient, admin_headers, seeded
) -> None:
    response = await client.put(
        f"/api/v1/departments/{seeded.root_dept_id}",
        headers=admin_headers,
        json={"parent_id": seeded.tech_dept_id},
    )
    assert response.status_code == 400
    assert "子部门" in response.json()["message"]


async def test_delete_department_with_members_conflicts(
    client: AsyncClient, admin_headers, seeded
) -> None:
    response = await client.delete(
        f"/api/v1/departments/{seeded.tech_dept_id}", headers=admin_headers
    )
    assert response.status_code == 409


async def test_delete_department_with_children_conflicts(
    client: AsyncClient, admin_headers, seeded
) -> None:
    response = await client.delete(
        f"/api/v1/departments/{seeded.root_dept_id}", headers=admin_headers
    )
    assert response.status_code == 409


async def test_create_and_delete_empty_department(
    client: AsyncClient, admin_headers, seeded
) -> None:
    created = await client.post(
        "/api/v1/departments",
        headers=admin_headers,
        json={"name": "临时部门", "parent_id": None},
    )
    assert created.status_code == 201
    department_id = created.json()["id"]

    deleted = await client.delete(
        f"/api/v1/departments/{department_id}", headers=admin_headers
    )
    assert deleted.status_code == 200


async def test_employee_cannot_read_departments(
    client: AsyncClient, employee_headers
) -> None:
    response = await client.get("/api/v1/departments", headers=employee_headers)
    assert response.status_code == 403
