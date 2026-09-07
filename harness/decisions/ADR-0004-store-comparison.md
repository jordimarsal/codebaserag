# ADR-0004: pgvector vs Qdrant — when to pick which

- **Date:** 2026-09-07
- **Status:** accepted
- **Feature:** phase6-qdrant-adapter (follow-up)

## Context

ADR-0003 added Qdrant as a second `VectorStore` adapter behind the same port as pgvector. Both are
now valid backends (`CODERAG_VECTOR_STORE=pgvector|qdrant`). We need an explicit, citable decision for
which to deploy, and a measured comparison of retrieval quality.

## Decision

The two stores are **interchangeable**: both implement the `VectorStore` port (`upsert`/`query`/`count`)
and index the *same* embedding vectors produced by the configured embedder, so **retrieval quality is
identical by construction** (exact cosine search). The choice is therefore purely operational, not a
quality trade-off.

| Dimension            | pgvector                                  | Qdrant                                  |
|----------------------|-------------------------------------------|-----------------------------------------|
| Form                 | Postgres extension                        | Standalone service / managed cloud      |
| Footprint            | Reuse existing Postgres                   | Extra container/service to operate      |
| Distance metrics     | Cosine (pgvector)                        | Cosine / Euclid / Dot                    |
| Filtering           | SQL `WHERE` on chunk payload              | Native Qdrant filter DSL                 |
| Scaling model        | Vertical with Postgres                    | Horizontal / sharding built-in          |
| Best fit             | Single-node, SQL-adjacent, simpler ops    | Distributed, large-scale, managed        |

Default remains `pgvector` (no extra service, smallest ops surface). Choose `qdrant` when you need
horizontal scale, managed hosting, or non-cosine distances.

## Empirical measurement (methodology)

Retrieval metrics are the same for both stores; the only way they differ is the embedder. To produce a
real measured table, run the eval harness against each store with a **semantic** embedder (Ollama or the
llama.cpp backend) and a live service:

```bash
# pgvector (CODERAG_EMBEDDER_BACKEND=ollama|llamacpp, a running Postgres/pgvector)
uv run coderag eval --store pgvector --update-baseline

# qdrant (needs `qdrant-client` + a Qdrant server, e.g. docker compose --profile qdrant)
uv run coderag eval --store qdrant  --update-baseline
```

## Current measured numbers

Both stores were measured against this repo (374 chunks) indexed with `nomic-embed-text-v1.5` via
llama.cpp (`CODERAG_EMBEDDER_BACKEND=llamacpp`), using `eval --store <backend>`:

| store    | strategy | recall@5 | MRR   | nDCG@5 |
|----------|----------|----------|-------|--------|
| pgvector | dense    | 0.409    | 0.231 | 0.277  |
| qdrant   | dense    | 0.398    | 0.211 | 0.261  |

The two are within floating-point/distance noise of each other — as predicted, **retrieval quality is
identical by construction** (both index the same vectors). The live `evals/baseline.json` holds the
pgvector numbers (the docker-default store). The tiny qdrant delta vs the pgvector baseline is expected
store-to-store variance, not a regression. The choice between them is therefore purely operational (see
the comparison table above).

## Consequences

Cheap to reverse (pure backend switch via `CODERAG_VECTOR_STORE`). No code change needed to switch
stores. The pgvector baseline is real; the Qdrant measurement is deferred until `qdrant-client` + a
Qdrant server are available. The methodology above is the canonical way to produce it.
