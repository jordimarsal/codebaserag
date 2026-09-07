# ADR-0003: Qdrant as a second VectorStore adapter

- **Date:** 2026-09-07
- **Status:** accepted
- **Feature:** phase6-qdrant-adapter

## Context

pgvector is the default store, but some deployments prefer Qdrant (managed, distributed, different
distance options). The system must support both without forking the retrieval/generation core.

## Decision

Add `QdrantVectorStore` implementing the `VectorStore` port (`upsert` / `query` / `count`). The Qdrant
SDK (`qdrant-client`) is imported lazily and is an optional extra, so the core has no hard dependency.
Chunk text + metadata are stored as the point payload so `query` reconstructs full `Chunk`s. The
collection name and distance metric (cosine / euclid / dot, default cosine) come from `Settings`.
A shared `StoreError` (moved to `stores/errors.py`) is raised on any failure, identical to the
pgvector adapter, so the CLI/API handle both uniformly. `store="qdrant"` is a valid backend everywhere.

## Alternatives considered

- **Reuse the pgvector schema inside Qdrant.** Rejected: different backends; the port isolates them and
  keeps each adapter self-contained.
- **Require a live Qdrant server for tests.** Rejected: `:memory:` mode covers the round-trip offline;
  tests skip when `qdrant-client` is absent, keeping CI dependency-free.

## Consequences

Cheap to reverse (pure adapter behind a port). The eval suite now runs against either store; a future
comparative table (pgvector vs Qdrant) is an ADR-level decision, not a code change. `qdrant-client`
joined the mypy `ignore_missing_imports` overrides.
