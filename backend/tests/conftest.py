from __future__ import annotations

from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.token_store import InMemoryTokenStore, set_token_store
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from tests.helpers import (
    ADMIN_PASSWORD,
    EMPLOYEE_PASSWORD,
    MANAGER_PASSWORD,
    SeedResult,
    seed_basic,
)

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )


@pytest_asyncio.fixture
async def seeded(session_factory) -> SeedResult:
    async with session_factory() as session:
        result = await seed_basic(session)
        await session.commit()
    return result


@pytest_asyncio.fixture
async def client(session_factory) -> AsyncIterator[AsyncClient]:
    async def _override_get_db():
        async with session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db
    set_token_store(InMemoryTokenStore())

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http_client:
        yield http_client

    app.dependency_overrides.clear()
    set_token_store(None)


async def _login(
    client: AsyncClient, username: str, password: str, organization_code: str = "test"
) -> dict[str, str]:
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "username": username,
            "password": password,
            "organization_code": organization_code,
        },
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest_asyncio.fixture
async def admin_headers(client: AsyncClient, seeded: SeedResult) -> dict[str, str]:
    return await _login(client, "admin", ADMIN_PASSWORD)


@pytest_asyncio.fixture
async def manager_headers(client: AsyncClient, seeded: SeedResult) -> dict[str, str]:
    return await _login(client, "manager", MANAGER_PASSWORD)


@pytest_asyncio.fixture
async def employee_headers(client: AsyncClient, seeded: SeedResult) -> dict[str, str]:
    return await _login(client, "employee", EMPLOYEE_PASSWORD)


@pytest_asyncio.fixture
async def other_admin_headers(client: AsyncClient, seeded: SeedResult) -> dict[str, str]:
    return await _login(client, "admin", ADMIN_PASSWORD, organization_code="other")
