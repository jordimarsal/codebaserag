from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import typer
from evals.dataset import EvalError, load_golden
from evals.embedder import HashEmbedder
from evals.experiments.hybrid_vs_dense import run_experiment
from evals.harness import (
    assert_not_regressed,
    load_baseline,
    run_generation_eval,
    run_retrieval_eval,
    save_baseline,
)

from coderag import __version__
from coderag.compose import build_embedder, build_llm, build_retriever
from coderag.config import Settings
from coderag.generation.generator import GenerationError, Generator
from coderag.ingest.pipeline import IngestError, run_ingest
from coderag.llm.ollama_embedder import EmbedderError
from coderag.observability import build_tracer
from coderag.retrieval.retriever import RetrievalError
from coderag.stores.errors import StoreError
from coderag.stores.pgvector import PgvectorStore
from coderag.stores.qdrant import QdrantVectorStore

if TYPE_CHECKING:
    from coderag.types import RetrievalResult

app = typer.Typer(help="codebase-rag: hexagonal RAG over your own code.")


@app.command()
def version() -> None:
    """Print the installed version."""
    typer.echo(__version__)


@app.command()
def ingest(
    repo: Path = typer.Argument(..., exists=True, file_okay=False, dir_okay=True),  # noqa: B008
    store: str = typer.Option("pgvector", help="Vector store backend: pgvector | qdrant."),
    strategy: str = typer.Option("fixed", help="Chunking strategy."),
    top_k: int = typer.Option(5, help="Top-k retrieval size (informational)."),
) -> None:
    """Index a local repository into the vector store."""
    settings = Settings()
    embedder = build_embedder(settings)
    dim = embedder.dim()
    if store == "qdrant":
        vector_store: VectorStore = QdrantVectorStore(
            url=settings.qdrant_url,
            collection=settings.qdrant_collection,
            dim=dim,
            distance=settings.qdrant_distance,
        )
    else:
        vector_store = PgvectorStore(dsn=settings.database_dsn, dim=dim)
    try:
        indexed = run_ingest(
            repo, embedder, vector_store, strategy=strategy, chunk_size=settings.chunk_size
        )
    except (IngestError, StoreError, EmbedderError) as exc:
        typer.secho(f"ingest failed: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"indexed {indexed} chunks from {repo} (top_k={top_k})")


@app.command()
def query(
    question: str = typer.Argument(..., help="Natural-language question."),
    top_k: int = typer.Option(5, help="Number of chunks to retrieve."),
    strategy: str = typer.Option("dense", help="dense | hybrid | hybrid+rerank."),
    store: str = typer.Option("pgvector", help="Backend: pgvector | memory."),
    repo: Path = typer.Option(Path("."), help="Repo to index (memory backend only)."),  # noqa: B008
) -> None:
    """Retrieve the top-k chunks for a question (naive, no generation yet)."""
    settings = Settings()
    try:
        retriever = build_retriever(
            settings, backend=store, repo=repo, strategy=strategy, top_k=top_k
        )
        results: list[RetrievalResult] = retriever.retrieve(question)
    except (RetrievalError, StoreError, EmbedderError, IngestError) as exc:
        typer.secho(f"query failed: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    if not results:
        typer.echo("no results")
        return
    for rank, result in enumerate(results, start=1):
        chunk = result.chunk
        typer.echo(
            f"{rank}. score={result.score:.3f} {chunk.path}:{chunk.line_start}-{chunk.line_end}"
        )


@app.command()
def answer(
    question: str = typer.Argument(..., help="Natural-language question."),
    top_k: int = typer.Option(5, help="Number of chunks to retrieve."),
    strategy: str = typer.Option("dense", help="dense | hybrid | hybrid+rerank."),
    store: str = typer.Option("pgvector", help="Backend: pgvector | memory."),
    repo: Path = typer.Option(Path("."), help="Repo to index (memory backend only)."),  # noqa: B008
) -> None:
    """Retrieve context and generate a grounded, structured answer with citations."""
    settings = Settings()
    try:
        tracer = build_tracer(settings)
        retriever = build_retriever(
            settings, backend=store, repo=repo, strategy=strategy, top_k=top_k, tracer=tracer
        )
        retrieved = retriever.retrieve(question)
        generated = Generator(build_llm(settings), tracer=tracer).answer(question, retrieved)
    except (RetrievalError, GenerationError, StoreError, EmbedderError, IngestError) as exc:
        typer.secho(f"answer failed: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(generated.text)
    for citation in generated.citations:
        typer.echo(f"  - {citation.to_label()}")


@app.command()
def eval(
    golden_dir: Path = typer.Option(  # noqa: B008
        Path("evals/golden"), help="Golden dataset directory."
    ),
    top_k: int = typer.Option(5, help="Retrieval cutoff k for recall/NDCG."),
    store: str = typer.Option("memory", help="Backend: pgvector | memory."),
    repo: Path = typer.Option(Path("."), help="Repo to index (memory backend only)."),  # noqa: B008
    strategy: str = typer.Option("dense", help="dense | hybrid | hybrid+rerank."),
    update_baseline: bool = typer.Option(False, help="Write a new evals/baseline.json."),
    adr: str = typer.Option(None, help="ADR reference to override a regression."),
    baseline_path: Path = typer.Option(Path("evals/baseline.json")),  # noqa: B008
    experiment: bool = typer.Option(False, help="Run dense/hybrid/hybrid+rerank and write the table."),
    kind: str = typer.Option("retrieval", help="retrieval | generation."),
) -> None:
    """Run the eval harness (deterministic recall/MRR/nDCG or grounded generation)."""
    settings = Settings()
    entries = load_golden(golden_dir)

    if experiment:
        typer.echo(run_experiment())
        return

    try:
        retriever = build_retriever(
            settings, backend=store, repo=repo, strategy=strategy, top_k=top_k
        )
        if kind == "generation":
            generator = Generator(build_llm(settings))
            report = run_generation_eval(entries, retriever.retrieve, generator.answer, top_k=top_k)
        else:
            report = run_retrieval_eval(entries, retriever.retrieve, top_k=top_k)
    except (EvalError, RetrievalError, GenerationError, IngestError, StoreError, EmbedderError) as exc:
        typer.secho(f"eval failed: {exc}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(report.to_markdown())
    if kind == "retrieval" and update_baseline:
        save_baseline(baseline_path, report)
        typer.echo(f"baseline written to {baseline_path}")
        return
    if kind == "retrieval":
        baseline = load_baseline(baseline_path)
        try:
            assert_not_regressed(report, baseline, adr=adr)
        except AssertionError as exc:
            typer.secho(str(exc), fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1) from exc


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="Bind host."),
    port: int = typer.Option(8000, help="Bind port."),
) -> None:
    """Serve the FastAPI app (compose ingest/retrieve/generate) via uvicorn."""
    import uvicorn

    from coderag.api.app import create_app

    uvicorn.run(create_app(Settings()), host=host, port=port)


if __name__ == "__main__":
    app()
