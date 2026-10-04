from pydantic import BaseModel, model_validator


class PayloadCreate(BaseModel):
    """Request body for POST /payload: two equal-length lists of strings.
    The interleaving only makes sense when both lists line up one-to-one, so a
    length mismatch is rejected here as a contract violation — FastAPI turns a
    failed validator into a 422 automatically, keeping this check out of the
    service layer.
    """
    list_1: list[str]
    list_2: list[str]

    @model_validator(mode="after")
    def lists_must_match_length(self) -> "PayloadCreate":
        if len(self.list_1) != len(self.list_2):
            raise ValueError("list_1 and list_2 must have the same length")
        return self


class PayloadCreateResponse(BaseModel):
    """Response for POST /payload: a confirmation plus the payload id to read back."""

    message: str
    id: str


class PayloadReadResponse(BaseModel):
    """Response for GET /payload/{id}: the assembled, interleaved output string."""

    output: str