# Requirements: phase7-api-compose

Scope: a FastAPI service that composes the already-built pieces — ingest, hybrid retrieval, and
structured generation — behind REST endpoints, configured entirely via `Settings`. The offline eval
suite is the contract: the API's retrieval path must return the same results as the core `Retriever`.

## R1
The system shall expose a FastAPI application that composes ingest, hybrid retrieval, and structured
generation (no new retrieval/generation logic — it reuses `Retriever` + `Generator`).

## R2
The service shall provide at least: `POST /ingest` (index a repo path), `POST /query` (return the
top-k retrieved chunks for a question), and `POST /answer` (return a grounded `Answer` with citations).

## R3
Endpoints shall depend only on the existing ports/retriever/generator; the API layer contains no
business logic beyond orchestration and I/O mapping.

## R4
The backend (`pgvector` | `qdrant` | `memory`), retrieval `strategy`, and LLM `backend` shall be
selected via `Settings` so the service is configured without code changes.

## R5
Request and response bodies shall be validated with Pydantic models; malformed input returns 422.

## R6
Retrieval and generation shall be traced through the existing `Tracer` port (observability reuse).

## R7
Errors shall map to proper HTTP status codes (400/422/500) and never crash the server with an
unhandled exception; `RetrievalError`/`GenerationError`/`StoreError` become 4xx/5xx with a message.

## R8
The eval suite is the contract: a test shall drive `POST /query` through the API and assert the
returned chunk paths equal the core `Retriever` output for the same question (determinism).

## R9
The service shall be offline-testable: `fastapi.testclient.TestClient` with `memory` backend + `fake`
LLM runs all endpoints without external services.

## R10
A `serve` CLI command shall start the service via `uvicorn` using `Settings` (host/port configurable).
