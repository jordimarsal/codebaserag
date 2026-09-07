# Design: phase3-hybrid-rerank

## Files to create or modify

- `src/coderag/retrieval/bm25.py` — `Bm25Index` protocol/adapter: `index(chunks)`, `search(query, top_k)` returning `list[RetrievalResult]`. Two backends selectable by config: ` TantivyBm25` (tantivy-py) and `PostgresFtsBm25` (Postgres FTS via the pgvector store's DSN).
- `src/coderag/retrieval/fusion.py` — pure `reciprocal_rank_fusion(rankings, k=60) -> list[RetrievalResult]` and `bm25_score` helpers.
- `src/coderag/retrieval/reranker.py` — `CrossEncoderReranker` implementing the existing `Reranker` port (sentence-transformers `bge-reranker-base`).
- `src/coderag/retrieval/retriever.py` — `Retriever` orchestrator with `strategy: dense | hybrid | hybrid+rerank`, injecting `VectorStore`, `Bm25Index`, optional `Reranker`.
- `src/coderag/config.py` — add `retrieval_strategy`, `rerank_model`, `rerank_top_n`, `bm25_backend` settings.
- `src/coderag/cli.py` / future API — pass the strategy (e.g. `query --strategy hybrid`).
- `evals/harness.py` — `run_retrieval_eval` accepts a `retriever` callable (or strategy) so the same golden set runs under each mode.
- `evals/experiments/` — `hybrid_vs_dense.md` report template (dense vs hybrid vs hybrid+rerank table).
- `tests/test_fusion.py` — pure-function tests for RRF + BM25 scoring.
- `tests/test_retriever.py` — orchestration test with fake dense store + fake BM25 index (no services).

## Public signatures

```python
# bm25.py
class Bm25Index(Protocol):
    def index(self, chunks: list[Chunk]) -> None: ...
    def search(self, query: str, top_k: int) -> list[RetrievalResult]: ...

# fusion.py
def reciprocal_rank_fusion(rankings: list[list[RetrievalResult]], k: int = 60) -> list[RetrievalResult]: ...
def bm25_idf(...)  # internal helper if needed

# reranker.py
class CrossEncoderReranker:
    def __init__(self, model: str = "bge-reranker-base", device: str = "cpu") -> None
    def rerank(self, query: str, results: list[RetrievalResult], top_k: int) -> list[RetrievalResult]: ...

# retriever.py
class Retriever:
    def __init__(self, store: VectorStore, bm25: Bm25Index, *, reranker: Reranker | None = None,
                 strategy: str = "dense", top_k: int = 5, rerank_top_n: int = 20) -> None
    def retrieve(self, question: str) -> list[RetrievalResult]: ...
```

## Exceptions and error cases

- `RetrievalError` raised when both dense and BM25 return nothing or a backend call fails.
- `ConfigurationError` when `strategy="hybrid+rerank"` but no `Reranker` is configured.
- `CrossEncoderReranker` falls back to the fused ranking + `logging.warning` when the model
  cannot be loaded (R11), so queries still return results.

## Strategy / config flow

- `Settings.retrieval_strategy` (`dense` | `hybrid` | `hybrid+rerank`) drives the default.
- `Retriever.retrieve` builds the dense list via `store.query`, the lexical list via `bm25.search`,
  fuses with RRF, and (only in `hybrid+rerank`) passes the top-`rerank_top_n` to `reranker.rerank`.
- BM25 backend chosen by `Settings.bm25_backend` (`tantivy` | `postgres`); both implement
  `Bm25Index`, so the `Retriever` is unchanged (R7).

## Discarded alternatives

- **RRF vs CombSUM/CombMNZ.** Chosen RRF because it needs no score normalization between dense
  and lexical scales and is the brief's specified method; CombSUM would require calibrating the
  dense score distribution.
- **Lexical via Postgres FTS only.** Rejected as the sole option: `tantivy-py` keeps retrieval
  dependency-free of the DB and testable offline; we support both behind `Bm25Index`.
- **Rerank before fusion.** Rejected: reranking requires a fixed candidate set; fusing first then
  reranking the top-N is cheaper and matches the brief's "top-20 → top-5".

## Eval integration

- `run_retrieval_eval` takes a `retriever` callable `(question) -> list[RetrievalResult]` instead
  of (embedder, store). A small adapter builds the retriever per strategy. The existing metric
  functions and regression guard (F2) are reused unchanged.
- The experiment table (`evals/experiments/hybrid_vs_dense.md`) records mean recall@5 / MRR / nDCG
  for each strategy side-by-side; this is the artifact the brief requires.
