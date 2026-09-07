# Requirements: phase5-observability

Scope: per-query observability so every RAG step (retrieval, rerank, generation) is traceable with
its inputs, outputs, latency, and cost. Tracing goes through a port so the core never imports a
concrete observability SDK; a Langfuse adapter ships traces to a self-hosted instance, and an
offline tracer keeps tests/eval deterministic.

## R1
The system shall emit one **trace per user query** that captures the retrieval, (optional) rerank,
and generation steps.

## R2
Tracing shall use an observability `Tracer` port; the core (retriever, generator) shall depend only
on the port, never on a concrete tracing SDK.

## R3
The retrieval step shall record: strategy, `top_k`, candidate count, latency (ms), and the returned
chunk paths.

## R4
The rerank step (when used) shall record: input candidate count, output count, and latency (ms).

## R5
The generation step shall record: prompt size (chars), response size (chars), model name, latency
(ms), and cost (when the backend reports it).

## R6
A Langfuse adapter shall implement `Tracer` and send traces to a self-hosted Langfuse (host + keys
from config).

## R7
An offline `InMemoryTracer` (and a `NoOpTracer`) shall allow tracing without a live backend, so eval
and tests run deterministically (R10).

## R8
Tracing shall be **optional and non-blocking**: any failure inside a tracer shall be swallowed and
must not break retrieval or generation.

## R9
Tracing shall be toggleable via `Settings` (`observability_backend` / enabled flag) without code
changes to the calling layer.

## R10
The `InMemoryTracer` shall expose the collected spans (name, attributes, latency) so tests can assert
on them.

## R11
When `observability_backend` is not `langfuse`, the system shall default to `NoOpTracer` (no spans
emitted) so the default path stays zero-dependency.
