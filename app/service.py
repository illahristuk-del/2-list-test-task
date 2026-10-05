import asyncio
import hashlib
import json

from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import Payload, TransformCache
from app.schemas import PayloadCreate
from app.transformer import transform


def _hash_input(data: PayloadCreate) -> str:
    """Content hash of the input, used as the payload id.

    Serializing via JSON (not a naive join) keeps the mapping injective:
    separators and quotes inside the strings are escaped, so inputs that would
    otherwise flatten to the same text — ["a,b"],["c"] vs ["a"],["b,c"] — hash
    differently. Order is preserved because it affects the interleaving.
    """
    canonical = json.dumps(
        [data.list_1, data.list_2], ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _interleave(transformed_1: list[str], transformed_2: list[str]) -> str:
    """Assemble the final payload: take one item from each list in turn."""
    pairs = zip(transformed_1, transformed_2)
    return ", ".join(value for pair in pairs for value in pair)


async def create_payload(data: PayloadCreate, session: AsyncSession) -> str:
    """Generate (or reuse) a payload for the given input, return its id.

    The transformer is treated as an expensive external call, so it is invoked
    only for strings not already in TransformCache, and only once per distinct
    string even within this request.
    """
    payload_id = _hash_input(data)

    # Reuse the identifier for an input we have already generated.
    if await session.get(Payload, payload_id) is not None:
        return payload_id

    # Deduplicate within the request so each distinct string costs at most one
    # transformer call.
    unique_strings = set(data.list_1) | set(data.list_2)

    # One round-trip to load everything already cached, instead of N queries.
    cached_rows = (
        await session.exec(
            select(TransformCache).where(TransformCache.source.in_(unique_strings))
        )
    ).all()
    cache = {row.source: row.result for row in cached_rows}

    # Call the transformer only for the misses, concurrently — this is the
    # whole point of the async stack.
    missing = [s for s in unique_strings if s not in cache]
    if missing:
        results = await asyncio.gather(*(transform(s) for s in missing))
        new_entries = dict(zip(missing, results))
        cache.update(new_entries)

        session.add_all(
            TransformCache(source=s, result=r) for s, r in new_entries.items()
        )
        try:
            await session.commit()
        except IntegrityError:
            # A concurrent request inserted an overlapping string between our
            # read and write. Its value is identical (transform is
            # deterministic), so the cache is already correct — roll back our
            # duplicate insert and carry on. The output is built from the
            # in-memory cache, so it is unaffected either way.
            await session.rollback()

    # Build the output from the now-complete cache, preserving input order.
    output = _interleave(
        [cache[s] for s in data.list_1],
        [cache[s] for s in data.list_2],
    )

    session.add(Payload(id=payload_id, output=output))
    await session.commit()
    return payload_id


async def read_payload(payload_id: str, session: AsyncSession) -> Payload | None:
    """Fetch a generated payload by id. None if it does not exist."""
    return await session.get(Payload, payload_id)
