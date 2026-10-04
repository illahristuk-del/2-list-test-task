from sqlmodel import Field, SQLModel

class TransformCache(SQLModel, table=True):
    """Per-string cache of the transformer's output.
    Keyed by the raw source string: the transform is deterministic, so a
    string uniquely identifies its result. This is what lets us avoid
    re-calling the transformer for any string seen in an earlier request.
    """
    source: str = Field(primary_key=True)
    result: str


class Payload(SQLModel, table=True):
    """Per-string cache of the transformer's output.

    Keyed by the raw source string: the transform is deterministic, so a
    string uniquely identifies its result. This is what lets us avoid
    re-calling the transformer for any string seen in an earlier request.
    """

    id: str = Field(primary_key=True)
    output: str