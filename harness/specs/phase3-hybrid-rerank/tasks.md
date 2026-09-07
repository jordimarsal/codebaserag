# Tasks: phase3-hybrid-rerank

- [x] T1: Create `src/coderag/retrieval/bm25.py` — `Bm25Index` protocol + `TantivyBm25` and `PostgresFtsBm25` adapters (selectable backend).
      depends_on: (none)
      refs: R1, R6, R7

- [x] T2: Create `src/coderag/retrieval/fusion.py` — pure `reciprocal_rank_fusion` (RRF, k=60) and BM25 scoring helpers.
      depends_on: (none)
      refs: R2, R3, R12

- [x] T3: Create `src/coderag/retrieval/reranker.py` — `CrossEncoderReranker` implementing the `Reranker` port (sentence-transformers), with unavailable-model fallback (R11).
      depends_on: (none)
      refs: R5, R6, R11

- [x] T4: Create `src/coderag/retrieval/retriever.py` — `Retriever` orchestrator (dense | hybrid | hybrid+rerank), injecting `VectorStore`, `Bm25Index`, optional `Reranker`.
      depends_on: T1, T2, T3
      refs: R2, R4, R6, R8, R11

- [x] T5: Extend `src/coderag/config.py` with `retrieval_strategy`, `rerank_model`, `rerank_top_n`, `bm25_backend`; expose in CLI `query`/`eval` (e.g. `--strategy`).
      depends_on: T4
      refs: R4, R8

- [x] T6: Update `evals/harness.py` `run_retrieval_eval` to accept a `retriever` callable so the golden set runs under each strategy.
      depends_on: T4
      refs: R9, R10

- [x] T7: Add `evals/experiments/hybrid_vs_dense.md` report template; emit dense vs hybrid vs hybrid+rerank table (recall@5, MRR, nDCG).
      depends_on: T6
      refs: R9, R10

- [x] T8: Write `tests/test_fusion.py` — pure-function tests for RRF fusion and BM25 scoring edge cases.
      depends_on: T2
      refs: R2, R3, R12

- [x] T9: Write `tests/test_retriever.py` — orchestration test with fake dense store + fake BM25 index across dense/hybrid/hybrid+rerank; verify reranker fallback (R11).
      depends_on: T4, T8
      refs: R4, R6, R9, R11

- [x] T10: Run quality gates (ruff, black, mypy --strict, pytest) and update `harness/progress/current.md`.
      depends_on: T5, T7, T8, T9
      refs: R10, R12
