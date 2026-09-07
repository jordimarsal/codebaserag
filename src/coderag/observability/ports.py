import time
from typing import Protocol, runtime_checkable


# region Span
class Span:
    """Context manager recording a timed span with mutable attributes."""

    def __init__(self, name: str, **attributes: object) -> None:
        self._name = name
        self._attributes = dict(attributes)
        self._start = 0.0
        self._latency_ms = 0.0

    def set(self, **attributes: object) -> None:
        self._attributes.update(attributes)

    def __enter__(self) -> "Span":
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc: object) -> None:
        self._latency_ms = (time.perf_counter() - self._start) * 1000.0

    @property
    def attributes(self) -> dict[str, object]:
        return dict(self._attributes)

    @property
    def latency_ms(self) -> float:
        return self._latency_ms


# region Tracer
@runtime_checkable
class Tracer(Protocol):
    def span(self, name: str, **attributes: object) -> Span:
        """Return a `Span` context manager for the named step."""
        ...


# region NoOpTracer
class NoOpTracer:
    def span(self, name: str, **attributes: object) -> Span:
        return Span(name, **attributes)
