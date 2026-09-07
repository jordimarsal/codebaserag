FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY evals ./evals

RUN pip install --no-cache-dir \
    .[pgvector, qdrant, embeddings, rerank, bm25, observability, llm]

EXPOSE 8000

# Index the mounted codebase, then serve the API.
CMD ["sh", "-c", "coderag ingest /repo && uvicorn coderag.api.app:app_factory --factory --host 0.0.0.0 --port 8000"]
