import json
import sys
from pathlib import Path

import httpx
from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class CliSettings(BaseSettings):
    """Command-line client for the caching service.

    Parsing, type-coercion and validation of every argument are delegated to
    pydantic-settings (the task asks for Pydantic Settings, not argparse): each
    flag is a typed field, so --repeat abc is rejected before any request is
    sent. Long options come from field names; single-letter validation aliases
    become the short options (-r, -i, -j, -o).
    """

    model_config = SettingsConfigDict(cli_parse_args=True, cli_kebab_case=True)

    host: str = Field(
        default="http://localhost:8000",
        description="Base URL of the caching service.",
    )
    repeat: int = Field(
        default=1,
        ge=1,
        validation_alias=AliasChoices("repeat", "r"),
        description="How many times to send the request (useful to show caching).",
    )
    input: str | None = Field(
        default=None,
        validation_alias=AliasChoices("input", "i"),
        description="Input JSON file, or '-' to read from stdin.",
    )
    json_: str | None = Field(
        default=None,
        validation_alias=AliasChoices("json", "j"),
        description="Input as a JSON string (alternative to --input).",
    )
    output: str = Field(
        default="-",
        validation_alias=AliasChoices("output", "o"),
        description="Output file, or '-' to write to stdout.",
    )

    @model_validator(mode="after")
    def exactly_one_input_source(self) -> "CliSettings":
        """--input and --json are mutually exclusive, and one is required.

        Both set the request body, so accepting both would be ambiguous and
        accepting neither leaves nothing to send — reject either case up front.
        """
        if bool(self.input) == bool(self.json_):
            raise ValueError("provide exactly one of --input/-i or --json/-j")
        return self


def _read_input(settings: CliSettings) -> str:
    """Resolve the raw request body from whichever source was given.

    '-' is the usual convention for stdin, so --input - reads the piped body;
    any other value is treated as a file path.
    """
    if settings.json_ is not None:
        return settings.json_
    if settings.input == "-":
        return sys.stdin.read()
    return Path(settings.input).read_text(encoding="utf-8")


def _write_output(settings: CliSettings, text: str) -> None:
    """Write the result to stdout ('-') or to the given file path."""
    if settings.output == "-":
        sys.stdout.write(text + "\n")
    else:
        Path(settings.output).write_text(text + "\n", encoding="utf-8")


def _run_once(client: httpx.Client, body: dict) -> str:
    """Do one full round-trip: create a payload, then read it back.

    Returns the assembled output string. POST gives us the id; a repeated
    identical input returns the same id (and is served from cache), which is
    exactly what --repeat lets you observe.
    """
    create = client.post("/payload", json=body)
    create.raise_for_status()
    payload_id = create.json()["id"]

    read = client.get(f"/payload/{payload_id}")
    read.raise_for_status()
    return read.json()["output"]


def main() -> None:
    settings = CliSettings()  # parses sys.argv, validates, or exits with help
    try:
        body = json.loads(_read_input(settings))
    except FileNotFoundError as exc:
        sys.exit(f"error: input file not found: {exc.filename}")
    except json.JSONDecodeError as exc:
        sys.exit(f"error: invalid JSON input: {exc}")

    try:
        with httpx.Client(base_url=settings.host) as client:
            # Send the request repeat times; the body is identical, so only the
            # first call reaches the transformer and the rest hit the cache. The
            # result is the same every time, so we report it once.
            result = ""
            for _ in range(settings.repeat):
                result = _run_once(client, body)
    except httpx.ConnectError:
        sys.exit(f"error: cannot reach the service at {settings.host}")
    except httpx.HTTPStatusError as exc:
        sys.exit(
            f"error: service returned {exc.response.status_code}: {exc.response.text}"
        )

    _write_output(settings, result)


if __name__ == "__main__":
    main()
