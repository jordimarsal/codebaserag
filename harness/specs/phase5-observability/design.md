# Design: phase5-observability

## Files to create or modify

- `src/coderag/observability/ports.py` — `Tracer` port + `Span` context-manager protocol; `NoOpTracer`.
- `src/coderag/observability/memory.py` — `InMemoryTracer` (collects `SpanRecord`s) for tests/offline.
- `src/coderag/observability/langfuse_tracer.py` — `LangfuseTracer` adapter (langfuse extra), lazy import.
- `src/coderag/observability/__init__.py` — exports `Tracer`, `NoOpTracer`, `InMemoryTracer`, `build_tracer`.
- `src/coderag/retrieval/retriever.py` — accept `tracer: Tracer | None`; wrap retrieval/rerank in spans
  (R3/R4/R8); tracer failures swallowed.
- `src/coderag/generation/generator.py` — accept `tracer: Tracer | None`; wrap generation in a span (R5/R8).
- `src/coderag/config.py` — add `observability_backend: str = "none"`, `langfuse_host`, `langfuse_public_key`,
  `langfuse_secret_key`.
- `src/coderag/cli.py` — build tracer from `Settings`; pass to retriever/generator in `answer`.
- `tests/test_observability.py` — `InMemoryTracer` records retrieval/rerank/generation spans; failing
  tracer does not break retrieval (R8).

## Public signatures

```python
# observability/ports.py
class Span:  # context manager
    def set(self, **attributes: object) -> None: ...
    def __enter__(self) -> "Span": ...
    def __exit__(self, *exc) -> None: ...

@runtime_checkable
class Tracer(Protocol):
    def span(self, name: str, **attributes: object) -> Span: ...

# observability/memory.py
@dataclass
class SpanRecord:
    name: str
    attributes: dict[str, object]
    latency_ms: float

class InMemoryTracer:
    spans: list[SpanRecord]
    def span(self, name: str, **attributes: object) -> Span: ...

def build_tracer(settings: Settings) -> Tracer:
    if settings.observability_backend == "langfuse":
        return LangfuseTracer(settings)
    return NoOpTracer()
```

## Span model

`Tracer.span(name, **attributes)` returns a `Span` context manager. On `__enter__` it records a start
timestamp and the initial attributes; `Span.set(**attrs)` merges attributes mid-span (e.g. result
count after the call returns); on `__exit__` it records end time and appends a `SpanRecord` to the
tracer (for `InMemoryTracer`) or flushes to Langfuse (for `LangfuseTracer`).

## Instrumentation points

- `Retriever.retrieve`:
  - `with tracer.span("retrieval", strategy=..., top_k=...):` then after computing `fused`,
    `span.set(candidate_count=len(fused))`.
  - when reranking: `with tracer.span("rerank", input_count=..., top_k=...):` around `reranker.rerank`,
    then `span.set(output_count=len(...))`.
- `Generator.answer`:
  - `with tracer.span("generation", model=..., prompt_chars=...):` around `generate_structured`, then
    `span.set(response_chars=..., grounded=..., citations=len(...))`.

## Non-blocking (R8)

Every tracer interaction is wrapped in `try/except Exception: log.warning(...)` inside the core so a
broken Langfuse endpoint never fails a user query. `NoOpTracer.span` returns a no-op `Span`.

## Discarded alternatives

- **OpenTelemetry SDK directly in core.** Rejected: pulls a heavy dependency and couples the core to
  OTel; a thin `Tracer` port keeps the core clean and Langfuse is just one adapter.
- **Tracing only at the CLI layer.** Rejected: would miss per-step latency (rerank vs retrieval);
  instrumenting the retriever/generator captures the real costs.
- **Sampling in core.** Rejected: sampling policy belongs to the backend (Langfuse); core always emits,
  backend decides what to keep.

## Eval/CI integration

`InMemoryTracer` is the default in tests; `NoOpTracer` is the runtime default (`observability_backend="none"`)
so CI has zero new dependencies. Toggling `CODERAG_OBSERVABILITY_BACKEND=langfuse` activates the adapter
without code changes (R9/R11).
