from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from coderag.api.models import (
    AnswerOut,
    AnswerRequest,
    ChunkOut,
    ErrorOut,
    IngestRequest,
    QueryRequest,
)
from coderag.compose import (
    build_llm,
    build_reranker,
    build_serving_components,
)
from coderag.config import Settings
from coderag.generation.generator import GenerationError, Generator
from coderag.ingest.pipeline import IngestError, collect_chunks, run_ingest
from coderag.llm.ollama_embedder import EmbedderError
from coderag.observability import build_tracer
from coderag.retrieval.reranker import CrossEncoderReranker
from coderag.retrieval.retriever import RetrievalError, Retriever
from coderag.stores.errors import StoreError


# region create_app
def create_app(settings: Settings) -> FastAPI:
    app = FastAPI(title="codebaserag", version="0.1.0")

    # Heavy components are built exactly once per process: the memory backend
    # indexes the configured repo here, and pgvector/qdrant open one store
    # connection. Handlers only assemble the cheap Retriever wrapper per
    # request (audit findings api-query-memory-backend-reindex-per-request,
    # api.crossencoder-per-request-construction-no-preauth-gate).
    store, embedder, bm25 = build_serving_components(settings)
    tracer = build_tracer(settings)
    llm = build_llm(settings)
    reranker_cache: dict[str, CrossEncoderReranker] = {}

    def _reranker_for(strategy: str) -> CrossEncoderReranker | None:
        if "rerank" not in strategy:
            return None
        if "reranker" not in reranker_cache:
            reranker_cache["reranker"] = build_reranker(settings)
        return reranker_cache["reranker"]

    @app.exception_handler(RetrievalError)
    @app.exception_handler(GenerationError)
    async def _bad_request(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=400, content=ErrorOut(error=str(exc)).model_dump())

    @app.exception_handler(StoreError)
    @app.exception_handler(IngestError)
    @app.exception_handler(EmbedderError)
    async def _server_error(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=500, content=ErrorOut(error=str(exc)).model_dump())

    @app.post("/ingest")
    def ingest(body: IngestRequest) -> "dict[str, int]":
        configured = Path(settings.repo).resolve()
        requested = Path(body.repo if body.repo is not None else settings.repo).resolve()
        if requested != configured:
            # Security invariant: the API only ever indexes the operator-configured
            # repository. A caller-supplied path would turn this endpoint into an
            # arbitrary-directory read primitive (see audit finding
            # api-unauth-ingest-repo-scope-override).
            raise HTTPException(
                status_code=400,
                detail="repo does not match the configured ingest scope",
            )
        if settings.vector_store == "memory":
            # The in-memory serving corpus is indexed once at startup and its
            # stores are append-only: report what a (re)index would produce
            # instead of duplicating the corpus the handlers serve from.
            indexed = len(
                collect_chunks(
                    configured,
                    chunk_size=settings.chunk_size,
                    max_file_bytes=settings.ingest_max_file_bytes,
                    max_files=settings.ingest_max_files,
                    max_total_bytes=settings.ingest_max_total_bytes,
                )
            )
            return {"indexed": indexed}
        indexed = run_ingest(
            configured,
            embedder,
            store,
            chunk_size=settings.chunk_size,
            max_file_bytes=settings.ingest_max_file_bytes,
            max_files=settings.ingest_max_files,
            max_total_bytes=settings.ingest_max_total_bytes,
        )
        return {"indexed": indexed}

    @app.post("/query", response_model=list[ChunkOut])
    def query(body: QueryRequest) -> list[ChunkOut]:
        retriever = Retriever(
            store,
            bm25,
            embedder,
            reranker=_reranker_for(body.strategy),
            strategy=body.strategy,
            top_k=body.top_k,
            rerank_top_n=settings.rerank_top_n,
            tracer=tracer,
        )
        results = retriever.retrieve(body.question)
        return [
            ChunkOut(
                path=r.chunk.path,
                line_start=r.chunk.line_start,
                line_end=r.chunk.line_end,
                score=r.score,
            )
            for r in results
        ]

    @app.post("/answer", response_model=AnswerOut)
    def answer(body: AnswerRequest) -> AnswerOut:
        retriever = Retriever(
            store,
            bm25,
            embedder,
            reranker=_reranker_for(body.strategy),
            strategy=body.strategy,
            top_k=body.top_k,
            rerank_top_n=settings.rerank_top_n,
            tracer=tracer,
        )
        retrieved = retriever.retrieve(body.question)
        generated = Generator(llm, tracer=tracer).answer(body.question, retrieved)
        return AnswerOut(
            text=generated.text,
            citations=[c.to_label() for c in generated.citations],
            confidence=generated.confidence,
            grounded=bool(generated.payload.get("grounded", False)),
        )

    return app


# region app_factory
def app_factory() -> FastAPI:
    """ASGI factory for `uvicorn coderag.api.app:app_factory --factory` (reads Settings from env)."""
    return create_app(Settings())
