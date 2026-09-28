# Agent skills

Cursor loads a skill when its `SKILL.md` description matches the task. **Only directories with a real `SKILL.md` exist here.** Do not add placeholder `SKILL.md` files — an empty skill still gets selected and will confuse the agent.

Fill catalog cards first. Write the skill after the cards it covers have been used once and the rules are obvious.

## Built

| Skill | Use when | Wiki |
|---|---|---|
| [coding-standards](coding-standards/SKILL.md) | Writing or reviewing any application code: naming, docstrings, functions, ABCs and OOP, tests (fixture scripts exempt) | [wiki/reference/coding-standards.md](../../wiki/reference/coding-standards.md) |
| [fde-engagement](fde-engagement/SKILL.md) | Start, unclear scope, blocked, close | [wiki/1-frame/](../../wiki/1-frame/), [wiki/6-land/](../../wiki/6-land/), [wiki/catalog/](../../wiki/catalog/README.md#engagement) |
| [agentic-system-design](agentic-system-design/SKILL.md) | Designing or reviewing an agent | [wiki/2-design/agentic-system-design.md](../../wiki/2-design/agentic-system-design.md) |
| [figma-draw-standards](figma-draw-standards/SKILL.md) | Drawing or generating a diagram | [wiki/2-design/figma-draw-standards.md](../../wiki/2-design/figma-draw-standards.md) |
| [agentic-project-init](agentic-project-init/SKILL.md) | Creating a project in about two minutes: `python3 templates/new_project.py <name>` copies the tested template (backend, frontend, `.env`, `data/raw` + `data/processed`, providers, `BaseAgent`, database, RAG, memory, MCP, Docker, `scripts/check.sh`) | Template: [templates/agentic-project/](../../templates/agentic-project/README.md) |
| [agentic-project-planning](agentic-project-planning/SKILL.md) | Breaking a project into plan documents, phases, and exit gates | Reference: [cashflow-copilot/docs/](../../cashflow-copilot/docs/implementation_plan.md); catalog in the skill folder |

## Planned — do not create SKILL.md yet

| Skill | Use when | Catalog cards |
|---|---|---|
| `retrieval-and-memory` | Chunk, embed, retrieve, or remember | [Retrieval](../../wiki/catalog/README.md#retrieval) |
| `workflow-patterns` | Record trigger, approval, or scheduled report | triggers, human-gates, idempotency, commit-boundaries, surfaces + [workflow-patterns.md](../../wiki/3-build/workflow-patterns.md) |
| `api-and-integration` | Schema, REST, webhooks | relational-data, apis, webhooks-and-events, files-and-blobs |
| `claude-integration` | Runtime, tools, Claude API | Architecture frameworks + Tools + Runtime + state-and-checkpoints |
| `testing-and-evals` | Golden sets, judges, regression gates | [Evals](../../wiki/catalog/README.md#evals) |
| `production-readiness` | Launch, operate, 3am | [Production](../../wiki/catalog/README.md#production) |
| `orient-scaffold` | First 15 minutes in this repo | [context/repo-map.md](../../context/repo-map.md) — not a catalog card |

Always-on rules (not a skill): [../rules/engagement.mdc](../rules/engagement.mdc).
