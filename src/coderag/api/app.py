from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from coderag.api.models import (
    AnswerOut,
    AnswerRequest,
    ChunkOut,
    ErrorOut,
    IngestRequest,
    QueryRequest,
)
from coderag.compose import build_llm, build_retriever, build_store
from coderag.config import Settings
from coderag.generation.generator import GenerationError, Generator
from coderag.ingest.pipeline import IngestError, run_ingest
from coderag.llm.ollama_embedder import EmbedderError
from coderag.observability import build_tracer
from coderag.retrieval.retriever import RetrievalError
from coderag.stores.errors import StoreError


# region create_app
def create_app(settings: Settings) -> FastAPI:
    app = FastAPI(title="codebaserag", version="0.1.0")

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
        store, embedder = build_store(settings)
        indexed = run_ingest(Path(body.repo), embedder, store, chunk_size=settings.chunk_size)
        return {"indexed": indexed}

    @app.post("/query", response_model=list[ChunkOut])
    def query(body: QueryRequest) -> list[ChunkOut]:
        tracer = build_tracer(settings)
        retriever = build_retriever(
            settings,
            backend=settings.vector_store,
            repo=Path(settings.repo),
            strategy=body.strategy,
            top_k=body.top_k,
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
        tracer = build_tracer(settings)
        retriever = build_retriever(
            settings,
            backend=settings.vector_store,
            repo=Path(settings.repo),
            strategy=body.strategy,
            top_k=body.top_k,
            tracer=tracer,
        )
        retrieved = retriever.retrieve(body.question)
        generated = Generator(build_llm(settings), tracer=tracer).answer(body.question, retrieved)
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
