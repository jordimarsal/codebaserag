# Conventions

This document defines the coding and project conventions for `codebase-rag`. These rules
enforce extreme homogeneity across the codebase so any developer can open any file and
immediately understand its structure, naming, and intent. They are adapted from the
project's Python engineering standard (`AGENTS_pk.md`) for the hexagonal RAG design
described in `01-rag-codi-propis.md` and `docs/architecture.md`.

**Language policy.** All source code, code comments, docstrings, test descriptions, and
READMEs inside the repository are written in **English**. Discussion outside the repository
may use other languages; repository content stays English-only.

**Typing policy.** Python type hints are mandatory everywhere. Target Python 3.13. Use
`mypy --strict`. Avoid `Any` unless strictly required at external boundaries.

---

## Style Rules

- Mandatory type hints on all public functions/classes; avoid `Any` unless unavoidable at
  boundaries. When you must, alias it explicitly: `Json = dict[str, Any]`.
- Prefer small, cohesive functions with low cyclomatic complexity.
- Keep diffs minimal; avoid unrelated formatting changes.
- Use `.get(key, default)` when accessing dictionary keys to prevent `KeyError`.
- Put module constants in quotes, group them thematically with comment separators.
- Avoid nested functions unless forming a closure over a local value other than `self`/`cls`.
- Format with `black`; lint with `ruff`; type-check with `mypy --strict`.
- No icons/emojis in logs or test messages; keep them plain text.

### Project layout

```
src/coderag/
  ingest/       # readers, chunkers (fixed, recursive, ast), pipeline
  retrieval/    # dense, bm25, fusion (rrf), reranker
  generation/   # prompt builder, structured output, citations
  stores/       # protocols + pgvector + qdrant adapters
  llm/          # provider adapters (ollama, anthropic, openai)
  api/          # FastAPI
  cli.py        # typer: ingest / query / eval
evals/          # golden dataset, harness, versioned reports
adr/            # ADR-001 chunking, ADR-002 embeddings, ...
tests/          # pure-core unit + integration (compose)
```

---

## Naming Rules

- Modules/packages: `snake_case`. Classes: `CapWords`. Functions/variables: `snake_case`.
  Constants: `UPPER_SNAKE_CASE`.
- Ports are `Protocol` types named by role: `VectorStore`, `Embedder`, `LlmClient`,
  `Reranker`. Adapters are named `<Provider><Port>`: `PgvectorStore`, `QdrantStore`,
  `OllamaEmbedder`, `AnthropicLlm`.
- DTOs/Value Objects are `@dataclass` (prefer `frozen=True`): `Chunk`, `Citation`,
  `RetrievalResult`. Closed sets are `Enum`.
- Public packages expose a stable surface via `__init__.py` and `__all__`.

---

## File Structure

- **Data modeling first.** Prefer semantic types over loose dictionaries:
  - `Enum` for closed sets.
  - `@dataclass(frozen=True)` for DTO/VO. Avoid raw `dict[str, Any]` except at external
    API boundaries.
- **Region markers.** Two blank lines before each class, add a region header with the
  class name:

```python
from dataclasses import dataclass
from enum import Enum


# region ChunkStatus
class ChunkStatus(Enum):
    PENDING = "PENDING"
    INDEXED = "INDEXED"


# region Chunk
@dataclass(frozen=True)
class Chunk:
    path: str
    line_start: int
    line_end: int
    text: str
```

- **Single responsibility.** If a module grows beyond one responsibility, split by cohesion
  into multiple modules; group related modules into a new package. Keep `cli.py` and `api/`
  as thin orchestration surfaces.
- **Dependency boundaries.** Compose services by injecting collaborators, not global state.
  Keep imports at the top of each file. Avoid circular imports; move shared types to a
  neutral module. Keep I/O at the edges; core logic stays pure.

---

## Test Rules

- Tests live under `tests/` (pure-core units) and integration tests use Compose.
  Eval suites live under `evals/`.
- Write tests in English (names, messages, docstrings). Cover happy paths plus 1–2 edge
  cases, error cases (invalid inputs, missing context), and enum/dataclass serialization
  semantics where applicable.
- Use `pytest` parametrization for matrix-like cases. Async tests use `pytest-asyncio`.
- Mark eval tests with `@pytest.mark.eval`. Deterministic retrieval/citation evals run in
  CI on every PR; LLM-judge evals run nightly/manual.
- Do not merge with failing tests. Run the eval harness before changing any core component.
- Quick commands:

```bash
# Unit tests
pytest -q tests

# One file / test
pytest -q tests/test_chunking.py::test_fixed_size

# Eval harness
python -m evals.harness
```

---

## Error Handling

- Raise specific exceptions (`ValueError`, `TypeError`, custom domain errors). Never use a
  blanket `except Exception:`.
- Do not nest `try/except`, and do not combine `finally` with `try/except` awkwardly.
  Keep exception handling as close as possible to the source of the error.
- Make functions small and single-purpose where exceptions are expected.
- Keep core logic pure; let adapters translate provider errors into domain exceptions at
  the boundary.
- Logging uses the project logger (no `print`). Build all log messages with `%s`
  formatting—never f-strings or string interpolation inside the log call.

---

## Quality Gates (before submitting changes)

1. Import-check / build.
2. `ruff check --fix --show-fixes .`
3. `black .`
4. `mypy --check-untyped-defs --strict .`
5. `pytest -q tests` and the deterministic eval suite green.

## Documentation

- Add docstrings to all public functions/classes (concise; inputs, outputs, error modes).
  Private helpers get a brief docstring only when non-obvious.
- Update or create READMEs near new features. Keep the top-level `README.md` metrics table
  (baseline vs current) up to date after each experiment.
- Record trade-off decisions as short ADRs under `adr/` (e.g. `ADR-001-chunking.md`).

## Acceptance Criteria for Changes

- Code in English with mandatory type hints and dataclasses/enums.
- Region markers present two lines before each class.
- Ports defined as `Protocol`; no adapter imported in the core.
- Tests added/updated and passing locally; evals green against baseline.
- Single responsibility respected; refactors split by cohesion when modules grow.
- Minimal diffs; no broken imports; `ruff`/`black`/`mypy --strict` clean.
