# Project Wiki

Working knowledge for building production agentic systems on the FDE scaffold (FastAPI + SQLite backend, React + TypeScript + Vite frontend).

Three layers. Do not mix them:

| Layer | Path | Owns |
|---|---|---|
| Engagement method | [mental-model.md](mental-model.md), `1-frame/` … `6-land/` | When in the job |
| Decision catalog | [catalog/](catalog/) | What to decide — one card, one family |
| Implementation skills | [`.cursor/skills/`](../.cursor/skills/README.md) | How to implement, after cards are filled |

**Most catalog cards are placeholders.** A stub is not guidance. Fill them one at a time. Do not invent a missing card.

## Start here

1. **[mental-model.md](mental-model.md)** — the spine (six phases, inner loop)
2. **[catalog/README.md](catalog/README.md)** — the decision index
3. The phase folder for method and long-form pages

## Phases

| Phase | Method that stays here | Decisions that moved to catalog |
|---|---|---|
| [1 · Frame](1-frame/) | Consulting craft; long-form discovery, qualification, scoping | [Engagement cards](catalog/README.md#engagement) |
| [2 · Design](2-design/) | Pattern ladder, diagram notation | [Architecture](catalog/README.md#architecture), [Retrieval](catalog/README.md#retrieval) |
| [3 · Build](3-build/) | Three workflow shapes | [Data](catalog/README.md#data), [Tools](catalog/README.md#tools), [Runtime](catalog/README.md#runtime), [Surfaces](catalog/README.md#surfaces) |
| 4 · Prove | *(no folder — empty stubs removed)* | [Evals](catalog/README.md#evals) |
| 5 · Operate | *(no folder — empty stubs removed)* | [Production](catalog/README.md#production) |
| [6 · Land](6-land/) | Demo and handoff | — |

## Reference

| Page | Covers |
|---|---|
| [reference/](reference/) | This project: [setup](reference/environment-setup.md), [architecture](reference/architecture.md), [coding standards](reference/coding-standards.md), [troubleshooting](reference/troubleshooting.md) |
| [diagrams/](diagrams/) | Mermaid sources — the version we trust; a Figma board is a rendering of it |

## Agent skills

Rules the agent applies while working. Catalog cards are the reasoning. Keep a skill in sync with its cards — if a rule changes, edit both. **Do not add placeholder `SKILL.md` files.** Planned skills are listed in [`.cursor/skills/README.md`](../.cursor/skills/README.md).

| Skill | Status | Catalog / wiki |
|---|---|---|
| [coding-standards](../.cursor/skills/coding-standards/SKILL.md) | **Built** | [reference/coding-standards.md](reference/coding-standards.md) |
| [fde-engagement](../.cursor/skills/fde-engagement/SKILL.md) | **Built** | [Engagement](catalog/README.md#engagement), [1-frame](1-frame/), [6-land](6-land/) |
| [agentic-system-design](../.cursor/skills/agentic-system-design/SKILL.md) | **Built** | [Architecture](catalog/README.md#architecture), [2-design](2-design/) |
| [figma-draw-standards](../.cursor/skills/figma-draw-standards/SKILL.md) | **Built** | [2-design/figma-draw-standards.md](2-design/figma-draw-standards.md) |
| [agentic-project-init](../.cursor/skills/agentic-project-init/SKILL.md) | **Built** | Template [templates/agentic-project/](../templates/agentic-project/README.md), created with `templates/new_project.py` |
| [agentic-project-planning](../.cursor/skills/agentic-project-planning/SKILL.md) | **Built** | [cashflow-copilot/docs/](../cashflow-copilot/docs/implementation_plan.md); catalog lives in the skill folder |
| `retrieval-and-memory` | Planned | [Retrieval](catalog/README.md#retrieval) |
| `workflow-patterns` | Planned | [3-build/workflow-patterns.md](3-build/workflow-patterns.md) |
| `api-and-integration` | Planned | [Data](catalog/README.md#data) |
| `claude-integration` | Planned | [Tools](catalog/README.md#tools), [Runtime](catalog/README.md#runtime) |
| `testing-and-evals` | Planned | [Evals](catalog/README.md#evals) |
| `production-readiness` | Planned | [Production](catalog/README.md#production) |
| `orient-scaffold` | Planned | [context/repo-map.md](../context/repo-map.md) |

Cursor selects by description match. Overlapping descriptions hurt. Each skill owns a **moment**, not a topic.

| Layer | Path | Loads |
|---|---|---|
| Always-on rules | [`.cursor/rules/engagement.mdc`](../.cursor/rules/engagement.mdc) | Every prompt — **overrides skills on conflict**, so it stays short |
| Session context | [`context/repo-map.md`](../context/repo-map.md), [`context/session-notes.md`](../context/session-notes.md) | Read on demand; `session-notes` is a live scratchpad |
| Rehearsal | [`practice/`](../practice/) | Not loaded — timed drills against the scaffold |

## Retired names

Do not create these under phase folders. They were planned, then replaced by catalog cards:

`decision-design.md` · `trigger-design.md` · `context-and-memory.md` · `data-model.md` · `api-design.md` · `integration-patterns.md` · `claude-integration.md` (wiki page) · `error-handling.md` · `frontend.md` · phase folders `4-prove/` and `5-operate/`

## Conventions

Write down a fact here when it cost time to discover. A page earns its place if it stops someone re-debugging something we already understand.

Record what was **verified**, not what should be true. If a command was run and its output observed, say so. If something is an assumption, label it as one.

When a fact changes, edit the existing page rather than appending a correction.

Prefer concrete commands and exact error strings over prose descriptions.

Architecture diagrams are text. The Mermaid source lives in [diagrams/](diagrams/). Diagram notation is not the product design system — see [2-design/figma-draw-standards.md](2-design/figma-draw-standards.md).
