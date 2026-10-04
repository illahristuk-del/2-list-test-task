from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database import get_session
from app.schemas import PayloadCreate, PayloadCreateResponse, PayloadReadResponse
from app.service import create_payload, read_payload

router = APIRouter()


@router.post("/payload", response_model=PayloadCreateResponse, status_code=201)
async def create(
    data: PayloadCreate, session: AsyncSession = Depends(get_session)
) -> PayloadCreateResponse:
    """Create (or reuse) a payload from two equal-length lists of strings.

    Returns the identifier; the same input always maps to the same id, so a
    repeated request is a cheap lookup rather than a regeneration.
    """
    payload_id = await create_payload(data, session)
    return PayloadCreateResponse(message="Payload created", id=payload_id)


@router.get("/payload/{payload_id}", response_model=PayloadReadResponse)
async def read(
    payload_id: str, session: AsyncSession = Depends(get_session)
) -> PayloadReadResponse:
    """Return the generated payload for the given id, or 404 if unknown."""
    payload = await read_payload(payload_id, session)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Payload not found"
        )
    return PayloadReadResponse(output=payload.output)
