"""产品五件套：多级审批、附件、通知、强制改密、assignee_me。"""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User
from tests.helpers import ADMIN_PASSWORD, EMPLOYEE_PASSWORD


@pytest.fixture
def isolate_uploads(tmp_path, monkeypatch):
    target = tmp_path / "uploads"
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(target))
    return target


async def test_assignee_me_filter(
    client: AsyncClient, employee_headers, admin_headers, manager_headers, seeded
) -> None:
    created = await client.post(
        "/api/v1/tickets",
        headers=employee_headers,
        json={"title": "待我处理筛选", "priority": "medium"},
    )
    ticket_id = created.json()["id"]

    await client.patch(
        f"/api/v1/tickets/{ticket_id}",
        headers=admin_headers,
        json={"assignee_id": seeded.manager_id},
    )

    mine = await client.get(
        "/api/v1/tickets",
        headers=manager_headers,
        params={"assignee_me": True},
    )
    assert mine.status_code == 200
    assert mine.json()["total"] >= 1
    assert any(item["id"] == ticket_id for item in mine.json()["items"])

    employee_todo = await client.get(
        "/api/v1/tickets",
        headers=employee_headers,
        params={"assignee_me": True},
    )
    assert employee_todo.json()["total"] == 0


async def test_multi_level_approval_and_notifications(
    client: AsyncClient, employee_headers, manager_headers, admin_headers, seeded
) -> None:
    created = await client.post(
        "/api/v1/approvals",
        headers=employee_headers,
        json={
            "title": "两级串签报销",
            "business_type": "expense",
            "amount": 1200,
            "approver_ids": [seeded.manager_id, seeded.admin_id],
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    instance_id = body["id"]
    assert body["status"] == "pending"
    assert body["current_node"] == 1

    detail = await client.get(
        f"/api/v1/approvals/{instance_id}", headers=employee_headers
    )
    tasks = detail.json()["tasks"]
    assert len(tasks) == 2
    assert tasks[0]["status"] == "pending"
    assert tasks[1]["status"] == "waiting"

    # 第一级：经理通过 → 仍 pending，切到第二级
    step1 = await client.post(
        f"/api/v1/approvals/{instance_id}/decision",
        headers=manager_headers,
        json={"action": "approve", "comment": "部门同意"},
    )
    assert step1.status_code == 200, step1.text
    assert step1.json()["status"] == "pending"
    assert step1.json()["current_node"] == 2
    assert step1.json()["tasks"][0]["status"] == "approved"
    assert step1.json()["tasks"][1]["status"] == "pending"

    # 第二级未到管理员之前，经理不能再批
    again = await client.post(
        f"/api/v1/approvals/{instance_id}/decision",
        headers=manager_headers,
        json={"action": "approve"},
    )
    assert again.status_code == 403

    step2 = await client.post(
        f"/api/v1/approvals/{instance_id}/decision",
        headers=admin_headers,
        json={"action": "approve", "comment": "财务同意"},
    )
    assert step2.status_code == 200
    assert step2.json()["status"] == "approved"

    # 申请人应收到通过通知；经理/管理员应收到过待办通知
    notify = await client.get("/api/v1/notifications", headers=employee_headers)
    assert notify.status_code == 200
    titles = [item["title"] for item in notify.json()["items"]]
    assert any("已通过" in title for title in titles)

    manager_unread = await client.get(
        "/api/v1/notifications/unread-count", headers=manager_headers
    )
    assert manager_unread.status_code == 200
    assert manager_unread.json()["count"] >= 1


async def test_multi_level_reject_stops_flow(
    client: AsyncClient, employee_headers, manager_headers, admin_headers, seeded
) -> None:
    created = await client.post(
        "/api/v1/approvals",
        headers=employee_headers,
        json={
            "title": "会被驳回的采购",
            "business_type": "purchase",
            "approver_ids": [seeded.manager_id, seeded.admin_id],
        },
    )
    instance_id = created.json()["id"]

    rejected = await client.post(
        f"/api/v1/approvals/{instance_id}/decision",
        headers=manager_headers,
        json={"action": "reject", "comment": "预算不够"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert rejected.json()["tasks"][1]["status"] == "waiting"

    # 第二级不能再批
    denied = await client.post(
        f"/api/v1/approvals/{instance_id}/decision",
        headers=admin_headers,
        json={"action": "approve"},
    )
    assert denied.status_code == 400


async def test_attachment_upload_download_delete(
    client: AsyncClient, employee_headers, isolate_uploads: Path
) -> None:
    created = await client.post(
        "/api/v1/tickets",
        headers=employee_headers,
        json={"title": "带附件的工单"},
    )
    ticket_id = created.json()["id"]

    upload = await client.post(
        f"/api/v1/attachments/tickets/{ticket_id}",
        headers=employee_headers,
        files={"file": ("说明.txt", b"hello attachment", "text/plain")},
    )
    assert upload.status_code == 200, upload.text
    file_id = upload.json()["id"]
    assert upload.json()["filename"] == "说明.txt"

    detail = await client.get(f"/api/v1/tickets/{ticket_id}", headers=employee_headers)
    assert len(detail.json()["attachments"]) == 1

    download = await client.get(
        f"/api/v1/attachments/{file_id}/download",
        headers=employee_headers,
    )
    assert download.status_code == 200
    assert download.content == b"hello attachment"

    deleted = await client.delete(
        f"/api/v1/attachments/{file_id}", headers=employee_headers
    )
    assert deleted.status_code == 200

    detail2 = await client.get(f"/api/v1/tickets/{ticket_id}", headers=employee_headers)
    assert detail2.json()["attachments"] == []


async def test_ticket_assign_creates_notification(
    client: AsyncClient, employee_headers, admin_headers, manager_headers, seeded
) -> None:
    created = await client.post(
        "/api/v1/tickets",
        headers=employee_headers,
        json={"title": "指派通知验证"},
    )
    ticket_id = created.json()["id"]

    await client.patch(
        f"/api/v1/tickets/{ticket_id}",
        headers=admin_headers,
        json={"assignee_id": seeded.manager_id},
    )

    unread = await client.get(
        "/api/v1/notifications/unread-count", headers=manager_headers
    )
    assert unread.json()["count"] >= 1

    listed = await client.get("/api/v1/notifications", headers=manager_headers)
    item = next(
        i for i in listed.json()["items"] if i.get("link_id") == ticket_id
    )
    assert item["link_type"] == "ticket"
    assert item["is_read"] is False

    marked = await client.post(
        f"/api/v1/notifications/{item['id']}/read",
        headers=manager_headers,
    )
    assert marked.status_code == 200
    assert marked.json()["is_read"] is True


async def test_must_change_password_flag(
    client: AsyncClient, admin_headers, session_factory, seeded
) -> None:
    async with session_factory() as session:
        user = User(
            organization_id=seeded.org_id,
            username="newbie",
            password_hash=hash_password("Newbie@123"),
            real_name="新员工",
            email="newbie@example.com",
            status=1,
            must_change_password=1,
        )
        session.add(user)
        await session.commit()

    login = await client.post(
        "/api/v1/auth/login",
        json={
            "username": "newbie",
            "password": "Newbie@123",
            "organization_code": "test",
        },
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = await client.get("/api/v1/auth/me", headers=headers)
    assert me.json()["must_change_password"] is True

    changed = await client.put(
        "/api/v1/auth/me/password",
        headers=headers,
        json={"old_password": "Newbie@123", "new_password": "Newbie@456"},
    )
    assert changed.status_code == 200, changed.text

    me2 = await client.get("/api/v1/auth/me", headers=headers)
    # 改密后旧 token 仍可用，但标记应已清零
    assert me2.json()["must_change_password"] is False


async def test_cannot_choose_self_as_approver(
    client: AsyncClient, employee_headers, seeded
) -> None:
    resp = await client.post(
        "/api/v1/approvals",
        headers=employee_headers,
        json={
            "title": "自己批自己",
            "approver_ids": [seeded.employee_id],
        },
    )
    assert resp.status_code == 400
