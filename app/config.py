from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.

    Values come from (in priority order) real environment variables,
    then a local .env file, then the defaults defined here.
    """

    # Async SQLite (via aiosqlite) by default so development needs zero
    # infrastructure. Overridden with an async Postgres URL
    # (postgresql+psycopg://...) through DATABASE_URL in Docker.
    database_url: str = "sqlite+aiosqlite:///./cache.db"

    # Simulated latency of the "external" transformer service, in seconds.
    # The transformer is a stand-in for a slow network call; a non-zero delay
    # gives the async fan-out in the service layer something real to overlap,
    # making the benefit of concurrency observable. Kept at 0 by default so
    # the test suite stays fast.
    transformer_delay_seconds: float = 0.0

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
