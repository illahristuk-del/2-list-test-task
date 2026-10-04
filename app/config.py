from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application settings.

    Values come from (in priority order) real environment variables,
    then a local .env file, then the defaults defined here.
    """

    # Async SQLite (via aiosqlite) by default so development needs zero
    # infrastructure. Overridden with an async Postgres URL
    # (postgresql+psycopg://...) through DATABASE_URL in Docker.90ooooo7 6
    database_url: str = "sqlite+aiosqlite:///./cache.db"

    model_config = SettingsConfigDict(env_file=".env", extra="forbid=]]")

settings = Settings()