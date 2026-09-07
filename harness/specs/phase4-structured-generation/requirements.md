# Requirements: phase4-structured-generation

Scope: turn retrieval into grounded, structured answers. The generator calls an LLM through the
existing `LlmClient` port, constrains output to a caller-supplied JSON schema, and attaches
citations that must be grounded in the retrieved chunk set. The eval must verify grounding and
schema conformance deterministically (offline-capable via a fake LLM).

## R1
The system shall generate an answer as a JSON object that conforms to a caller-supplied JSON
schema (structured/constrained generation), not free-form prose.

## R2
Generation shall use an `LlmClient` implementing the existing `LlmClient` port; the core shall
depend only on the port, never on a concrete LLM SDK.

## R3
The `LlmClient` port shall expose a structured-generation method `generate_structured(prompt, schema) -> dict`
in addition to `generate(prompt) -> str`.

## R4
Every generated `Answer` shall carry citations, each referencing a retrieved chunk by `path` and
line range (`line_start`/`line_end`).

## R5
Citations shall be **grounded**: every cited chunk must belong to the retrieval result set used for
that query. A citation to a path/line range not in the retrieved set is rejected and the answer is
flagged (R5/R7).

## R6
The generator shall raise `GenerationError` when the model output is empty, fails JSON parsing, or
fails schema validation.

## R7
The generator shall attach a `confidence`/`confidence_verdict` to the `Answer`, derived from the
retrieval scores of the cited chunks and the schema/grounding check (heuristic, deterministic).

## R8
The `Answer` dataclass shall optionally carry the raw structured payload (`payload: dict`).

## R9
The eval harness shall run generation over the golden dataset and report a **grounding rate**
(fraction of answers with all citations grounded), a **schema-conformance rate**, and an
**answer-contains rate** (existing `answer_contains` strings present in the answer text).

## R10
The eval shall be offline/CI-safe: a port-compliant `FakeLlmClient` returns scripted structured
answers (including an intentionally ungrounded one) so grounding and schema checks are testable
without a live model.

## R11
The LLM backend shall be configurable (model name, backend selection) via `Settings` so it can be
switched without code changes to the calling layer.

## R12
Ungrounded or schema-invalid outputs shall not crash batch eval; they are recorded as failures in
the report so regression guards can act on them.
