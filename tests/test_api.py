"""End-to-end tests through the real HTTP stack against the test database.

These exercise routes, service, schemas and models together via an in-process
ASGI client, with no running server.
"""


async def test_create_then_read(client):
    """Full happy path: POST returns an id, GET returns the assembled output
    in the exact format from the task description."""
    body = {
        "list_1": ["first string", "second string", "third string"],
        "list_2": ["other string", "another string", "last string"],
    }
    create = await client.post("/payload", json=body)
    assert create.status_code == 201
    payload_id = create.json()["id"]

    read = await client.get(f"/payload/{payload_id}")
    assert read.status_code == 200
    assert read.json()["output"] == (
        "FIRST STRING, OTHER STRING, SECOND STRING, "
        "ANOTHER STRING, THIRD STRING, LAST STRING"
    )


async def test_same_input_reuses_id(client):
    """Posting identical input twice returns the same id (reuse requirement)."""
    body = {"list_1": ["a"], "list_2": ["b"]}

    first = await client.post("/payload", json=body)
    second = await client.post("/payload", json=body)

    assert first.json()["id"] == second.json()["id"]


async def test_read_unknown_id_returns_404(client):
    """An id that was never created yields 404, not an empty 200."""
    read = await client.get("/payload/does-not-exist")
    assert read.status_code == 404


async def test_mismatched_lengths_returns_422(client):
    """Lists of unequal length violate the contract and are rejected by the
    schema validator before reaching the service."""
    body = {"list_1": ["a", "b"], "list_2": ["c"]}
    create = await client.post("/payload", json=body)
    assert create.status_code == 422
