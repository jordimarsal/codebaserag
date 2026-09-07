# Architecture

This document defines the architectural quality standards for `codebase-rag`. It describes
the principles that guide all design decisions, the data flow the system follows, and the
boundaries that must never be crossed. Every contributor and agent is expected to
understand and follow these standards. When in doubt, refer back to this document.

> Source of truth for the product scope: `01-rag-codi-propis.md`. This file captures the
> *enforced* architecture; the project brief captures the *intent*.

---

## Principles

The system is a **hexagonal (ports & adapters)** RAG over your own source code, with a
**pipeline of pure transforms** at its core. The following principles are non-negotiable:

- **Pure core, I/O at the edges.** Chunking, RRF fusion, prompt assembly, and citation
  calculation are deterministic functions with no network access. Readers, embedders,
  stores, rerankers and LLMs are *ports* (`Protocol`); the core never imports an adapter.
- **Adapters for interchangeability.** `VectorStore`, `Embedder`, `LlmClient`, `Reranker`
  are defined as `Protocol` interfaces. pgvector, Qdrant, Ollama, Anthropic, OpenAI are
  interchangeable adapters that implement those protocols without touching the core.
- **Three separated subdomains.** `ingest`, `retrieval`, and `generation` are independent
  packages. The vector store is the *only* coupling point between ingest and retrieval:
  ingest can run as a CLI and retrieval as a FastAPI service without sharing I/O code.
- **Eval-first.** No change to a chunker, embedder, prompt, or reranker is merged unless
  the eval suite is green against the documented baseline. Evals are deterministic tests,
  not estimates.
- **Structured output only.** Generation never returns free-form, unvalidated text.
  Responses are Pydantic models. Citations are exact `path:line_start-line_end` references.
- **Determinism for the core.** The core must be testable with no mocks of network
  boundaries. Adapter behavior is verified at the boundary, not in the core.

---

## Data Flow

### Ingestion path (CLI)

```
repo local
  └─▶ READERS        # read .md/.py/.toml/.yaml, honour .gitignore
       └─▶ CHUNKERS  # fixed | recursive | ast (symbol-level)
            └─▶ EMBEDDER (port)
                 └─▶ STORE (port: pgvector default / Qdrant adapter)
```

Each stored record carries: `chunk`, `embedding`, and metadata
(`path`, `line_start`, `line_end`, `hash`, `language`).

### Query path (FastAPI → answer)

```
question
  └─▶ RETRIEVER            # dense + BM25
       └─▶ FUSION (RRF)    # reciprocal rank fusion of result lists
            └─▶ RERANKER   # cross-encoder over top-k (optional, config-gated)
                 └─▶ PROMPT BUILDER   # few-shot, structured schema
                      └─▶ LLM (port)  # Pydantic structured output + citations
```

### Observability

Every query emits a trace to Langfuse (retrieval, rerank, prompt, response, cost, latency).
The eval harness (`evals/harness.py`) consumes the same paths deterministically.

```
RETRIEVER ─┐
RERANKER  ─┼─▶ Langfuse trace ◀─ generation
PROMPT    ─┘
                  │
                  ▼
         Eval harness (pytest + judge)
```

---

## Do Not

- Do **not** import an adapter (pgvector, Qdrant, Ollama, Anthropic, OpenAI, Langfuse) from
  inside the core (`ingest`/`retrieval`/`generation` pure logic). Depend on the `Protocol`,
  not the implementation.
- Do **not** put network or file I/O inside pure transforms (chunking decisions, RRF
  fusion, prompt assembly, citation math). Keep them pure and unit-testable offline.
- Do **not** return unvalidated free-form LLM text. Generation output is always a Pydantic
  model.
- Do **not** fabricate or approximate citations. A citation must resolve to a real
  `path:line_start-line_end`; never emit a path that does not exist.
- Do **not** let `ingest` and `retrieval` share I/O code. The store is their only contract.
- Do **not** merge a chunker/embedder/prompt/reranker change that drops `recall@5` below
  the documented baseline without an ADR justifying it.
- Do **not** create global state for services. Compose collaborators by injection.
- Do **not** introduce provider lock-in (no direct SDK calls in core). Route through
  `Protocol` adapters.
