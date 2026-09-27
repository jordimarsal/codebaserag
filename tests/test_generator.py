from coderag.generation.generator import GenerationError, Generator
from coderag.llm.fake import FakeLlmClient
from coderag.types import Chunk, Language, RetrievalResult


def _chunk(path: str, score: float = 0.8) -> RetrievalResult:
    chunk = Chunk(
        path=path,
        line_start=1,
        line_end=2,
        text=f"body {path}",
        language=Language.PYTHON,
        hash=f"h-{path}",
    )
    return RetrievalResult(chunk=chunk, score=score)


def _retrieved(paths: list[str], score: float = 0.8) -> list[RetrievalResult]:
    return [_chunk(path, score) for path in paths]


# region grounded generation
def test_grounded_answer_builds_citations_and_confidence() -> None:
    fake = FakeLlmClient({"q1": FakeLlmClient.grounded_answer(["a.py"])})
    answer = Generator(fake).answer("q1", _retrieved(["a.py"], score=0.8))
    assert answer.text == "See a.py."
    assert answer.citations[0].path == "a.py"
    assert answer.payload["grounded"] is True
    assert answer.confidence == 0.8


def test_multiple_citations_average_score() -> None:
    fake = FakeLlmClient({"q1": FakeLlmClient.grounded_answer(["a.py", "b.py"])})
    answer = Generator(fake).answer("q1", _retrieved(["a.py", "b.py"], score=0.6))
    assert len(answer.citations) == 2
    assert answer.confidence == 0.6


# region ungrounded generation
def test_ungrounded_answer_flags_and_zero_confidence() -> None:
    fake = FakeLlmClient({"q1": FakeLlmClient.ungrounded_answer()})
    answer = Generator(fake).answer("q1", _retrieved(["a.py"], score=0.8))
    assert answer.payload["grounded"] is False
    assert answer.confidence == 0.0


def test_ungrounded_answer_strict_raises() -> None:
    fake = FakeLlmClient({"q1": FakeLlmClient.ungrounded_answer()})
    try:
        Generator(fake).answer("q1", _retrieved(["a.py"], score=0.8), strict=True)
        raise AssertionError("expected GenerationError")
    except GenerationError:
        pass


# region invalid outputs
def test_empty_answer_raises() -> None:
    fake = FakeLlmClient({"q1": {"answer": "   ", "citations": []}})
    try:
        Generator(fake).answer("q1", _retrieved(["a.py"]))
        raise AssertionError("expected GenerationError")
    except GenerationError:
        pass


def test_missing_citations_raises() -> None:
    fake = FakeLlmClient({"q1": {"answer": "ok"}})
    try:
        Generator(fake).answer("q1", _retrieved(["a.py"]))
        raise AssertionError("expected GenerationError")
    except GenerationError:
        pass


def test_malformed_citation_raises() -> None:
    fake = FakeLlmClient({"q1": {"answer": "ok", "citations": [{"path": "a.py"}]}})
    try:
        Generator(fake).answer("q1", _retrieved(["a.py"]))
        raise AssertionError("expected GenerationError")
    except GenerationError:
        pass


def test_confidence_clamped_to_one() -> None:
    fake = FakeLlmClient({"q1": FakeLlmClient.grounded_answer(["a.py"])})
    answer = Generator(fake).answer("q1", _retrieved(["a.py"], score=2.0))
    assert answer.confidence == 1.0


# region grounding verdict integrity (audit: generator.payload.model-grounded-override)
def test_model_grounded_key_cannot_override_verdict() -> None:
    fake = FakeLlmClient(
        {
            "q1": {
                "answer": "see ghost.py",
                "citations": [{"path": "ghost.py", "line_start": 1, "line_end": 1}],
                "confidence": 0.9,
                "grounded": "true",  # any truthy value would coerce via bool()
            }
        }
    )
    answer = Generator(fake).answer("q1", _retrieved(["a.py"]))
    assert answer.payload["grounded"] is False  # computed verdict wins
    assert answer.confidence == 0.0


def test_zero_citation_answer_is_not_grounded() -> None:
    fake = FakeLlmClient({"q1": {"answer": "cannot answer", "citations": []}})
    answer = Generator(fake).answer("q1", _retrieved(["a.py"]))
    assert answer.payload["grounded"] is False
    assert answer.confidence == 0.0


def test_generation_error_hides_provider_detail() -> None:
    from coderag.llm.ports import LlmClient

    class BrokenLlm(LlmClient):
        def model_name(self) -> str:
            return "broken"

        def generate_structured(self, prompt: str, schema: object) -> object:
            raise RuntimeError("provider https://api.internal SECRET-CANARY")

    try:
        Generator(BrokenLlm()).answer("q1", _retrieved(["a.py"]))
        raise AssertionError("expected GenerationError")
    except GenerationError as exc:
        assert "SECRET-CANARY" not in str(exc)
        assert "RuntimeError" in str(exc)


def test_strict_ungrounded_raises_generation_error_with_tracer() -> None:
    from coderag.observability import NoOpTracer

    fake = FakeLlmClient({"q1": FakeLlmClient.ungrounded_answer()})
    try:
        Generator(fake, tracer=NoOpTracer()).answer("q1", _retrieved(["a.py"]), strict=True)
        raise AssertionError("expected GenerationError")
    except GenerationError:
        pass  # propagated untouched even with an attached tracer
