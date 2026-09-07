# Requirements: phase2-eval-harness

Scope: build the eval harness with a versioned golden dataset and **deterministic
retrieval metrics** (recall@5, MRR, nDCG). This phase covers only the retrieval layer;
fidelity/quality (citation + LLM-as-judge) layers are later phases. The harness must be
runnable from pytest and from the CLI `eval` command.

## R1
The system shall load the golden dataset from `evals/golden/*.yaml`, where each entry has
`question`, `expected_files`, `answer_contains`, and `repo` fields.

## R2
The golden dataset v1 shall contain at least 40 entries, each derived from the project's own
repositories and tagged with a `repo` label.

## R3
When the retrieval eval runs, the system shall embed each `question` with the `Embedder` port
and retrieve the top-k chunks from the `VectorStore` port.

## R4
The system shall map each retrieved chunk back to its source file path to produce an ordered
list of retrieved files per question.

## R5
The system shall compute **recall@k** as the fraction of `expected_files` present in the top-k
retrieved files.

## R6
The system shall compute **MRR** (Mean Reciprocal Rank) as the mean over entries of the
reciprocal rank of the first retrieved file that is in `expected_files`.

## R7
The system shall compute **nDCG@k** over the retrieved ranking using binary relevance
(`expected_files` = relevant).

## R8
The core metric functions (recall@k, MRR, nDCG@k) shall be **pure functions with no I/O**,
unit-testable independently of any store or embedder.

## R9
The harness shall aggregate per-entry metrics into a summary report (mean recall@k, mean MRR,
mean nDCG@k) and write it as a versioned artifact (markdown table).

## R10
When comparing to a stored baseline, the harness shall fail (non-zero exit / assertion) if the
mean recall@k drops below the baseline, unless an explicit ADR override is supplied.

## R11
The retrieval eval shall be executable from `coderag eval` (CLI) and as a pytest suite marked
`@pytest.mark.eval` so it runs in CI on every PR.

## R12
The retrieval metric computation shall not require any LLM or network call; only the
`VectorStore`/`Embedder` ports are used, and the metric unit tests run with no external
services.

## R13
The current baseline metrics shall be documented in `README.md` as a table (current vs baseline).
