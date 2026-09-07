# Tasks: phase5-observability

- [x] T1: Create `src/coderag/observability/ports.py` — `Tracer` port + `Span` context-manager protocol +
      `NoOpTracer`.
      depends_on: (none)
      refs: R2, R8, R11

- [x] T2: Create `src/coderag/observability/memory.py` — `InMemoryTracer` collecting `SpanRecord`s
      (name/attributes/latency).
      depends_on: T1
      refs: R7, R10

- [x] T3: Create `src/coderag/observability/langfuse_tracer.py` — `LangfuseTracer` (langfuse extra, lazy
      import) implementing `Tracer`; sends spans to self-hosted Langfuse from config.
      depends_on: T1
      refs: R6

- [x] T4: Create `src/coderag/observability/__init__.py` — exports `Tracer`, `NoOpTracer`, `InMemoryTracer`,
      `LangfuseTracer`, `build_tracer`.
      depends_on: T2, T3
      refs: R9

- [x] T5: Instrument `src/coderag/retrieval/retriever.py` — optional `tracer`, wrap retrieval/rerank in
      spans (strategy/top_k/counts/latency); swallow tracer errors (R8).
      depends_on: T1, T4
      refs: R3, R4, R8

- [x] T6: Instrument `src/coderag/generation/generator.py` — optional `tracer`, wrap generation span
      (prompt/response size, model, latency, grounded); swallow tracer errors (R8).
      depends_on: T1, T4
      refs: R5, R8

- [x] T7: Add `observability_backend`, `langfuse_host`, `langfuse_public_key`, `langfuse_secret_key` to
      `src/coderag/config.py`.
      depends_on: (none)
      refs: R6, R9, R11

- [x] T8: Wire `build_tracer(settings)` into CLI `answer` and pass to retriever/generator.
      depends_on: T4, T5, T6, T7
      refs: R1, R9

- [x] T9: Write `tests/test_observability.py` — `InMemoryTracer` records retrieval/rerank/generation spans;
      a failing tracer does not break retrieval. Run gates; update `harness/progress/current.md`.
      depends_on: T2, T5, T6
      refs: R8, R10
