import asyncio

from app.config import settings


async def transform(value: str) -> str:
    """Transform a single string, standing in for a call to a slow external
    service.

    The real service would be network-bound; we model that with an optional
    delay so the async fan-out in the service layer has something to overlap.
    The actual work is a trivial upper-casing — the point of this task is the
    caching around the call, not the transformation itself.
    """
    if settings.transformer_delay_seconds:
        await asyncio.sleep(settings.transformer_delay_seconds)
    return value.upper()
