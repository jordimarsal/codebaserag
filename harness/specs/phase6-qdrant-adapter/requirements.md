# Requirements: phase6-qdrant-adapter

Scope: add a Qdrant vector-store adapter behind the existing `VectorStore` port so the system can use
Qdrant as an alternative to pgvector. Distance metric and collection are configurable; the core never
imports the Qdrant SDK.

## R1
The system shall provide a `QdrantVectorStore` adapter that implements the `VectorStore` port
(`upsert`, `query`).

## R2
The adapter shall depend only on the `VectorStore` port; the Qdrant SDK (`qdrant-client`) shall be
imported lazily so the core has no hard dependency on it.

## R3
The Qdrant collection name shall be configurable via `Settings` (`qdrant_collection`).

## R4
The distance metric (cosine / euclid / dot) shall be configurable via `Settings` (`qdrant_distance`),
defaulting to cosine (matching the existing in-memory store semantics).

## R5
`upsert` shall persist the chunk text and metadata (path, line range, language, hash) as the point
payload so `query` can reconstruct a `Chunk` without a second lookup.

## R6
`query` shall return the top-k `RetrievalResult`s with a similarity score, reconstructed from the
stored payload.

## R7
Connection, upsert, and query failures shall raise `StoreError` (the same error type used by the
pgvector adapter) so callers handle both stores uniformly.

## R8
Eval/tests shall exercise the adapter against an **in-memory Qdrant** (`:memory:`) when `qdrant-client`
is installed, and skip otherwise, so CI stays dependency-free of a live server.

## R9
The `store` backend selection (CLI `ingest`/`query`/`eval` and `build_retriever`) shall accept `qdrant`
as a value, building a `QdrantVectorStore` from `Settings`, without code changes elsewhere.
