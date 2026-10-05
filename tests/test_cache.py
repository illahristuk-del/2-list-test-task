"""The core requirement: the transformer is called as little as possible.

These tests patch the transformer so we can count exactly how many times it
runs, proving that cached strings are never re-transformed — neither within a
request (duplicates) nor across requests (the per-string cache).
"""

from unittest.mock import AsyncMock, patch

from app.schemas import PayloadCreate
from app.service import create_payload


async def test_duplicate_strings_transformed_once(session):
    """A string repeated within one request must reach the transformer once."""
    data = PayloadCreate(list_1=["a", "a"], list_2=["a", "a"])

    with patch("app.service.transform", new_callable=AsyncMock) as mock:
        mock.side_effect = lambda s: s.upper()
        await create_payload(data, session)

    # Four slots, but all the same string → exactly one transform call.
    mock.assert_awaited_once()


async def test_cache_hit_skips_transformer_across_requests(session):
    """A string transformed in an earlier request is served from the DB cache
    and never reaches the transformer again."""
    first = PayloadCreate(list_1=["hello"], list_2=["world"])
    second = PayloadCreate(list_1=["hello"], list_2=["brand new"])

    with patch("app.service.transform", new_callable=AsyncMock) as mock:
        mock.side_effect = lambda s: s.upper()

        await create_payload(first, session)
        assert mock.await_count == 2  # "hello", "world" — both new

        mock.reset_mock()
        await create_payload(second, session)
        # "hello" is cached from the first request → only "brand new" is new.
        mock.assert_awaited_once()
        mock.assert_awaited_with("brand new")


async def test_reused_payload_skips_transformer_entirely(session):
    """An identical repeated request reuses the payload id and does not touch
    the transformer at all (fast path)."""
    data = PayloadCreate(list_1=["x"], list_2=["y"])

    with patch("app.service.transform", new_callable=AsyncMock) as mock:
        mock.side_effect = lambda s: s.upper()

        id_1 = await create_payload(data, session)
        assert mock.await_count == 2  # first time: both strings new

        mock.reset_mock()
        id_2 = await create_payload(data, session)
        mock.assert_not_awaited()  # same input → payload reused, no transform

    assert id_1 == id_2
