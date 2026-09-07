# Tasks: phase2-eval-harness

- [x] T1: Create `evals/dataset.py` — `GoldenEntry` dataclass and `load_golden(directory)` YAML loader.
      depends_on: (none)
      refs: R1, R2

- [x] T2: Create `evals/metrics.py` — pure functions `recall_at_k`, `reciprocal_rank`, `ndcg_at_k`, `dcg`.
      depends_on: (none)
      refs: R5, R6, R7, R8, R12

- [x] T3: Create `evals/golden/codebaserag.yaml` with ≥40 golden entries (`question`, `expected_files`, `answer_contains`, `repo`).
      depends_on: T1
      refs: R1, R2

- [x] T4: Create `evals/harness.py` — `run_retrieval_eval`, `EvalReport`, `EntryResult`, `load_baseline`, `save_baseline`, `assert_not_regressed`.
      depends_on: T1, T2
      refs: R3, R4, R5, R6, R7, R9, R10

- [x] T5: Add an in-memory `VectorStore` + deterministic local embedder for CI (no DB/network), used by the eval integration test.
      depends_on: (none)
      refs: R11, R12

- [x] T6: Wire the `eval` command in `src/coderag/cli.py` — run retrieval eval, print/save the markdown report, support `--update-baseline` and `--adr-override`.
      depends_on: T4
      refs: R9, R10, R11

- [x] T7: Document the baseline metrics table in `README.md` (current vs baseline).
      depends_on: T4
      refs: R13

- [x] T8: Write `tests/test_metrics.py` (pure-function unit tests, no services) covering recall@k, MRR, nDCG edge cases.
      depends_on: T2
      refs: R5, R6, R7, R8, R12

- [x] T9: Write `tests/test_eval.py` — integration eval over the in-memory store (CI-safe), asserting report structure and regression guard.
      depends_on: T4, T5
      refs: R3, R4, R9, R10, R11

- [x] T10: Run quality gates (ruff, black, mypy --strict, pytest) and update `harness/progress/current.md`.
      depends_on: T6, T7, T8, T9
      refs: R11, R13
