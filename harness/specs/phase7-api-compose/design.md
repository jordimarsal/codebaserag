# Design: phase7-api-compose

## Files to create or modify

- `src/coderag/api/models.py` — Pydantic request/response models: `IngestRequest`, `QueryRequest`,
  `AnswerRequest`, `ChunkOut`, `AnswerOut`, `ErrorOut`.
- `src/coderag/api/app.py` — `create_app(settings: Settings) -> FastAPI` with `POST /ingest`,
  `POST /query`, `POST /answer`; reuses `run_ingest`, `build_retriever`, `Generator`, `build_tracer`.
- `src/coderag/cli.py` — add `serve` command (`uvicorn` run of `create_app`).
- `tests/test_api.py` — `TestClient` offline round-trip (memory + fake LLM) + R8 contract assertion.
- `README.md` — document the endpoints.

## Public signatures

```python
# api/app.py
def create_app(settings: Settings) -> FastAPI:
    """Build the FastAPI app wired to the given settings."""

# api/models.py
class QueryRequest(BaseModel):
    question: str
    top_k: int = 5
    strategy: str = "dense"

class ChunkOut(BaseModel):
    path: str
    line_start: int
    line_end: int
    score: float

class AnswerRequest(BaseModel):
    question: str
    top_k: int = 5
    strategy: str = "dense"

class AnswerOut(BaseModel):
    text: str
    citations: list[str]
    confidence: float
    grounded: bool
```

## Endpoint behaviour

- `POST /ingest` — body `{repo}`; calls `run_ingest(repo, embedder, store)` using the configured
  backend; returns `{indexed: int}`. `IngestError`/`StoreError`/`EmbedderError` → 500 with `ErrorOut`.
- `POST /query` — body `QueryRequest`; builds `Retriever` (memory/pgvector/qdrant per `Settings`),
  returns `[ChunkOut, ...]`. `RetrievalError` → 400.
- `POST /answer` — body `AnswerRequest`; builds `Retriever` + `Generator(fake/llm)`, returns `AnswerOut`.
  `RetrievalError`/`GenerationError` → 400/500.

## App construction (R9)

`create_app(settings)` is a factory so tests inject a `Settings` with `store`/backend forced to
`memory` and `llm_backend="fake"` (no services). The CLI `serve` command calls `create_app(Settings())`
and runs `uvicorn` (host/port from env). The retriever/llm are built per request from `settings` so a
single app instance serves the configured backend.

## Error mapping (R7)

A small exception handler converts `RetrievalError`/`GenerationError` → 400 and
`StoreError`/`IngestError`/`EmbedderError` → 500, returning `ErrorOut`. Pydantic validation → 422
automatically.

## Eval-as-contract (R8)

`tests/test_api.py` builds `create_app(Settings(repo=".", store="memory", llm_backend="fake"))`,
ingests the repo via `POST /ingest`, then for a sample question compares `POST /query` chunk paths
with a directly constructed `Retriever(...).retrieve(question)` — they must match (same store/embedder).

## Discarded alternatives

- **New retrieval logic in the API.** Rejected: duplicates the core; the API is only an I/O boundary.
- **One monolithic `/chat` endpoint only.** Rejected: `/query` is needed to validate retrieval
  independently (and for the R8 contract test).
- **Settings baked at import time.** Rejected: a factory lets tests override backend/LLM without env
  juggling (R9).

## CLI integration (R10)

`serve --host 0.0.0.0 --port 8000` imports `create_app` and runs `uvicorn` with `Settings()`. Backend
and model come from env (`CODERAG_*`).
