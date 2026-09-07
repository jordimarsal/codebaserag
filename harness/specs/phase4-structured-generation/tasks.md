# Tasks: phase4-structured-generation

- [x] T1: Extend `src/coderag/llm/ports.py` `LlmClient` with `generate_structured(prompt, schema) -> dict`.
      depends_on: (none)
      refs: R2, R3

- [x] T2: Create `src/coderag/llm/litellm_client.py` — `LitellmClient` (litellm extra) implementing
      `generate` + `generate_structured` via JSON-schema `response_format`/function calling.
      depends_on: T1
      refs: R1, R2, R11

- [x] T3: Create `src/coderag/llm/fake.py` — `FakeLlmClient` returning scripted structured answers
      (registry keyed by question), incl. one ungrounded case for tests.
      depends_on: T1
      refs: R9, R10

- [x] T4: Add `payload: dict = field(default_factory=dict)` to `Answer` in `src/coderag/types.py`.
      depends_on: (none)
      refs: R8

- [x] T5: Create `src/coderag/generation/generator.py` — `Generator` + `GenerationError` + `CiteSpec`;
      build prompt, call `generate_structured`, parse `Answer`, grounded-check, confidence.
      depends_on: T1, T3, T4
      refs: R4, R5, R6, R7, R12

- [x] T6: Create `src/coderag/generation/__init__.py` exporting `Generator`, `GenerationError`.
      depends_on: T5
      refs: R2

- [x] T7: Add `llm_model`, `llm_backend` to `src/coderag/config.py`.
      depends_on: (none)
      refs: R11

- [x] T8: Add `run_generation_eval` + `GenerationReport` to `evals/harness.py` (grounding/schema/contains rates).
      depends_on: T5
      refs: R9, R12

- [x] T9: Wire CLI: add `answer` command and `eval --kind {retrieval,generation}`; build `Generator`
      from `Settings` + `LlmClient`.
      depends_on: T2, T5, T7, T8
      refs: R9, R11

- [x] T10: Write `tests/test_generator.py` (grounding/schema/confidence with `FakeLlmClient`) and
      `tests/test_llm.py` (port conformance). Run gates; update `harness/progress/current.md`.
      depends_on: T3, T5, T8
      refs: R9, R10, R12
