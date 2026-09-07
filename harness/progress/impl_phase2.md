# Implementation progress — phase2-eval-harness

## Traceability

| Requirement | Test(s) | Implementation file(s) | Status |
|-------------|---------|------------------------|--------|
| R1 | test_eval.py::test_load_golden_from_yaml, ::test_load_golden_missing_field | evals/dataset.py, evals/golden/codebaserag.yaml | done |
| R2 | (45 entries in golden yaml; test_load_golden_from_yaml) | evals/golden/codebaserag.yaml | done |
| R3 | test_eval.py::test_run_retrieval_eval_perfect | evals/harness.py | done |
| R4 | test_eval.py::test_run_retrieval_eval_perfect (retrieved_files asserted) | evals/harness.py | done |
| R5 | test_metrics.py::test_recall_at_k_* | evals/metrics.py | done |
| R6 | test_metrics.py::test_reciprocal_rank_* | evals/metrics.py | done |
| R7 | test_metrics.py::test_ndcg_* | evals/metrics.py | done |
| R8 | test_metrics.py (no I/O), test_eval (no services) | evals/metrics.py | done |
| R9 | test_eval.py::test_run_retrieval_eval_perfect, cli `eval` + `to_markdown` | evals/harness.py, src/coderag/cli.py | done |
| R10 | test_eval.py::test_regression_guard_* | evals/harness.py | done |
| R11 | test_eval.py (in-memory, CI-safe), cli `eval --store memory` | src/coderag/stores/memory.py, evals/embedder.py, src/coderag/cli.py | done |
| R12 | test_metrics.py + test_eval.py run with no external services | evals/metrics.py, evals/harness.py | done |
| R13 | README.md metrics table + CLI `--update-baseline` | README.md, evals/harness.py | done |

## Notes
- The `InMemoryVectorStore` (cosine) and `HashEmbedder` (deterministic token-hash) let the full
  retrieval eval run in CI with **no pgvector/Ollama** — satisfying the "deterministic, no network"
  requirement. The `HashEmbedder` is a semantic placeholder: real recall numbers require Ollama.
- Baseline (`evals/baseline.json`) is intentionally **not** written yet — it should be set with a
  real embedder via `uv run python -m coderag.cli eval --store pgvector --update-baseline`. The
  README table therefore shows `—` until then. The regression guard (`assert_not_regressed`) is
  implemented and unit-tested (passes with `--adr-override`, fails otherwise).
- Smoke run `eval --store memory --repo .` produced a valid report (recall ≈ 0.02 with the naive
  embedder) — confirms the harness and CLI path work end-to-end.
- Wekan mirror: F2 card `dQEx9MwvqqDxDLSty` moved to `in_progress` and commented.
