from coderag.generation.generator import Generator
from coderag.llm.fake import FakeLlmClient
from coderag.observability import InMemoryTracer, NoOpTracer, build_tracer
from coderag.retrieval.retriever import Retriever
from coderag.stores.ports import Embedder, VectorStore
from coderag.types import Chunk, Language, RetrievalResult
from evals.embedder import HashEmbedder


def _chunk(path: str) -> Chunk:
    return Chunk(
        path=path, line_start=1, line_end=2, text=f"body {path}",
        language=Language.PYTHON, hash=f"h-{path}",
    )


class FakeVectorStore:
    def query(self, vector: list[float], top_k: int) -> list[RetrievalResult]:
        return [RetrievalResult(chunk=_chunk("a.py"), score=0.5)]


class FakeBm25:
    def index(self, chunks: list[Chunk]) -> None: ...

    def search(self, query: str, top_k: int) -> list[RetrievalResult]:
        return [RetrievalResult(chunk=_chunk("c.py"), score=0.4)]


class FakeReranker:
    def rerank(self, query, results, top_k):
        return results[:top_k]


def _embedder() -> Embedder:
    return HashEmbedder()


def test_retriever_records_retrieval_span() -> None:
    tracer = InMemoryTracer()
    retriever = Retriever(
        FakeVectorStore(), FakeBm25(), _embedder(), tracer=tracer, strategy="dense", top_k=5
    )
    retriever.retrieve("q")
    names = [s.name for s in tracer.spans]
    assert "retrieval" in names
    span = next(s for s in tracer.spans if s.name == "retrieval")
    assert span.attributes["strategy"] == "dense"
    assert span.attributes["candidate_count"] == 1
    assert span.latency_ms >= 0.0


def test_retriever_records_rerank_span() -> None:
    tracer = InMemoryTracer()
    retriever = Retriever(
        FakeVectorStore(), FakeBm25(), _embedder(),
        reranker=FakeReranker(), tracer=tracer, strategy="hybrid+rerank", top_k=3,
    )
    retriever.retrieve("q")
    names = [s.name for s in tracer.spans]
    assert "retrieval" in names
    assert "rerank" in names
    rerank = next(s for s in tracer.spans if s.name == "rerank")
    assert rerank.attributes["input_count"] >= 1
    assert rerank.attributes["output_count"] == min(2, 3)


def test_generator_records_generation_span() -> None:
    tracer = InMemoryTracer()
    generator = Generator(FakeLlmClient({"q": FakeLlmClient.grounded_answer(["a.py"])}), tracer=tracer)
    generator.answer("q", [RetrievalResult(chunk=_chunk("a.py"), score=0.8)])
    span = next(s for s in tracer.spans if s.name == "generation")
    assert span.attributes["model"] == "fake"
    assert span.attributes["response_chars"] > 0
    assert span.attributes["grounded"] is True
    assert span.attributes["citations"] == 1


def test_failing_tracer_does_not_break_retrieval() -> None:
    class FailingTracer:
        def span(self, name: str, **attributes: object):
            raise RuntimeError("tracer down")

    retriever = Retriever(
        FakeVectorStore(), FakeBm25(), _embedder(),
        tracer=FailingTracer(), strategy="dense", top_k=5,  # type: ignore[arg-type]
    )
    results = retriever.retrieve("q")
    assert [r.chunk.path for r in results] == ["a.py"]


def test_build_tracer_defaults_to_noop() -> None:
    from coderag.config import Settings

    settings = Settings(observability_backend="none")
    assert isinstance(build_tracer(settings), NoOpTracer)
