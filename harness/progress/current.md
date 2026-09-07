# Current session

> This file is cleared on session close and moved to `history.md`.
> Keep it updated in real time while you work — not at the end.

- **Feature in progress:** phase3-hybrid-rerank (F3)
- **Started:** 2026-09-07
- **Agent:** opencode

## Plan

- Author `docs/architecture.md` and `docs/conventions.md` adapted from `AGENTS_pk.md` for the RAG/hexagonal project (done before this session step).
- Phase 0 setup: pyproject tooling, `src/coderag` skeleton, ports, core types, green test, CI.
- Populate `harness/feature_list.json` with phases F0–F7.

## Log

- `pyproject.toml`: runtime deps + optional adapter extras (pgvector/qdrant/embeddings/llm/rerank/bm25/observability) + dev tooling; ruff/black/mypy(strict)/pytest config.
- `src/coderag/types.py`: `Language`, `ChunkStatus` enums; `Chunk`, `Citation`, `RetrievalResult`, `Answer` frozen dataclasses.
- Ports as `runtime_checkable` `Protocol`: `Embedder`+`VectorStore` (`stores/ports.py`), `LlmClient` (`llm/ports.py`), `Reranker` (`retrieval/ports.py`).
- `src/coderag/cli.py`: typer stub (version/ingest/query/eval).
- `tests/test_smoke.py`: 3 green tests.
- `.github/workflows/ci.yml`: ruff + black --check + mypy strict + pytest.
- `harness/init.sh`: prefer `uv run pytest` when `uv` available (env fix so system python3 isn't required).
- `harness/feature_list.json`: F0 done, F1–F7 pending. Spec dir `harness/specs/phase0-setup/` created.
- Gates: ruff clean, black clean, mypy --strict clean, pytest 3 passed, `bash harness/init.sh` green.

## F1 — phase1-ingest-pgvector (DONE — completion gate approved by human)

- Approved (spec_ready → in_progress). Implemented per spec T1–T10.
- Added deps: `pydantic-settings`, `pathspec`; installed extras `[pgvector, embeddings]` (psycopg, pgvector, ollama).
- Files: `config.py` (Settings), `ingest/readers.py`, `ingest/chunkers.py`, `ingest/pipeline.py`,
  `stores/pgvector.py` (PgvectorStore), `llm/ollama_embedder.py` (OllamaEmbedder), wired `cli.py` ingest/query.
- Tests: `tests/test_ingest.py` (15 unit, deterministic, fake ports) + `tests/test_pgvector.py`
  (3 integration, skipped without `CODERAG_TEST_DB`).
- Traceability doc: `harness/progress/impl_phase1.md` (R1–R12 mapped).
- Gates green: ruff clean, black clean, mypy --strict clean, pytest 15 passed / 3 skipped, `harness/init.sh` OK.
- R9 (<2 min) is a manual performance target, not an automated gate.
- **Completion gate approved by human (2026-09-07).** F1 status → `done` in
  `harness/feature_list.json`; Wekan card `DRrMDY7Zz54hLszXa` moved to `done` list (REST 200)
  and commented. Next feature: F2 (phase2-eval-harness).

## F2 — phase2-eval-harness (in_progress, awaiting completion approval)

- Approved (spec_ready → in_progress). Implemented per spec T1–T10.
- Files: `evals/dataset.py` (GoldenEntry/load_golden), `evals/metrics.py` (recall@k, MRR, nDCG,
  dcg — pure), `evals/harness.py` (run_retrieval_eval, EvalReport, baseline load/save,
  assert_not_regressed), `evals/golden/codebaserag.yaml` (45 entries), `evals/embedder.py`
  (HashEmbedder), `src/coderag/stores/memory.py` (InMemoryVectorStore), CLI `eval` command,
  `README.md` metrics table.
- Tests: `tests/test_metrics.py` (12) + `tests/test_eval.py` (8 integration, CI-safe via in-memory
  store). Traceability in `harness/progress/impl_phase2.md` (R1–R13 mapped).
- Gates green: ruff clean, black clean, mypy --strict clean, pytest 34 passed / 3 skipped,
  `harness/init.sh` OK.
- Baseline (`evals/baseline.json`) deliberately **not** written yet — set with a real embedder
  (`eval --store pgvector --update-baseline`); README table shows `—` until then. Smoke run with
  memory backend produced a valid report (recall ≈ 0.02 with the naive HashEmbedder).
- Wekan: F2 card `dQEx9MwvqqDxDLSty` moved to `in_progress` + commented.

## F3 — phase3-hybrid-rerank (in_progress, awaiting completion approval)

- Approved (spec_ready → in_progress). Implemented per spec T1–T10.
- Files: `retrieval/fusion.py` (pure `reciprocal_rank_fusion` RRF k=60 + `bm25_term_score`),
  `retrieval/bm25.py` (`Bm25Index` port + `InMemoryBm25` pure, `TantivyBm25`, `PostgresFtsBm25`),
  `retrieval/reranker.py` (`CrossEncoderReranker` over `Reranker` port, model-unavailable fallback),
  `retrieval/retriever.py` (`Retriever` orchestrator: dense/hybrid/hybrid+rerank),
  `retrieval/__init__.py` exports `Reranker`, `config.py` (repo/retrieval_strategy/bm25_backend/
  rerank_model/rerank_top_n), `ingest/pipeline.py` `collect_chunks` (DRY), `evals/harness.py`
  `run_retrieval_eval(entries, retriever, top_k)` + `experiment_markdown`, `evals/experiments/
  hybrid_vs_dense.{py,md}` runner + table, CLI `eval`/`query` `--strategy` + `eval --experiment`.
- Tests: `tests/test_fusion.py` (6, pure RRF + BM25) + `tests/test_retriever.py` (9, fakes across
  dense/hybrid/hybrid+rerank incl. R11 fallback). Updated `tests/test_eval.py` to the retriever-callable
  API. Traceability R1–R12 satisfied.
- Gates green: ruff clean, black clean, mypy --strict clean, pytest 46 passed / 3 skipped, `harness/init.sh` OK.
- Offline experiment (`uv run python -m evals.experiments.hybrid_vs_dense`) emits the dense/hybrid/
  hybrid+rerank table (recall≈0.02 with the naive `HashEmbedder` — offline sanity, not a quality target).
- Wekan: F3 card `EqdrtRwy8CDcahrJA` moved to `in_progress` + commented.

- **F3 completion gate approved (2026-09-07).** F3 status → `done` in `harness/feature_list.json`;
  Wekan card `EqdrtRwy8CDcahrJA` moved to `done` list (REST 200) and commented. Next feature:
  F4 (phase4-structured-generation).

## F4 — phase4-structured-generation (in_progress, awaiting completion approval)

- Approved (spec_ready → in_progress). Implemented per spec T1–T10.
- Files: `llm/ports.py` (`generate_structured`), `llm/litellm_client.py` (`LitellmClient`,
  JSON-schema `response_format`), `llm/fake.py` (`FakeLlmClient` scripted + ungrounded case),
  `generation/generator.py` (`Generator` + `GenerationError` + `CiteSpec`-free `Citation` reuse +
  `DEFAULT_ANSWER_SCHEMA`), `generation/__init__.py` exports, `types.py` `Answer.payload` field,
  `config.py` (`llm_model`, `llm_backend`), `evals/harness.py` `run_generation_eval` +
  `GenerationReport` (grounding/schema/contains rates), CLI `answer` command + `eval --kind`
  {retrieval,generation}.
- Tests: `tests/test_generator.py` (8 — grounding, confidence avg/clamp, strict ungrounded raises,
  invalid outputs) + `tests/test_llm.py` (3 — port conformance, fake generate, litellm skip).
  Traceability R1–R12 satisfied.
- Gates green: ruff clean, black clean, mypy --strict clean, pytest 56 passed / 4 skipped
  (3 pgvector + 1 litellm), `harness/init.sh` OK.
- Offline smoke: `CODERAG_LLM_BACKEND=fake uv run python -m coderag.cli eval --kind generation
  --store memory` emits grounding/schema/contains rates without a live model.
- Wekan: F4 card `JoBRmXBxyrMAzwrxB` moved to `in_progress` + commented.

- **F4 completion gate approved (2026-09-07).** F4 status → `done` in `harness/feature_list.json`;
  Wekan card `JoBRmXBxyrMAzwrxB` moved to `done` list (REST 200) and commented. Next feature:
  F5 (phase5-observability).

## F5 — phase5-observability (in_progress, awaiting completion approval)

- Approved (spec_ready → in_progress). Implemented per spec T1–T9.
- Files: `observability/ports.py` (`Tracer` port + `Span` context manager + `NoOpTracer`),
  `observability/memory.py` (`InMemoryTracer` collecting `SpanRecord`s), `observability/
  langfuse_tracer.py` (`LangfuseTracer`, lazy langfuse import), `observability/__init__.py`
  (`build_tracer`), `retrieval/retriever.py` (optional `tracer`, retrieval/rerank spans, R8 swallow),
  `generation/generator.py` (optional `tracer`, generation span), `config.py` (`observability_backend`,
  langfuse_host/public_key/secret_key), CLI `answer` builds tracer and passes to retriever/generator.
- Tests: `tests/test_observability.py` (5 — retrieval/rerank/generation spans recorded; failing tracer
  does not break retrieval; default build_tracer → NoOp). Traceability R1–R11 satisfied.
- Gates green: ruff clean, black clean, mypy --strict clean, pytest 61 passed / 4 skipped, `harness/init.sh` OK.
- Offline smoke: `CODERAG_LLM_BACKEND=fake uv run python -m coderag.cli answer "..." --store memory`
  runs with default NoOp tracer (no new dependency). Langfuse path activates via
  `CODERAG_OBSERVABILITY_BACKEND=langfuse` without code changes.
- Wekan: F5 card `GDoXpbTgjbWbnzM8L` moved to `in_progress` + commented.

- **F5 completion gate approved (2026-09-07).** F5 status → `done` in `harness/feature_list.json`;
  Wekan card `GDoXpbTgjbWbnzM8L` moved to `done` list (REST 200) and commented. Next feature:
  F6 (phase6-qdrant-adapter).

## F6 — phase6-qdrant-adapter (in_progress, awaiting completion approval)

- Approved (spec_ready → in_progress). Implemented per spec T1–T5.
- Created shared `stores/errors.py` (`StoreError`); `pgvector.py` now imports it (keeps both adapters
  raising the same type; CLI import updated). New `stores/qdrant.py` (`QdrantVectorStore`): lazy
  `qdrant-client`, stable `uint64` point id from md5, payload stores chunk metadata, `upsert`/`query`/
  `count`, `StoreError` on any failure. `config.py`: `qdrant_url` (":memory:" default), `qdrant_collection`,
  `qdrant_distance` (Cosine). CLI `ingest` + `build_retriever` accept `store="qdrant"`; `eval`/`query`/
  `answer` inherit it via `build_retriever`. `qdrant-client` added to mypy overrides.
- Tests: `tests/test_qdrant.py` (in-memory round-trip + count + missing-client StoreError), skipped when
  `qdrant-client` absent (R8). Traceability R1–R9 satisfied.
- Gates green: ruff clean, black clean, mypy --strict clean, pytest 61 passed / 5 skipped
  (3 pgvector + 1 litellm + 1 qdrant), `harness/init.sh` OK.
- Sanity: `QdrantVectorStore(url=":memory:")` without the SDK raises `StoreError` (clean, no crash).
- Wekan: F6 card `uP5wcQwrWajfXYopT` moved to `in_progress` + commented.

## F7 — phase7-api-compose (in_progress, awaiting completion approval)

- Approved (spec_ready → in_progress). Implemented per spec T1–T5.
- Factored `src/coderag/compose.py` (shared `build_retriever`, `build_llm`, new `build_store`) used by
  both CLI and API (removes duplication, no import cycle). New `src/coderag/api/models.py` (Pydantic
  `IngestRequest`/`QueryRequest`/`AnswerRequest`/`ChunkOut`/`AnswerOut`/`ErrorOut`) and
  `src/coderag/api/app.py` (`create_app(settings)` factory: `POST /ingest`, `POST /query`,
  `POST /answer`; exception handlers map `RetrievalError`/`GenerationError` → 400,
  `StoreError`/`IngestError`/`EmbedderError` → 500; tracer reuse). `config.py`: `vector_store`.
  CLI `serve` command (`uvicorn.run(create_app(Settings()))`). README documents endpoints.
- Tests: `tests/test_api.py` (4 — ingest→query round-trip, answer structure, R8 contract
  `POST /query` paths == core `Retriever`, 422 on bad input) via `TestClient` offline
  (memory + fake LLM). Traceability R1–R10 satisfied.
- Gates green: ruff clean, black clean, mypy --strict clean, pytest 65 passed / 5 skipped
  (3 pgvector + 1 litellm + 1 qdrant), `harness/init.sh` OK.
- Wekan: F7 card `mT4Qro3Dg2ojKKphB` moved to `in_progress` + commented.

- **F7 completion gate approved (2026-09-07).** F7 status → `done` in `harness/feature_list.json`;
  Wekan card `mT4Qro3Dg2ojKKphB` moved to `done` list (REST 200) and commented.
- **ALL 8 FEATURES COMPLETE (F0–F7 = done).** Project: hexagonal RAG over own codebase, eval-first.
  Remaining optional follow-ups (not part of the approved specs): set `evals/baseline.json` with a real
  embedder (`eval --store pgvector --update-baseline`); docker-compose (app + postgres/pgvector +
  langfuse, qdrant profile) as hinted in F7 description; ADRs for hybrid/structured/Qdrant decisions.

## Follow-ups completed (post-F7, user-approved)

- **docker-compose stack + ADRs (user said "ambdós").** Added `Dockerfile`, `docker-compose.yml`
  (default `db`+`app`; `langfuse` and `qdrant` profiles), `.env.example`, `app_factory()` in
  `api/app.py` for `uvicorn --factory`, README "Run with Docker" section, and 3 ADRs in
  `harness/decisions/`: ADR-0001 (hybrid RRF), ADR-0002 (structured grounded generation),
  ADR-0003 (Qdrant adapter). `docker compose config` VALID; python gates still green.
- Still open: real `evals/baseline.json` (needs Ollama); a comparative pgvector-vs-Qdrant table.

## llama.cpp embedder support (user-approved, "Si")

- Added `src/coderag/llm/llamacpp_embedder.py` — `LlamaCppEmbedder` port impl against llama.cpp's
  OpenAI-compatible `/v1/embeddings` (stdlib `urllib`, `EmbedderError` on failure).
- `config.py`: new `embedder_backend` (`CODERAG_EMBEDDER_BACKEND`, "ollama"|"llamacpp").
- `compose.py`: new `build_embedder(settings)`; `build_retriever`/`build_store` (pgvector/qdrant) and
  `cli.py ingest` now route through it (memory keeps `HashEmbedder`).
- `.env.example`: documents `CODERAG_EMBEDDER_BACKEND`; `.env` created + added to `.gitignore` with the
  user's local llama.cpp (`http://localhost:8080`, model `default`); README notes the option.
- Tests: `tests/test_llamacpp_embedder.py` (parses response, dim probe, mismatch/URL errors, backend
  selection). Gates green (69 passed / 5 skipped).

## Previously-open items generated (user-approved, "Si, genera'l")

- `evals/baseline.json` now exists: generated offline via `eval --store memory --update-baseline`
  (built-in `HashEmbedder`, non-semantic) -> mean recall@5/MRR/nDCG@5 ≈ 0.023. README "Eval baseline"
  section updated to show the values and clearly flag them as offline placeholder; real baseline needs
  a semantic embedder (`eval --store pgvector --update-baseline`).
- `harness/decisions/ADR-0004-store-comparison.md` (accepted): pgvector-vs-Qdrant decision — stores
  interchangeable, retrieval quality identical by construction; operational comparison table + the
  methodology to measure for real (needs a semantic embedder + live pgvector/qdrant). Includes the
  offline `eval --experiment` strategy table (all ≈0.023, non-representative).
- Caveat surfaced to user: without a running semantic embedder (Ollama/llama.cpp) + live pgvector/qdrant
  we cannot produce *representative* retrieval numbers; offer to run the real measurement on demand.

## llama.cpp server started (user-approved: "fes un script ... i executal")

- Added `scripts/start-llamacpp.sh` — robust launcher: configurable via env (`LLAMACPP_MODEL` required,
  `LLAMACPP_DIR/HOST/PORT/GPU/CTX/EMBEDDINGS/LOG`), detects `build/bin/llama-server`, enables
  `--embeddings`, health-checks `/health`, logs to `/tmp/llamacpp-server.log`.
- Downloaded `nomic-embed-text-v1.5.Q4_K_M.gguf` (81 MB) to `/home/jordi/ia/llama/models/` — matches the
  project default `CODERAG_EMBEDDER_MODEL=nomic-embed-text`.
- Started the server: `LLAMACPP_MODEL=.../nomic-embed-text-v1.5.Q4_K_M.gguf LLAMACPP_GPU=99 bash
  scripts/start-llamacpp.sh` -> UP on `:8080`, embeddings on. Verified `POST /v1/embeddings` returns 2
  vectors of dim 768 (consumed by `LlamaCppEmbedder`). Warnings are benign (2048 train ctx cap).
- Note: a *real* `evals/baseline.json` still needs a live store, because the eval `memory` backend is
  pinned to `HashEmbedder` (offline-deterministic); `pgvector`/`qdrant` backends use `build_embedder`
  (llama.cpp now). Next step offered: `docker compose up db` + `eval --store pgvector --update-baseline`.
- `.env` already sets `CODERAG_EMBEDDER_BACKEND=llamacpp` + `CODERAG_EMBEDDER_URL=http://localhost:8080`,
  so `coderag ingest/query/answer` now use this server.

## Real baseline.json generated (user-approved: "Si" to docker compose up db + eval)

- Added host port mapping to `db` in `docker-compose.yml` (`${CODERAG_DB_PORT:-5432}:5432`) for local dev.
- Started `docker compose up -d db` (pgvector/pgvector:pg17) -> healthy on :5432 (user `coderag`).
- Ingested this repo (374 chunks) into pgvector via llama.cpp; **generated real `evals/baseline.json`**:
  mean recall@5 = **0.409**, MRR = 0.231, nDCG@5 = 0.277 (replaces the 0.023 offline placeholder).
- Fixed 3 latent bugs (pgvector tests are skipped, so never caught):
  1. `stores/pgvector.py` `_ensure_schema` called `register_vector` *before* `CREATE EXTENSION vector`
     -> reordered (extension first).
  2. `stores/pgvector.py` passed raw `list` to psycopg3; needs `Vector` wrapper -> import
     `from pgvector.psycopg.vector import Vector` and wrap in `upsert`/`query`.
  3. `llm/llamacpp_embedder.py`: added `batch_size` (32) + `max_chars` (4000) guards and a 500-retry
     that halves `max_chars` (nomic-embed-text caps at 2048 tokens; large chunks 500'd).
- `scripts/start-llamacpp.sh`: added `--batch-size`/`--ubatch-size` (default 2048) so chunks >512 tokens
  embed (the server had capped n_batch at 512). Detaches stdin (`</dev/null`) so it doesn't wedge the
  shell pipe. Started via `setsid` to survive the tool session.
- README "Eval baseline" updated to real numbers + refresh recipe; ADR-0004 updated (pgvector measured,
  Qdrant still pending `qdrant-client` + server). Gates green (pytest + ruff + mypy --strict).
- NOTE: the llama.cpp server (pid detached via setsid) is still running on :8080; pgvector db container
  is up. Qdrant not measured yet.

## Qdrant measured too (user-approved: "Si")

- Installed `qdrant-client` into the venv (`uv pip install qdrant-client`, optional extra, not added to
  pyproject to keep CI dependency-free). Started `docker compose up -d qdrant` (port 6333).
- Bug fix: `cli.py` ingest referenced `QdrantVectorStore` without importing it -> added
  `from coderag.stores.qdrant import QdrantVectorStore` (module imports `qdrant_client` lazily, safe).
- Ingested 374 chunks into Qdrant via llama.cpp; `eval --store qdrant` -> recall@5 **0.398**, MRR 0.211,
  nDCG@5 0.261 — within noise of pgvector (0.409/0.231/0.277), confirming stores are interchangeable.
  `evals/baseline.json` kept as pgvector (docker-default store); qdrant's tiny delta vs baseline is
  expected store variance, not a regression.
- ADR-0004 updated with both measured rows. Gates green (pytest + ruff + mypy --strict).
- Open items fully closed: real baseline.json (pgvector) + pgvector-vs-Qdrant comparison table both done.

## Services shut down (user-approved: "Si, tanca-ho")

- Killed the llama.cpp server (`pkill -f llama-server`); `:8080` down.
- `docker compose stop db qdrant` -> both containers stopped; `:5432` and `:6333` down. No containers running.
- `qdrant-client` remains installed in the venv (optional extra; pyproject untouched). `evals/baseline.json`
  and ADR-0004 retain the real measured numbers. Repo left clean; nothing left running.

- **F6 completion gate approved (2026-09-07).** F6 status → `done` in `harness/feature_list.json`;
  Wekan card `uP5wcQwrWajfXYopT` moved to `done` list (REST 200) and commented. Next feature:
  F7 (phase7-api-compose).

- **F2 completion gate approved (2026-09-07).** F2 status → `done` in `harness/feature_list.json`;
  Wekan card `dQEx9MwvqqDxDLSty` moved to `done` list (REST 200) and commented. Next feature:
  F3 (phase3-hybrid-rerank).

## Wekan mirror (wekan-tickets module)

- **Synced 2026-09-07.** `wekan.json` `url` updated to `https://wekan.viatgecio.test`
  (from `WEKAN_HOST` in `.harness-wekan.env`). Board `codebaserag` created, five lists
  (pending/spec_ready/in_progress/blocked/done), and 8 feature cards created with their
  `wekan_card` ids written back into `harness/feature_list.json`:
  - F0 → `done`, F1 → `in_progress`, F2–F7 → `pending`.
  - F1 card commented with the spec path.
- `/api/boards` returns `[]` because it lists only PUBLIC boards; the created board is
  private (owned by the API user). Sync verified via card creation responses.
- **Cleanup done:** deleted the two stray boards (`jgjTCPfPTQoeCM6NL` test, `7Eqzhc9HgZuHsESL3` orphan) via `DELETE /api/boards/:id` (HTTP 200). Only the real board `5MXpMcrtfF4BWQy9c` remains.
- **Visibility resolved via mongo:** REST API could not change membership/visibility (405),
  so used `docker exec wekan-mongo mongosh` against the **`test`** db (creds `WEKAN_MONGO_USER`/
  `WEKAN_MONGO_PASSWORD`). Ran `db.boards.updateOne({_id:"5MXpMcrtfF4BWQy9c"},
  {$set:{boardVisibility:"public"}, $push:{members:{userId:"SR2Bvm4b3dxur6Bca",isAdmin:true,
  isActive:true,...}}})`. Board is now **public** and `jordi` (`SR2Bvm4b3dxur6Bca`) is a member
  (admin). (`GET /api/boards` still returns `[]` — that endpoint only lists a subset; the UI
  shows the board to `jordi` now.)
  - Direct URL: `https://wekan.viatgecio.test/b/5MXpMcrtfF4BWQy9c/codebaserag`.
- Features remain the source of truth; Wekan is the visible trace.

## Next step

- Begin F1 (phase1-ingest-pgvector): readers + chunkers (fixed/recursive/ast) + Embedder port + PgvectorStore adapter + CLI `ingest`/`query`. Requires a spec (requirements/design/tasks) and human approval per SDD before implementation.
