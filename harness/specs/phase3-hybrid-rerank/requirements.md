# Requirements: phase3-hybrid-rerank

Scope: add hybrid retrieval (BM25 + dense) fused with Reciprocal Rank Fusion, plus an
optional cross-encoder reranker over the fused top-k. This builds on F1 (dense store) and
F2 (deterministic eval). The eval harness must measure hybrid vs dense so the experiment is
quantified, not estimated.

## R1
The system shall provide a BM25 retriever that, given a query, returns ranked chunks from an
indexed corpus using keyword (lexical) scoring.

## R2
The system shall define a `Retriever` orchestrator that executes dense retrieval and BM25
retrieval and merges their result lists with **Reciprocal Rank Fusion** (RRF) into a single
ranked list.

## R3
The RRF fusion shall combine rankings using the standard formula `score = sum(1 / (k + rank))`
per chunk (default `k = 60`), independent of the original score scales of each retriever.

## R4
The `Retriever` shall be configurable to run in `dense`, `hybrid` (dense + BM25 + RRF), or
`hybrid+rerank` mode via a single strategy flag.

## R5
The system shall provide a `Reranker` adapter (cross-encoder, e.g. `bge-reranker-base` via
sentence-transformers) implementing the `Reranker` port, reranking the fused top-N (default
top-20) and keeping the top-k (default top-5).

## R6
The `Retriever` shall depend only on ports (`VectorStore` for dense, a `Bm25Index` port for
lexical, `Reranker` for reranking); it shall not import concrete store/reranker SDKs.

## R7
The BM25 retriever shall be implementable against `tantivy-py` or Postgres FTS, selected by
configuration, without changing the `Retriever` orchestration.

## R8
The hybrid/rerank mode shall be activable by configuration (env/config flag) so it can be
toggled without code changes to the calling layer (CLI/API).

## R9
The eval harness shall support running the same golden dataset under `dense` and `hybrid`
(and `hybrid+rerank` when available) strategies and report recall@5, MRR, and nDCG for each.

## R10
The experiment results (dense vs hybrid vs hybrid+rerank) shall be emitted as a versioned
markdown table (artifact), and a regression in `recall@5` vs the established baseline shall
block the change unless justified by an ADR.

## R11
When the reranker backend is unavailable (model not loaded), the system shall fall back to the
fused ranking and log a warning, rather than failing the query.

## R12
The RRF fusion and BM25 scoring shall be pure, deterministic functions unit-testable without a
network or vector store.
