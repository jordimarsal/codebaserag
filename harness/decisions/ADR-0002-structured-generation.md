# ADR-0002: Structured generation with grounded citations

- **Date:** 2026-09-07
- **Status:** accepted
- **Feature:** phase4-structured-generation

## Context

Free-form LLM answers over retrieved code are easy to hallucinate: the model cites files or line
ranges that were never retrieved, and outputs are not machine-checkable. We need answers that are
schema-constrained and provably tied to the retrieval set.

## Decision

Generation goes through the `LlmClient` port extended with `generate_structured(prompt, schema)`; the
`Generator` builds a prompt from the question + retrieved chunks, requests a JSON object
(`answer` + `citations[]` + `confidence`), and parses it into an `Answer`. Every citation must reference
a chunk present in the retrieval result set for that query (**grounding**); ungrounded citations drop
confidence to 0 and (in strict mode) raise `GenerationError`. Confidence is the mean retrieval score of
the cited chunks, clamped to [0, 1].

## Alternatives considered

- **Free-form text + regex-extracted citations.** Rejected: unreproducible and trivially hallucinated.
- **Model self-citation trusted as-is.** Rejected: models cite paths outside the retrieved set; we
  enforce grounding post-hoc against the retrieval set instead.

## Consequences

Cheap to reverse. `Answer` gained an optional `payload` field (default, backward compatible). The eval
harness gained `run_generation_eval` reporting grounding / schema-conformance / answer-contains rates,
so citation validity is now a tested property, not a hope.
