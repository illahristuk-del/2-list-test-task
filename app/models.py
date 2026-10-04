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
    """A generated, immutable payload, addressed by the hash of its input.

    The id is a content hash of the canonical (order-sensitive) input, so an
    identical request maps to the same row for free — this is the "reuse the
    identifier" requirement, with no extra lookup table needed. The fully
    assembled output is stored so reads are a single primary-key fetch.
    """

    id: str = Field(primary_key=True)
    output: str
