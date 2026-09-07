# Implementation progress — phase1-ingest-pgvector

## Traceability

| Requirement | Test(s) | Implementation file(s) | Status |
|-------------|---------|------------------------|--------|
| R1 | test_discover_files_filters_by_extension | src/coderag/ingest/readers.py | done |
| R2 | test_discover_files_skips_gitignore_and_git_dir, test_is_ignored_direct | src/coderag/ingest/readers.py | done |
| R3 | test_language_for_maps_extensions | src/coderag/ingest/readers.py | done |
| R4 | test_chunk_fixed_line_spans_and_hash, test_chunk_fixed_empty_file | src/coderag/ingest/chunkers.py | done |
| R5 | test_chunk_fixed_line_spans_and_hash | src/coderag/ingest/chunkers.py | done |
| R6 | test_pipeline_end_to_end | src/coderag/ingest/pipeline.py | done |
| R7 | test_upsert_query_count_and_ordering, test_query_returns_empty_for_no_match | src/coderag/stores/pgvector.py | done |
| R8 | test_upsert_query_count_and_ordering (store.query); CLI `query` (manual) | src/coderag/stores/pgvector.py, src/coderag/cli.py | done |
| R9 | (performance; manual over a real repo) | src/coderag/ingest/pipeline.py | done* |
| R10 | test_ports_are_runtime_checkable; core imports only ports | src/coderag/ingest/*, src/coderag/stores/ports.py | done |
| R11 | test_pipeline_skips_binary_file, test_pipeline_raises_on_embedding_error, test_store_error_on_bad_dsn | src/coderag/ingest/pipeline.py, src/coderag/stores/pgvector.py | done |
| R12 | test_settings_reads_env_with_prefix | src/coderag/config.py | done |

\* R9 is a performance target validated manually (index a real repo in < 2 min); no
automated timing gate is enforced.

## Notes
- Core (`ingest`, `stores/ports`, `llm/ports`) imports no adapter SDK; only `stores/pgvector.py`
  and `llm/ollama_embedder.py` touch psycopg/ollama. This satisfies the hexagonal boundary (R10).
- `tests/test_pgvector.py` is skipped unless `CODERAG_TEST_DB` points to a live pgvector DB,
  so CI stays green without a database.
- Wekan mirror was NOT synced: `harness/wekan.json` is a placeholder and `.harness-wekan.env`
  is absent (see `harness/progress/current.md`).
