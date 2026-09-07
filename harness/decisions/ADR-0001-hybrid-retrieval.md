# ADR-0001: Hybrid retrieval via Reciprocal Rank Fusion

- **Date:** 2026-09-07
- **Status:** accepted
- **Feature:** phase3-hybrid-rerank

## Context

Dense single-vector retrieval over a code corpus misses exact-symbol / keyword matches (function
names, error strings, config keys) that lexical search finds trivially, and lexical search misses
semantic intent. We need one ranked list that benefits from both without hand-tuning score scales.

## Decision

Retrieve with two independent rankers — a dense `VectorStore` and a `Bm25Index` — and merge them with
**Reciprocal Rank Fusion** (`score = Σ 1/(k + rank)`, `k = 60`), which needs no score normalization
because it operates on ranks only. An optional cross-encoder `Reranker` reranks the fused top-N
(default 20 → 5). The strategy (`dense` | `hybrid` | `hybrid+rerank`) is selected via `Settings`.

## Alternatives considered

- **CombSUM / CombMNZ.** Rejected: requires calibrating the dense score distribution to the lexical
  one; RRF avoids that and is the brief's specified method.
- **Lexical only via Postgres FTS.** Rejected as the sole path: it cannot capture semantic queries and
  keeps retrieval dependent on the DB. We support `tantivy` and `postgres` BM25 backends behind one
  port instead.

## Consequences

Cheap to reverse (fusion is a pure function, `reciprocal_rank_fusion`). The retriever now depends on
three ports (`VectorStore`, `Bm25Index`, `Reranker`) but no concrete SDK. Regression in `recall@5`
vs the established baseline blocks the change unless an ADR overrides it.
