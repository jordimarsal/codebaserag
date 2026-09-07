# Tasks: phase6-qdrant-adapter

- [x] T1: Create `src/coderag/stores/qdrant.py` — `QdrantVectorStore` implementing `VectorStore`
      (lazy `qdrant-client` import, `StoreError` on failure, stable point ids, payload with chunk
      metadata).
      depends_on: (none)
      refs: R1, R2, R5, R6, R7

- [x] T2: Add `qdrant_url`, `qdrant_collection`, `qdrant_distance` to `src/coderag/config.py`.
      depends_on: (none)
      refs: R3, R4

- [x] T3: Wire `store="qdrant"` into `src/coderag/cli.py` (`build_retriever`, `ingest`, `query`,
      `eval`) building a `QdrantVectorStore` from `Settings`.
      depends_on: T1, T2
      refs: R9

- [x] T4: Add `qdrant-client` to mypy overrides (`ignore_missing_imports`).
      depends_on: T1
      refs: R2

- [x] T5: Write `tests/test_qdrant.py` — in-memory Qdrant round-trip (upsert + query reconstructs
      chunks, scores present); skip when `qdrant-client` absent. Run gates; update
      `harness/progress/current.md`.
      depends_on: T1, T2
      refs: R6, R8
