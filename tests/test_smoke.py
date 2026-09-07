from coderag import Answer, Chunk, ChunkStatus, Citation, Language
from coderag.llm import LlmClient
from coderag.retrieval import Reranker
from coderag.stores import Embedder, VectorStore


def test_core_types_construct() -> None:
    chunk = Chunk(
        path="src/foo.py",
        line_start=1,
        line_end=10,
        text="def f(): pass",
        language=Language.PYTHON,
        hash="abc",
    )
    assert chunk.status is ChunkStatus.PENDING

    citation = Citation(path="src/foo.py", line_start=1, line_end=10)
    assert citation.to_label() == "src/foo.py:1-10"


def test_answer_confidence_verdict() -> None:
    answer = Answer(
        text="see foo",
        citations=(Citation("src/foo.py", 1, 10),),
        confidence=0.9,
        model="test",
    )
    assert answer.confidence_verdict == "high"


def test_ports_are_runtime_protocols() -> None:
    assert getattr(Embedder, "_is_runtime_protocol", False) is True
    assert getattr(VectorStore, "_is_runtime_protocol", False) is True
    assert getattr(LlmClient, "_is_runtime_protocol", False) is True
    assert getattr(Reranker, "_is_runtime_protocol", False) is True
