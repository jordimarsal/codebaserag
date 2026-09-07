# Tasks: phase7-api-compose

- [x] T1: Create `src/coderag/api/models.py` — Pydantic `IngestRequest`, `QueryRequest`, `AnswerRequest`,
      `ChunkOut`, `AnswerOut`, `ErrorOut`.
      depends_on: (none)
      refs: R5

- [x] T2: Create `src/coderag/api/app.py` — `create_app(settings)` with `POST /ingest`, `POST /query`,
      `POST /answer`; reuse `run_ingest`/`build_retriever`/`Generator`/`build_tracer`; exception handlers
      mapping core errors to HTTP status (R7).
      depends_on: T1
      refs: R1, R2, R3, R4, R6, R7

- [x] T3: Add `serve` command to `src/coderag/cli.py` (uvicorn run of `create_app(Settings())`).
      depends_on: T2
      refs: R10

- [x] T4: Write `tests/test_api.py` — `TestClient` offline round-trip (memory + fake LLM) for all three
      endpoints; R8 contract test asserting `POST /query` paths == core `Retriever` output; 422 on bad input.
      depends_on: T2
      refs: R8, R9

- [x] T5: Document endpoints in `README.md`; run gates; update `harness/progress/current.md`.
      depends_on: T2, T3, T4
      refs: R2
