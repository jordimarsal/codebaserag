from pathlib import Path
from typing import TYPE_CHECKING

from evals.embedder import HashEmbedder

from coderag.config import Settings
from coderag.generation.generator import GenerationError
from coderag.ingest.pipeline import collect_chunks
from coderag.llm.fake import FakeLlmClient
from coderag.llm.litellm_client import LitellmClient
from coderag.llm.llamacpp_embedder import LlamaCppEmbedder
from coderag.llm.ollama_embedder import OllamaEmbedder
from coderag.llm.ports import EmbedderError
from coderag.retrieval.bm25 import InMemoryBm25, PostgresFtsBm25, TantivyBm25
from coderag.retrieval.reranker import CrossEncoderReranker
from coderag.retrieval.retriever import Retriever
from coderag.stores.errors import StoreError
from coderag.stores.memory import InMemoryVectorStore
from coderag.stores.qdrant import QdrantVectorStore

if TYPE_CHECKING:
    from coderag.llm.ports import LlmClient
    from coderag.observability.ports import Tracer
    from coderag.stores.ports import Embedder, VectorStore


def _build_pgvector_store(settings: Settings, dim: int) -> "VectorStore":
    try:
        from coderag.stores.pgvector import PgvectorStore  # lazy: optional dependency
    except ImportError as exc:
        raise StoreError(
            f"pgvector backend needs the 'pgvector' extra: pip install 'codebaserag[pgvector]' ({exc})"
        ) from exc
    return PgvectorStore(dsn=settings.database_dsn, dim=dim)


def _build_qdrant_store(settings: Settings, dim: int) -> "VectorStore":
    try:
        return QdrantVectorStore(
            url=settings.qdrant_url,
            collection=settings.qdrant_collection,
            dim=dim,
            distance=settings.qdrant_distance,
        )
    except ImportError as exc:
        raise StoreError(
            f"qdrant backend needs the 'qdrant' extra: pip install 'codebaserag[qdrant]' ({exc})"
        ) from exc


# region build_retriever
def build_retriever(
    settings: Settings,
    *,
    backend: str,
    repo: Path,
    strategy: str,
    top_k: int,
    tracer: "Tracer | None" = None,
) -> Retriever:
    reranker = CrossEncoderReranker(settings.rerank_model) if "rerank" in strategy else None
    if backend == "memory":
        embedder: Embedder = HashEmbedder()
        chunks = collect_chunks(repo, chunk_size=settings.chunk_size)
        store: VectorStore = InMemoryVectorStore(dim=embedder.dim())
        store.upsert(chunks, embedder.embed([chunk.text for chunk in chunks]))
        bm25 = InMemoryBm25()
        bm25.index(chunks)
    elif backend == "pgvector":
        embedder = build_embedder(settings)
        store = _build_pgvector_store(settings, embedder.dim())
        if settings.bm25_backend == "tantivy":
            bm25 = TantivyBm25()
        else:
            bm25 = PostgresFtsBm25(settings.database_dsn)
    elif backend == "qdrant":
        embedder = build_embedder(settings)
        store = _build_qdrant_store(settings, embedder.dim())
        if settings.bm25_backend == "tantivy":
            bm25 = TantivyBm25()
        else:
            bm25 = PostgresFtsBm25(settings.database_dsn)
    else:
        raise ValueError(f"unknown backend: {backend}")
    return Retriever(
        store,
        bm25,
        embedder,
        reranker=reranker,
        strategy=strategy,
        top_k=top_k,
        rerank_top_n=settings.rerank_top_n,
        tracer=tracer,
    )


# region build_llm
def build_llm(settings: Settings) -> "LlmClient":
    if settings.llm_backend == "fake":
        return FakeLlmClient()
    try:
        return LitellmClient(model=settings.llm_model, backend=settings.llm_backend)
    except ImportError as exc:
        raise GenerationError(
            f"llm backend needs the 'llm' extra: pip install 'codebaserag[llm]' "
            f"or set CODERAG_LLM_BACKEND=fake ({exc})"
        ) from exc


# region build_embedder
def build_embedder(settings: Settings) -> "Embedder":
    if settings.embedder_backend == "llamacpp":
        return LlamaCppEmbedder(model=settings.embedder_model, base_url=settings.embedder_url)
    try:
        return OllamaEmbedder(model=settings.embedder_model, base_url=settings.embedder_url)
    except ImportError as exc:
        raise EmbedderError(
            f"ollama embedder needs the 'embeddings' extra: pip install 'codebaserag[embeddings]' ({exc})"
        ) from exc


# region build_store
def build_store(settings: Settings) -> "tuple[VectorStore, Embedder]":
    if settings.vector_store == "memory":
        embedder: Embedder = HashEmbedder()
        store: VectorStore = InMemoryVectorStore(dim=embedder.dim())
    elif settings.vector_store == "pgvector":
        embedder = build_embedder(settings)
        store = _build_pgvector_store(settings, embedder.dim())
    elif settings.vector_store == "qdrant":
        embedder = build_embedder(settings)
        store = _build_qdrant_store(settings, embedder.dim())
    else:
        raise ValueError(f"unknown vector_store: {settings.vector_store}")
    return store, embedder
