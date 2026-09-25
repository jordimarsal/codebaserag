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
