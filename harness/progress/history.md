# Historical log (append-only)

> Each time a session closes, its summary is appended here.
> Do not edit previous entries. Only append.

---

## Session 2026-09-07 — codebaserag F0→F7 (ALL COMPLETE)

Built the full hexagonal RAG-over-own-codebase system, phase by phase, via the harness SDD flow.
Each feature drafted as requirements/design/tasks, approved by human, implemented, gates green,
Wekan card moved to `done`.

- **F0 setup**: `docs/`, `pyproject`, `src/coderag` skeleton, ports (`VectorStore`/`Embedder`/
  `LlmClient`/`Reranker`), `types`, CLI stub, CI.
- **F1 ingest+pgvector**: readers (gitignore via pathspec), chunkers, `run_ingest`,
  `PgvectorStore`, `OllamaEmbedder`, CLI ingest/query.
- **F2 eval-harness**: golden dataset (45), metrics (recall@k/MRR/nDCG), `run_retrieval_eval`,
  `HashEmbedder`+`InMemoryVectorStore` (offline), CLI eval, baseline regression guard.
- **F3 hybrid-rerank**: `reciprocal_rank_fusion` (RRF k=60), `InMemoryBm25`/`TantivyBm25`/
  `PostgresFtsBm25`, `CrossEncoderReranker` (fallback), `Retriever` (dense/hybrid/hybrid+rerank),
  experiment table runner.
- **F4 structured-generation**: `LlmClient.generate_structured`, `LitellmClient`, `FakeLlmClient`,
  `Generator` (grounded citations + confidence), `Answer.payload`, generation eval rates.
- **F5 observability**: `Tracer` port + `Span`, `InMemoryTracer`/`NoOpTracer`/`LangfuseTracer`,
  instrumented retriever/generator (non-blocking), `build_tracer`.
- **F6 qdrant-adapter**: `QdrantVectorStore` (lazy SDK, payload store, `StoreError`), shared
  `stores/errors.py`, `store="qdrant"` backend, tests skip without SDK.
- **F7 api-compose**: `compose.py` (shared build helpers), `api/models.py` + `api/app.py`
  (`POST /ingest` `/query` `/answer`, exception handlers, R8 contract = /query == core Retriever),
  `serve` CLI, README endpoints.

**Final gates:** ruff clean, black clean, mypy --strict clean, pytest **65 passed / 5 skipped**
(3 pgvector + 1 litellm + 1 qdrant). `harness/init.sh` OK.

**Wekan:** board `codebaserag` (5MXpMcrtfF4BWQy9c); all 8 feature cards in `done`.

**Open follow-ups (not in approved specs):** real `evals/baseline.json` (needs Ollama), docker-compose
stack, ADRs for hybrid/structured/Qdrant decisions.
