import logging

from coderag.config import Settings
from coderag.observability.ports import Span

logger = logging.getLogger("coderag.observability")


# region LangfuseTracer
class LangfuseTracer:
    def __init__(self, settings: Settings) -> None:
        from langfuse import Langfuse  # lazy: optional dependency

        self._client = Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
        self._trace_id: str | None = None

    def _ensure_trace(self) -> str:
        if self._trace_id is None:
            trace = self._client.trace(name="codebaserag-query")
            self._trace_id = getattr(trace, "id", None) or "codebaserag"
        return self._trace_id

    def span(self, name: str, **attributes: object) -> "_LangfuseSpan":
        return _LangfuseSpan(self, name, **attributes)


class _LangfuseSpan(Span):
    def __init__(self, tracer: LangfuseTracer, name: str, **attributes: object) -> None:
        super().__init__(name, **attributes)
        self._tracer = tracer
        self._span = None

    def __enter__(self) -> "_LangfuseSpan":
        super().__enter__()
        try:
            trace_id = self._tracer._ensure_trace()
            self._span = self._tracer._client.span(
                name=self._name, trace_id=trace_id, metadata=self.attributes
            )
        except Exception as exc:  # non-blocking (R8)
            logger.warning("langfuse span start failed: %s", exc)
            self._span = None
        return self

    def __exit__(self, *exc: object) -> None:
        super().__exit__(*exc)
        if self._span is not None:
            try:
                self._span.end(
                    metadata=self.attributes,
                    output={"latency_ms": self._latency_ms},
                )
                self._tracer._client.flush()
            except Exception as err:  # non-blocking (R8)
                logger.warning("langfuse span end failed: %s", err)
