# Requirements: phase1-ingest-pgvector

Scope: implement ingestion (read → chunk → embed → store) and a naive dense query
over the default pgvector store, exposed through the typer CLI. This phase does NOT
include hybrid search, reranking, or structured generation (those are later phases).

## R1
When the user invokes `ingest <repo> [--store pgvector]`, the system shall read all
files under `<repo>` whose extension is `.md`, `.py`, `.toml`, or `.yaml`.

## R2
When reading files during ingestion, the system shall skip any path matched by the
repository's `.gitignore` and any path under a `.git` directory.

## R3
When files are read, the system shall assign each chunk a `Language` derived from its
extension (`.py`→PYTHON, `.md`→MARKDOWN, `.toml`→TOML, `.yaml`→YAML, else UNKNOWN).

## R4
When files are chunked, the system shall support at least the `fixed` chunking strategy
that splits text into non-overlapping windows of a configurable `size` (lines), tagging
each chunk with `line_start` and `line_end`.

## R5
The system shall compute a stable content `hash` (e.g. sha256) per chunk and store it
in the `Chunk.hash` field.

## R6
When chunks are produced, the system shall embed their `text` via the `Embedder` port
and persist the `(Chunk, vector)` pairs through the `VectorStore` port.

## R7
The system shall provide a `PgvectorStore` adapter implementing `VectorStore` that
stores chunks and dense vectors in a Postgres + pgvector table and returns the
top-k nearest chunks by cosine/inner-product distance.

## R8
When the user invokes `query <question> [--top-k 5]`, the system shall embed the
question with the same `Embedder`, retrieve the top-k chunks from the store, and print
them (naive, free-text answer is out of scope for this phase).

## R9
The `ingest` command shall index a real repository of moderate size in under 2 minutes.

## R10
The core ingestion logic (readers, chunkers, pipeline orchestration) shall not import
any adapter (pgvector, psycopg, ollama, anthropic, openai, langfuse); it shall depend
only on the `Protocol` ports.

## R11
When an embedding or store error occurs, the system shall raise a specific domain
exception (not a bare `Exception`) and shall not abort the whole ingestion silently.

## R12
The system shall be configurable via environment variables / `.env` for the database
DSN and the embedder endpoint, with sensible defaults for local development.
