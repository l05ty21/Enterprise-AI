from __future__ import annotations

from httpx import AsyncClient


async def test_create_and_approve_flow(
    client: AsyncClient, employee_headers, admin_headers
) -> None:
    created = await client.post(
        "/api/v1/approvals",
        headers=employee_headers,
        json={
            "title": "上海出差报销 800 元",
            "business_type": "expense",
            "amount": 800,
            "reason": "客户拜访，三天两晚",
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["status"] == "pending"
    assert body["amount"] == 800
    # 部门没有负责人时，落到第一个有「审批操作」权限的人（测试数据里是系统管理员）
    assert body["current_approver_name"] == "系统管理员"

    todo = await client.get(
        "/api/v1/approvals", headers=admin_headers, params={"scope": "todo"}
    )
    assert todo.status_code == 200
    assert todo.json()["total"] == 1
    assert todo.json()["items"][0]["can_decide"] is True

    decided = await client.post(
        f"/api/v1/approvals/{body['id']}/decision",
        headers=admin_headers,
        json={"action": "approve", "comment": "同意，按标准报销"},
    )
    assert decided.status_code == 200, decided.text
    assert decided.json()["status"] == "approved"
    assert decided.json()["tasks"][0]["status"] == "approved"
    assert decided.json()["tasks"][0]["comment"] == "同意，按标准报销"

    # 已经处理过的不能再来一次
    again = await client.post(
        f"/api/v1/approvals/{body['id']}/decision",
        headers=admin_headers,
        json={"action": "reject"},
    )
    assert again.status_code == 400


async def test_reject_flow(client: AsyncClient, employee_headers, admin_headers) -> None:
    created = await client.post(
        "/api/v1/approvals",
        headers=employee_headers,
        json={"title": "采购显示器", "business_type": "purchase", "amount": 2999},
    )
    instance_id = created.json()["id"]

    rejected = await client.post(
        f"/api/v1/approvals/{instance_id}/decision",
        headers=admin_headers,
        json={"action": "reject", "comment": "超预算，下季度再提"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert rejected.json()["tasks"][0]["status"] == "rejected"


async def test_employee_cannot_decide(
    client: AsyncClient, employee_headers, admin_headers
) -> None:
    created = await client.post(
        "/api/v1/approvals",
        headers=employee_headers,
        json={"title": "请假一天", "business_type": "leave"},
    )
    instance_id = created.json()["id"]

    # 普通员工没有 approval:approve
    denied = await client.post(
        f"/api/v1/approvals/{instance_id}/decision",
        headers=employee_headers,
        json={"action": "approve"},
    )
    assert denied.status_code == 403


async def test_scope_filters(client: AsyncClient, employee_headers, admin_headers) -> None:
    await client.post(
        "/api/v1/approvals",
        headers=employee_headers,
        json={"title": "我发起的审批", "business_type": "other"},
    )

    mine = await client.get(
        "/api/v1/approvals", headers=employee_headers, params={"scope": "mine"}
    )
    assert mine.json()["total"] == 1
    assert mine.json()["items"][0]["applicant_name"] == "普通员工"

    # 员工看不到别人的审批详情
    admin_view = await client.get("/api/v1/approvals", headers=admin_headers)
    other_id = admin_view.json()["items"][0]["id"]
    hidden = await client.get(f"/api/v1/approvals/{other_id}", headers=employee_headers)
    assert hidden.status_code == 200  # 自己发起的那条

    someone_else = await client.post(
        "/api/v1/approvals",
        headers=admin_headers,
        json={"title": "管理员发起", "business_type": "other"},
    )
    blocked = await client.get(
        f"/api/v1/approvals/{someone_else.json()['id']}", headers=employee_headers
    )
    assert blocked.status_code == 404
