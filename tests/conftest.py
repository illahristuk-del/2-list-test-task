"""Shared test fixtures: an isolated in-memory database and an HTTP client
wired to it.

Each test gets a fresh schema, created on a single shared connection so the
in-memory database is visible across the whole test (see StaticPool below).
The app's get_session dependency is overridden to use this test database, so
no test ever touches the real one.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_session
from app.main import app


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    """A fresh in-memory database for one test, yielded as an async session.

    SQLite gives every connection to ':memory:' its own separate database, so a
    normal pool would create the schema on one connection and run the test on
    another empty one. StaticPool forces a single shared connection, keeping the
    tables visible for the whole test. The engine is torn down afterwards, so
    tests are fully isolated from one another.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s

    await engine.dispose()


@pytest_asyncio.fixture
async def client(session: AsyncSession) -> AsyncClient:
    """An HTTP client that drives the real app against the test database.

    get_session is overridden to hand out the test session, so requests flow
    through the actual routes, service and models but hit the in-memory DB.
    ASGITransport runs the app in-process — no real network, no running server.
    """

    async def _override_get_session():
        yield session

    app.dependency_overrides[get_session] = _override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
