from coderag.config import Settings
from coderag.observability.memory import InMemoryTracer, SpanRecord
from coderag.observability.ports import NoOpTracer, Span, Tracer


def build_tracer(settings: Settings) -> Tracer:
    if settings.observability_backend == "langfuse":
        from coderag.observability.langfuse_tracer import LangfuseTracer

        return LangfuseTracer(settings)
    return NoOpTracer()


__all__ = [
    "Tracer",
    "Span",
    "NoOpTracer",
    "InMemoryTracer",
    "SpanRecord",
    "build_tracer",
]
