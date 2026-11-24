from __future__ import annotations

from httpx import AsyncClient


async def test_create_and_list_ticket(
    client: AsyncClient, employee_headers, admin_headers
) -> None:
    created = await client.post(
        "/api/v1/tickets",
        headers=employee_headers,
        json={"title": "三楼打印机卡纸", "description": "换硒鼓也没用", "priority": "high"},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["status"] == "pending"
    assert body["ticket_no"].startswith("T")
    assert body["creator_name"] == "普通员工"

    mine = await client.get("/api/v1/tickets", headers=employee_headers)
    assert mine.status_code == 200
    assert mine.json()["total"] == 1

    all_tickets = await client.get("/api/v1/tickets", headers=admin_headers)
    assert all_tickets.json()["total"] == 1


async def test_assign_and_status_transitions(
    client: AsyncClient, employee_headers, admin_headers, seeded
) -> None:
    created = await client.post(
        "/api/v1/tickets",
        headers=employee_headers,
        json={"title": "会议室投影仪不亮"},
    )
    ticket_id = created.json()["id"]

    # 员工没有 ticket:update，不能自己把单子推成「已解决」
    denied = await client.patch(
        f"/api/v1/tickets/{ticket_id}",
        headers=employee_headers,
        json={"status": "resolved"},
    )
    assert denied.status_code == 403

    # 指派人 → 自动进入处理中
    assigned = await client.patch(
        f"/api/v1/tickets/{ticket_id}",
        headers=admin_headers,
        json={"assignee_id": seeded.manager_id},
    )
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()["status"] == "processing"
    assert assigned.json()["assignee_name"] == "部门经理"

    resolved = await client.patch(
        f"/api/v1/tickets/{ticket_id}",
        headers=admin_headers,
        json={"status": "resolved", "remark": "已更换灯泡"},
    )
    assert resolved.json()["status"] == "resolved"
    # 创建 + 指派 + 解决 = 3 条流转记录
    assert len(resolved.json()["histories"]) == 3

    closed = await client.patch(
        f"/api/v1/tickets/{ticket_id}",
        headers=admin_headers,
        json={"status": "closed"},
    )
    assert closed.json()["status"] == "closed"

    # 已关闭不能再动
    reopen = await client.patch(
        f"/api/v1/tickets/{ticket_id}",
        headers=admin_headers,
        json={"status": "processing"},
    )
    assert reopen.status_code == 400


async def test_creator_can_close_own_ticket(
    client: AsyncClient, employee_headers
) -> None:
    created = await client.post(
        "/api/v1/tickets", headers=employee_headers, json={"title": "自己关掉的单子"}
    )
    ticket_id = created.json()["id"]

    closed = await client.patch(
        f"/api/v1/tickets/{ticket_id}",
        headers=employee_headers,
        json={"status": "closed"},
    )
    assert closed.status_code == 200, closed.text
    assert closed.json()["status"] == "closed"


async def test_comment_and_visibility(
    client: AsyncClient, employee_headers, admin_headers
) -> None:
    created = await client.post(
        "/api/v1/tickets", headers=admin_headers, json={"title": "管理员工单"}
    )
    ticket_id = created.json()["id"]

    # 别人看不到不属于自己的工单
    invisible = await client.get(f"/api/v1/tickets/{ticket_id}", headers=employee_headers)
    assert invisible.status_code == 404

    comment = await client.post(
        f"/api/v1/tickets/{ticket_id}/comments",
        headers=admin_headers,
        json={"content": "已收到，今天处理"},
    )
    assert comment.status_code == 201

    detail = await client.get(f"/api/v1/tickets/{ticket_id}", headers=admin_headers)
    assert detail.json()["comments"][0]["content"] == "已收到，今天处理"
    assert detail.json()["comments"][0]["user_name"] == "系统管理员"
