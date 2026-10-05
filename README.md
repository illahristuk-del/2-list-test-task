# Caching Service

A small FastAPI microservice that caches the output of an expensive
"transformer" operation. `POST /payload` takes two equal-length lists of
strings, transforms each string (upper-casing, standing in for an external
service), interleaves the two transformed lists, and returns an identifier.
`GET /payload/{id}` returns the stored result.

Two caching layers keep the transformer calls to a minimum:

- a **per-string cache** — a string is never transformed twice, across any
  requests;
- a **per-request payload cache** — an identical request reuses its id and is
  served without touching the transformer.

## Requirements

- Python 3.12+
- Docker and Docker Compose (only for the Postgres setup)

## Running locally (SQLite)

No infrastructure needed — the app defaults to a local SQLite file.

```bash
python -m venv .venv
source .venv/Scripts/activate      # Windows (Git Bash); on Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API is then at `http://localhost:8000`, with interactive docs at
`http://localhost:8000/docs`.

### Example requests

```bash
# Create a payload — returns an id
curl -X POST http://localhost:8000/payload \
  -H "Content-Type: application/json" \
  -d '{"list_1": ["first string", "second string"], "list_2": ["other string", "another string"]}'

# Read it back by id
curl http://localhost:8000/payload/<id>
```

A create returns `201` with `{"message": ..., "id": ...}`; a read returns
`200` with `{"output": "FIRST STRING, OTHER STRING, SECOND STRING, ANOTHER STRING"}`.
Unequal list lengths return `422`; an unknown id returns `404`.

## Running with Docker (Postgres)

```bash
cp .env.example .env     # then edit the credentials if you like
docker compose up --build
```

This starts Postgres and the app together. The app waits for the database to
be healthy before starting, so the schema is created cleanly on boot. The API
is at `http://localhost:8000` as above, now backed by Postgres.

## CLI

A small client is included to exercise the service from the command line. It is
built on Pydantic Settings, so every flag is typed and validated.

```bash
# JSON passed as a string
python -m cli.main --json '{"list_1": ["a"], "list_2": ["b"]}' --output -

# input from a file, or from stdin with '-'
python -m cli.main --input data.json --output -
echo '{"list_1": ["a"], "list_2": ["b"]}' | python -m cli.main --input - --output -

# repeat the same request (useful to observe caching)
python -m cli.main --json '{"list_1": ["a"], "list_2": ["b"]}' --repeat 3 --output -
```

Flags: `--host` (default `http://localhost:8000`), `-r/--repeat`, `-i/--input`
(`-` for stdin), `-j/--json`, `-o/--output` (`-` for stdout). Exactly one of
`--input` or `--json` must be given.

> Note: passing JSON via `--json` works reliably in Git Bash / Linux. In
> PowerShell, shell quoting mangles the JSON — use `--input` with a file there.

## Tests

```bash
pytest
```

15 tests: unit tests for the hashing and interleaving logic, cache tests that
prove the transformer is called as few times as possible, and integration
tests that run the full HTTP stack against an in-memory database.

## Architecture notes

- **Async across the stack.** The transformer models an external I/O service,
  so the whole stack is async; cache-miss strings are transformed concurrently
  with `asyncio.gather`.
- **Two caching layers.** Per-string (saves transformer calls across requests)
  and per-payload (id reuse and a cheap read).
- **Database-agnostic.** Knowledge of the concrete database lives in a single
  `connect_args` line; the same code runs on SQLite (local) and Postgres
  (Docker), both verified live.
- **Layer separation.** API schemas are separate from DB tables; the service
  takes the session as a parameter (testability); routes are thin.

## Deliberate shortcuts

The task allows shortcuts "as long as they are clearly documented and
justified". The following were taken on purpose, scaled to the exercise:

1. **The final `Payload` insert race is not guarded.** Two identical concurrent
   requests could both reach the payload insert and the second would get an
   `IntegrityError` on commit. Only the transform-cache insert is guarded. In
   production: guard the final commit too, or use upsert/retry.
2. **`asyncio.gather` without a semaphore.** Unbounded fan-out to the
   transformer. Fine here; production would bound concurrency.
3. **The cache race is caught per batch, not per row.** One conflicting row
   rolls back the whole cache batch — harmless (rows are re-cached next request,
   output is built from memory), but loses some batch efficiency under a race.
4. **`create_all` instead of migrations.** Schema is created from scratch;
   production would use Alembic.
5. **`settings` and `engine` are module-level singletons.** Tests override the
   session via `dependency_overrides` rather than reconfiguring them.
6. **SQLite is detected by URL prefix**, because `connect_args` is needed before
   the engine exists.
7. **`extra="ignore"` in settings**, because the shared `.env` carries Postgres
   credentials that are not addressed to the app.
8. **The CLI is run as `python -m cli.main`**, not a `cache-cli` command; in
   production it would be a packaged entry-point.