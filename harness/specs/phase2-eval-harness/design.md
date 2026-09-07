# Design: phase2-eval-harness

## Files to create or modify

- `evals/golden/codebaserag.yaml` (and additional repo files) — ≥40 golden entries:
  `question`, `expected_files`, `answer_contains`, `repo`.
- `evals/dataset.py` — `GoldenEntry` dataclass + `load_golden(directory)` loader.
- `evals/metrics.py` — pure functions `recall_at_k`, `reciprocal_rank`, `ndcg_at_k`, `dcg`.
- `evals/harness.py` — `run_retrieval_eval(entries, embedder, store, *, top_k)`, `EvalReport`,
  `EntryResult`, `load_baseline`, `save_baseline`, `assert_not_regressed`.
- `evals/baseline.json` — stored baseline metrics (created on first run / `--update-baseline`).
- `src/coderag/cli.py` — implement `eval` command (was a stub) to run the retrieval eval.
- `README.md` — metrics table (current vs baseline).
- `tests/test_metrics.py` — deterministic unit tests for the pure metric functions.
- `tests/test_eval.py` — integration test using an in-memory `VectorStore` (no DB/network),
  gated so it can run in CI without external services.

## Public signatures

```python
# dataset.py
@dataclass(frozen=True)
class GoldenEntry:
    question: str
    expected_files: tuple[str, ...]
    answer_contains: tuple[str, ...]
    repo: str

def load_golden(directory: Path) -> list[GoldenEntry]: ...

# metrics.py
def recall_at_k(retrieved: list[str], relevant: set[str], k: int) -> float
def reciprocal_rank(retrieved: list[str], relevant: set[str]) -> float
def ndcg_at_k(retrieved: list[str], relevant: set[str], k: int) -> float
def dcg(gains: list[float]) -> float

# harness.py
@dataclass
class EntryResult:
    entry: GoldenEntry
    retrieved_files: list[str]
    recall: float
    mrr: float
    ndcg: float

@dataclass
class EvalReport:
    entries: list[EntryResult]
    mean_recall: float
    mean_mrr: float
    mean_ndcg: float
    top_k: int

def run_retrieval_eval(entries, embedder, store, *, top_k: int = 5) -> EvalReport: ...
def load_baseline(path: Path) -> dict[str, float]: ...
def save_baseline(path: Path, report: EvalReport) -> None: ...
def assert_not_regressed(report: EvalReport, baseline: dict[str, float], *, adr: str | None = None) -> None: ...
```

## Exceptions and error cases

- `EvalError` raised when the golden dataset is empty or a YAML entry is missing a required
  field (R1, R2) — wraps the underlying cause.
- `EvalError` raised when `store.query` returns a different number of results than `top_k`
  (consistency guard).
- `assert_not_regressed` raises `AssertionError` when `mean_recall` < `baseline["mean_recall"]`
  and no `adr` override is given (R10).

## Deterministic CI strategy (no DB/network in CI)

- `tests/test_metrics.py` never touches a store/embedder — pure-function coverage for R8/R12.
- `tests/test_eval.py` uses an **in-memory `VectorStore`** seeded from the golden repos via
  `run_ingest` with a deterministic local embedder, so the full retrieval eval runs in CI
  without pgvector/Ollama. The optional pgvector-backed run remains available via the CLI
  against a live store (gated by `CODERAG_TEST_DB`).
- Metric functions live in `evals/metrics.py` as pure functions; the store/embedder are
  injected, keeping the core deterministic (R8, R12).

## Discarded alternatives

- **Reuse LangChain/ragas eval utilities.** Rejected: conflicts with the "pure core, no
  provider lock-in" principle in `docs/architecture.md`; we keep metric math dependency-free.
- **Use an LLM to score retrieval relevance.** Rejected: retrieval metrics must be
  deterministic and CI-cheap (R11, R12); LLM-as-judge is deferred to the quality layer.
- **Store baseline in a wiki/Notion.** Rejected: baseline must be versioned in-repo
  (`evals/baseline.json`) so regressions are caught in PRs (R10).
