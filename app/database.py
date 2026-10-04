from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import settings

# SQLite forbids sharing a connection across threads by default. aiosqlite
# drives sqlite3 from its own worker thread, so we lift that restriction.
# It is SQLite-specific, so we only pass it for SQLite URLs — this stays the
# single place in the codebase that is aware of the concrete database.
connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_async_engine(settings.database_url, connect_args=connect_args, echo=False)

# expire_on_commit=False: after a commit SQLAlchemy would otherwise expire
# instance attributes and reload them on next access. Under async that lazy
# reload needs an await and raises instead. Keeping objects usable post-commit
# avoids that whole class of bug.
async_session_factory = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def init_db() -> None:
    """Create all tables from SQLModel metadata. Called once from the app
    lifespan handler on startup. create_all is synchronous, so it runs through
    run_sync on the async connection."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async DB session and closes it after.
    Tests swap this out via dependency_overrides to point at a test engine."""
    async with async_session_factory() as session:
        yield session