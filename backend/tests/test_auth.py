from __future__ import annotations

from httpx import AsyncClient

from tests.helpers import ADMIN_PASSWORD


async def test_health(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "up"


async def test_root(client: AsyncClient) -> None:
    response = await client.get("/")
    assert response.status_code == 200
    assert response.json()["api_prefix"] == "/api/v1"


async def test_login_success(client: AsyncClient, seeded) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": ADMIN_PASSWORD, "organization_code": "test"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0


async def test_login_wrong_password(client: AsyncClient, seeded) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "wrong-password", "organization_code": "test"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


async def test_login_unknown_org(client: AsyncClient, seeded) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": ADMIN_PASSWORD, "organization_code": "nope"},
    )
    assert response.status_code == 401


async def test_me_returns_permissions(client: AsyncClient, admin_headers) -> None:
    response = await client.get("/api/v1/auth/me", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "admin"
    assert body["is_superuser"] is True
    assert "user:create" in body["permissions"]
    assert body["organization_name"] == "测试企业"
    assert any(role["code"] == "super_admin" for role in body["roles"])


async def test_me_requires_token(client: AsyncClient, seeded) -> None:
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401


async def test_refresh_rotates_token(client: AsyncClient, seeded) -> None:
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": ADMIN_PASSWORD, "organization_code": "test"},
    )
    refresh_token = login.json()["refresh_token"]

    first = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert first.status_code == 200
    assert first.json()["access_token"]

    # 旧的刷新令牌已经轮换作废
    second = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert second.status_code == 401


async def test_logout_revokes_access_token(client: AsyncClient, admin_headers) -> None:
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": ADMIN_PASSWORD, "organization_code": "test"},
    )
    tokens = login.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    logout = await client.post(
        "/api/v1/auth/logout",
        headers=headers,
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert logout.status_code == 200

    me = await client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 401


async def test_invalid_access_token(client: AsyncClient, seeded) -> None:
    response = await client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401


async def test_update_profile(client: AsyncClient, admin_headers) -> None:
    response = await client.put(
        "/api/v1/auth/me", headers=admin_headers, json={"real_name": "新名字"}
    )
    assert response.status_code == 200
    assert response.json()["real_name"] == "新名字"


async def test_change_password(client: AsyncClient, admin_headers) -> None:
    response = await client.put(
        "/api/v1/auth/me/password",
        headers=admin_headers,
        json={"old_password": ADMIN_PASSWORD, "new_password": "NewPassw0rd"},
    )
    assert response.status_code == 200

    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "NewPassw0rd", "organization_code": "test"},
    )
    assert login.status_code == 200
