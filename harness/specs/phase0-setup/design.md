# Design — Phase 0: Setup

## Approach
Greenfield scaffold following the hexagonal architecture from `docs/architecture.md`:
- `pyproject.toml` declares runtime deps (pydantic, typer, fastapi, uvicorn, pyyaml) and
  optional adapter extras, plus dev tooling (ruff, black, mypy, pytest, pytest-asyncio).
- `src/coderag/types.py` holds frozen dataclasses and enums (the core vocabulary).
- `src/coderag/{stores,llm,retrieval}/ports.py` declare the `Protocol` boundaries.
- `src/coderag/cli.py` is a typer app with `version/ingest/query/eval` stubs.
- `.github/workflows/ci.yml` runs ruff, black --check, mypy strict, and pytest.

## Decisions
- Use `uv` for environment management; `.python-version` targets 3.13.
- mypy scoped to `src` only (harness tooling and tests excluded from strict checks).
- Region markers (`# region X`) precede every class per project conventions.
