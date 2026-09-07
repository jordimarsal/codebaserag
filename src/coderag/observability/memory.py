from dataclasses import dataclass, field

from coderag.observability.ports import Span


# region SpanRecord
@dataclass
class SpanRecord:
    name: str
    attributes: dict[str, object] = field(default_factory=dict)
    latency_ms: float = 0.0


# region InMemoryTracer
class InMemoryTracer:
    def __init__(self) -> None:
        self.spans: list[SpanRecord] = []

    def span(self, name: str, **attributes: object) -> "_RecordingSpan":
        return _RecordingSpan(self, name, **attributes)

    def _record(self, record: SpanRecord) -> None:
        self.spans.append(record)


class _RecordingSpan(Span):
    def __init__(self, tracer: InMemoryTracer, name: str, **attributes: object) -> None:
        super().__init__(name, **attributes)
        self._tracer = tracer

    def __exit__(self, *exc: object) -> None:
        super().__exit__(*exc)
        self._tracer._record(
            SpanRecord(name=self._name, attributes=self.attributes, latency_ms=self._latency_ms)
        )
