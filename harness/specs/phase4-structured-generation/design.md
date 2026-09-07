# Design: phase4-structured-generation

## Files to create or modify

- `src/coderag/llm/ports.py` — add `generate_structured(prompt, schema) -> dict` to `LlmClient`.
- `src/coderag/llm/litellm_client.py` — `LitellmClient` implementing `LlmClient` (litellm extra),
  using `response_format={"type":"json_schema",...}` or function-calling to constrain output.
- `src/coderag/llm/fake.py` — `FakeLlmClient` returning scripted structured answers (offline eval).
- `src/coderag/generation/generator.py` — `Generator` orchestrator: builds a prompt from the
  question + retrieved chunks, calls `LlmClient.generate_structured`, parses into `Answer`,
  verifies citation grounding, computes confidence.
- `src/coderag/generation/__init__.py` — exports `Generator`, `GenerationError`.
- `src/coderag/types.py` — add `payload: dict = field(default_factory=dict)` to `Answer` (default keeps
  existing uses valid).
- `src/coderag/config.py` — add `llm_model: str = "gpt-4o-mini"` and `llm_backend: str = "litellm"`.
- `evals/harness.py` — add `run_generation_eval(entries, retriever, generator, *, top_k) -> GenerationReport`
  (grounding_rate, schema_rate, contains_rate) reusing `answer_contains` logic + new grounding check.
- `src/coderag/cli.py` — add `answer` command (retrieve + generate + print answer with citations);
  extend `eval` with `--kind {retrieval,generation}`.
- `evals/golden/codebaserag.yaml` — optional: reuse as-is; `answer_contains` already present per entry.
- `tests/test_generator.py` — grounding/schema/confidence with `FakeLlmClient` (no network).
- `tests/test_llm.py` — `LlmClient` port conformance (fake + optional live skip).

## Public signatures

```python
# llm/ports.py
@runtime_checkable
class LlmClient(Protocol):
    def generate(self, prompt: str) -> str: ...
    def generate_structured(self, prompt: str, schema: dict) -> dict: ...
    def model_name(self) -> str: ...

# generation/generator.py
class GenerationError(Exception): ...

@dataclass
class CiteSpec:
    path: str
    line_start: int
    line_end: int

class Generator:
    def __init__(self, llm: LlmClient, schema: dict | None = None) -> None
    def answer(self, question: str, retrieved: list[RetrievalResult]) -> Answer: ...
    def _grounded(self, cites: list[CiteSpec], retrieved: list[RetrievalResult]) -> bool: ...

# evals/harness.py
@dataclass
class GenerationReport:
    entries: list[GenEntryResult]
    grounding_rate: float
    schema_rate: float
    contains_rate: float
    top_k: int
```

## Answer schema (default)

```json
{
  "type": "object",
  "properties": {
    "answer":   {"type": "string"},
    "citations": {"type": "array", "items": {
      "type": "object",
      "properties": {"path": {"type": "string"},
                     "line_start": {"type": "integer"},
                     "line_end": {"type": "integer"}},
      "required": ["path", "line_start", "line_end"]}},
    "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0}
  },
  "required": ["answer", "citations"]
}
```

## Grounding check (R5)

`Generator._grounded` builds a set of `(path, line_start, line_end)` keys from `retrieved` and
requires every `CiteSpec` to match one of them (exact key match; ranges equal the chunk's). If any
citation is ungrounded, `answer(...)` sets a `grounded=False` flag and `GenerationError` is raised
only when the caller requests strict mode; batch eval records the failure instead (R12).

## Confidence (R7)

`confidence = clamp(mean(retrieval_score of cited chunks), 0, 1)` when grounded, else `0.0`; the
existing `Answer.confidence_verdict` ("high"/"medium"/"low") is reused.

## Discarded alternatives

- **Free-form text + regex citations.** Rejected: unreproducible and easy to hallucinate;
  schema-constrained output plus an exact grounding check is what the brief requires.
- **Rely on model self-citation.** Rejected: models cite paths that were not retrieved; grounding is
  enforced post-hoc against the retrieval set.
- **Separate LLM per citation.** Rejected: one structured call returning `answer`+`citations` is
  cheaper and matches the schema-driven design.

## Eval integration (R9/R10/R12)

`FakeLlmClient` returns a scripted dict per question (looked up by an in-test registry) so the
golden set can be driven offline. One scripted answer is intentionally ungrounded to exercise R5/R12.
`run_generation_eval` mirrors `run_retrieval_eval`: iterates entries, builds `retriever(q)`,
calls `generator.answer`, and accumulates grounding/schema/contains outcomes into `GenerationReport`.
