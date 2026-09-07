# Tasks: phase1-ingest-pgvector

- [x] T1: Create `src/coderag/config.py` with pydantic `Settings` (DSN, embedder URL/model, chunk size) and env/.env loading.
      depends_on: (none)
      refs: R12

- [x] T2: Implement `src/coderag/ingest/readers.py` — `discover_files` (extension filter) + `.gitignore`/`.git` skipping via `is_ignored`.
      depends_on: (none)
      refs: R1, R2

- [x] T3: Implement `src/coderag/ingest/chunkers.py` — `chunk_fixed` (windowed by lines, `line_start`/`line_end`, language tag) and `chunk_text` dispatcher; `hash` via sha256.
      depends_on: (none)
      refs: R3, R4, R5

- [x] T4: Implement `src/coderag/ingest/pipeline.py` — `run_ingest` orchestrating read → chunk → embed → store, raising `IngestError` on per-file failures (R11).
      depends_on: T2, T3
      refs: R6, R10, R11

- [x] T5: Implement `src/coderag/stores/pgvector.py` — `PgvectorStore` adapter (upsert/query/count) over psycopg+pgvector, raising `StoreError`.
      depends_on: T1
      refs: R6, R7, R10, R11

- [x] T6: Implement `src/coderag/llm/ollama_embedder.py` — `OllamaEmbedder` implementing `Embedder`, raising `EmbedderError`.
      depends_on: T1
      refs: R6, R10, R11

- [x] T7: Wire `ingest` and `query` commands in `src/coderag/cli.py` using `Settings`, `PgvectorStore`, `OllamaEmbedder`, and `run_ingest`.
      depends_on: T4, T5, T6
      refs: R6, R8, R9

- [x] T8: Write deterministic unit tests (`tests/test_ingest.py`) with fake `Embedder`/`VectorStore`: extension filter, gitignore skip, fixed chunking line spans + hash, pipeline end-to-end, error isolation.
      depends_on: T2, T3, T4
      refs: R1, R2, R3, R4, R5, R6, R10, R11

- [x] T9: Write integration test `tests/test_pgvector.py` (skipped without a live DB) covering upsert/query/count and top-k ordering.
      depends_on: T5
      refs: R7, R8, R9

- [x] T10: Run quality gates (ruff, black, mypy --strict, pytest) and update `harness/progress/current.md`.
      depends_on: T7, T8, T9
      refs: R9, R12
