from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import init_db
from app.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create database tables on startup.

    Using create_all here is a deliberate shortcut for the scope of this task;
    a production service would manage schema changes with migrations (Alembic).
    """
    await init_db()
    yield


app = FastAPI(title="Caching Service", lifespan=lifespan)
app.include_router(router)
