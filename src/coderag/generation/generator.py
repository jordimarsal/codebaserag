import logging
from contextlib import contextmanager

from coderag.llm.ports import LlmClient
from coderag.observability.ports import Span, Tracer
from coderag.types import Answer, Citation, RetrievalResult

logger = logging.getLogger("coderag.generation")

DEFAULT_ANSWER_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "citations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "line_start": {"type": "integer"},
                    "line_end": {"type": "integer"},
                },
                "required": ["path", "line_start", "line_end"],
            },
        },
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
    },
    "required": ["answer", "citations"],
}


# region GenerationError
class GenerationError(Exception):
    """Raised when structured generation fails (empty, unparseable, schema-invalid, or ungrounded)."""


# region Generator
class Generator:
    def __init__(
        self, llm: LlmClient, schema: dict | None = None, tracer: Tracer | None = None
    ) -> None:
        self._llm = llm
        self._schema = schema or DEFAULT_ANSWER_SCHEMA
        self._tracer = tracer

    @contextmanager
    def _trace(self, name: str, **attributes: object):
        if self._tracer is None:
            yield Span(name, **attributes)
            return
        try:
            with self._tracer.span(name, **attributes) as span:
                yield span
        except Exception as exc:  # non-blocking (R8)
            logger.warning("tracer failed for span %s: %s", name, exc)
            yield Span(name, **attributes)

    def answer(self, question: str, retrieved: list[RetrievalResult], *, strict: bool = False) -> Answer:
        prompt = self._build_prompt(question, retrieved)
        with self._trace(
            "generation", model=self._llm.model_name(), prompt_chars=len(prompt)
        ) as span:
            try:
                data = self._llm.generate_structured(prompt, self._schema)
            except Exception as exc:
                raise GenerationError(f"LLM structured generation failed: {exc}") from exc
            if not isinstance(data, dict):
                raise GenerationError("structured output was not an object")
            text = data.get("answer")
            if not isinstance(text, str) or not text.strip():
                raise GenerationError("structured output missing non-empty 'answer'")
            raw_cites = data.get("citations")
            if not isinstance(raw_cites, list):
                raise GenerationError("structured output missing 'citations' list")

            citations = self._parse_citations(raw_cites)
            grounded = self._grounded(citations, retrieved)
            if not grounded:
                logger.warning("answer has ungrounded citations; confidence forced to 0.0")
                if strict:
                    raise GenerationError("answer contains ungrounded citations")
            confidence = self._confidence(citations, retrieved) if grounded else 0.0
            span.set(
                response_chars=len(text or ""),
                grounded=grounded,
                citations=len(citations),
            )
        return Answer(
            text=text,
            citations=tuple(citations),
            confidence=confidence,
            model=self._llm.model_name(),
            payload={"grounded": grounded, **data},
        )

    # region helpers
    def _build_prompt(self, question: str, retrieved: list[RetrievalResult]) -> str:
        context = "\n\n".join(
            f"[{i}] {r.chunk.path}:{r.chunk.line_start}-{r.chunk.line_end}\n{r.chunk.text}"
            for i, r in enumerate(retrieved, start=1)
        )
        return (
            "Answer the question using ONLY the provided code context. "
            "Cite the exact path:line_start-line_end of every chunk you use.\n\n"
            f"QUESTION:\n{question}\n\nCONTEXT:\n{context}"
        )

    def _parse_citations(self, raw_cites: list) -> list[Citation]:
        citations: list[Citation] = []
        for item in raw_cites:
            if not isinstance(item, dict):
                raise GenerationError("citation was not an object")
            try:
                citation = Citation(
                    path=str(item["path"]),
                    line_start=int(item["line_start"]),
                    line_end=int(item["line_end"]),
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise GenerationError(f"invalid citation: {item}") from exc
            citations.append(citation)
        return citations

    def _grounded(self, citations: list[Citation], retrieved: list[RetrievalResult]) -> bool:
        keys = {(r.chunk.path, r.chunk.line_start, r.chunk.line_end) for r in retrieved}
        return all((c.path, c.line_start, c.line_end) in keys for c in citations)

    def _confidence(self, citations: list[Citation], retrieved: list[RetrievalResult]) -> float:
        if not citations:
            return 0.0
        scores: list[float] = []
        for citation in citations:
            for result in retrieved:
                if (
                    result.chunk.path == citation.path
                    and result.chunk.line_start == citation.line_start
                    and result.chunk.line_end == citation.line_end
                ):
                    scores.append(result.score)
                    break
        if not scores:
            return 0.0
        return max(0.0, min(1.0, sum(scores) / len(scores)))
