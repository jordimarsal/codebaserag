# AGENTS.md — Navigation map for AI agents

> This file is the **entry point** for any agent working in this repository.
> It is NOT a rule bible — it is a **map**. Read only what you need, when you need it (progressive disclosure).

---

## 1. Before you start (mandatory)

1. Run `harness/init.sh` and verify it finishes without errors. If it fails, **stop** and fix the environment before touching code.
2. Read `harness/progress/current.md` to understand where the last session left off.
3. Read `harness/feature_list.json`. ALL features follow **Spec Driven Development** — see §4 of this file.
4. Read `docs/specs.md` before touching any spec or feature.

## 2. Repository map

| File / folder               | What it contains                                                           | When to read it                  |
|-----------------------------|-----------------------------------------------------------------------------|----------------------------------|
| `harness/feature_list.json`         | Feature list with status (`pending` / `spec_ready` / `in_progress` / `done` / `blocked`) | Always, at start                 |
| `harness/progress/current.md`       | Current session state                                                       | Always, at start                 |
| `harness/progress/history.md`       | Append-only log of previous sessions                                        | When you need historical context |
| `harness/specs/<feature>/`          | `requirements.md` + `design.md` + `tasks.md` (Kiro-style)                  | Before implementing any feature  |
| `docs/architecture.md`      | What "doing a good job" means in this project                               | Before implementing              |
| `docs/conventions.md`       | Style rules, naming, structure                                              | Before writing code              |
| `docs/specs.md`             | SDD process: EARS notation, 3 files, human approval gate                   | Before writing or reading a spec |
| `docs/verification.md`      | How to verify your work works (including requirement traceability)          | Before marking a task as `done`  |
| `harness/CHECKPOINTS.md`            | Objective criteria for "correct final state"                                | For self-assessment              |
| `.opencode/agent/`           | Subagent definitions (`leader`, `spec-author`, `implementer`, `reviewer`)   | If you orchestrate work          |
| `src/`                      | Application code                                                            | To implement                     |
| `tests/`                    | Automated tests                                                             | To verify                        |
| `docs/architecture-options.md` | Architecture pattern catalog (module: architecture-catalog) | When filling design.md Architectural Decisions |
| `docs/iteration-protocol.md`   | Adaptive iteration + adversarial review protocol (module: iterative-refinement) | During implementer refinement rounds |
| `harness/tools/`               | Module tools: `audit-security.sh`, `bench.sh`, `scan.py` (if present) | On review (audits) or session start (scan) |
| `harness/decisions/`           | ADRs worth remembering beyond a feature (if present) | Before proposing a new architectural decision |
| `harness/wekan.json`           | Wekan ticket-mirror config (if present) | When syncing workflow state to the board |

> Module files are conditional: if a file above exists, its module was installed —
> follow it. If absent, ignore references to it.

## 3. Hard rules (non-negotiable)

- **One feature at a time.** Do not mix changes from multiple tasks in the same session.
- **Do not mark a task `done` without green tests.** Run `harness/init.sh` and ensure the test block passes 100%.
- **Do not skip the spec phase.** Every feature must go through `spec-author` and obtain human approval before touching code.
- **Do not skip the human approval gate.** The leader stops the flow at `spec_ready` and waits.
- **Document what you do** in `harness/progress/current.md` while working, not at the end.
- **Leave the repository clean** before closing the session (see §5).
- **If you don't know something, look in `docs/`** before inventing it.

## 4. Workflow (SDD — mandatory for all features)

```
pending → [spec-author] → spec_ready → ⏈ HUMAN → in_progress → [implementer → reviewer] → done
```

1. The leader detects the first `pending` feature.
2. The leader dispatches `spec-author`, who creates `harness/specs/<name>/{requirements,design,tasks}.md` and marks status as `spec_ready`.
3. **Pause.** The human reads the spec at `harness/specs/<name>/` and approves (or requests changes).
4. Once approved, the leader changes status to `in_progress` and dispatches `implementer`.
5. The implementer executes `tasks.md` one by one, marking them `[x]`.
6. The reviewer verifies traceability `R<n>` ↔ test and task completion; approves or rejects.
7. If approved, the implementer marks `done` and moves the summary to `harness/progress/history.md`.

### Parallelism

When `"parallel": true` in `harness/feature_list.json` project config:
- Independent tasks (no `depends_on`) can be dispatched to separate implementer subagents simultaneously.
- Only 1 feature may be `in_progress` at a time.

When `"parallel": false` (default): sequential execution, one task at a time.

## 5. Session lifecycle (closure)

Before finishing:

1. Run `harness/init.sh` — all green.
2. If the task is done: mark `status: "done"` in `harness/feature_list.json`.
3. Move the summary from `harness/progress/current.md` to the end of `harness/progress/history.md`.
4. Clear `harness/progress/current.md` leaving only the template.
5. Do not leave temporary files, debug prints, or context-free TODOs.

## 6. If you get stuck

- Re-read the relevant section of `docs/`.
- If a tool doesn't behave as expected, **do not invent a workaround**: document the block in `harness/progress/current.md` and stop the session.
