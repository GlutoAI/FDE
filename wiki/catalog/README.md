# Decision catalog

One file, one decision family. These are the sheets used at the moment of choice.

Phase folders (`1-frame` … `6-land`) answer **when in the engagement**. This directory answers **what to decide**. `.cursor/skills/` answers **how to implement** — write those only after the matching cards are filled.

**Most cards here are placeholders.** A file with `status: placeholder` is not guidance. Do not invent its contents. Do not treat a stub as a decision. Fill cards one at a time.

## Card contract

Every card uses the same skeleton (see [_TEMPLATE.md](_TEMPLATE.md)):

1. When this card is needed
2. The decisions — options × when × cost of being wrong
3. Anti-patterns
4. Production checks
5. Current defaults, dated
6. Pointers to related cards, phase pages, and the paired skill

Target length is short enough to use under time pressure. If a card needs more than ~150 lines, it is two cards.

## Families

| Family | Wave | Cards |
|---|---|---|
| [Engagement](#engagement) | 0 | Interviews, issue-to-idea, business go/no-go, qualification, first slice |
| [Architecture](#architecture) | 2 | Pattern, model-vs-code, triggers, frameworks |
| [Retrieval](#retrieval) | 1 | Chunking, embeddings, RAG, vector stores, memory |
| [Data](#data) | 3 | Relational, APIs, webhooks, idempotency, blobs |
| [Tools](#tools) | 3 | Tool design, MCP, blast radius |
| [Runtime](#runtime) | 4 | Loop, Claude API, caching, errors |
| [Evals](#evals) | 5 | Golden sets, judges, trajectories |
| [Production](#production) | 6 | Observability, cost, security, rollout |
| [Surfaces](#surfaces) | 6 | Run inspector, approvals UI, dashboards |

## Engagement

| Card | Owns | Skill |
|---|---|---|
| [customer-interviews.md](customer-interviews.md) | Which questions, in what order, when to stop | `fde-engagement` |
| [current-state.md](current-state.md) | What actually happens today | `fde-engagement` |
| [issue-to-idea.md](issue-to-idea.md) | Complaint → solvable bet | `fde-engagement` |
| [problem-statement.md](problem-statement.md) | Written statement with a number | `fde-engagement` |
| [business-decisions.md](business-decisions.md) | Go/no-go, buy vs build, whose budget | `fde-engagement` |
| [stakeholder-map.md](stakeholder-map.md) | Who decides, uses, gets blamed | `fde-engagement` |
| [qualification.md](qualification.md) | Rule vs workflow vs agent | `fde-engagement` |
| [success-metrics.md](success-metrics.md) | What number moves, how measured | `fde-engagement` |
| [constraints.md](constraints.md) | Systems, access, compliance, budget | `fde-engagement` |
| [scoping.md](scoping.md) | First slice, demo milestone, what's out | `fde-engagement` |

## Architecture

| Card | Owns | Skill |
|---|---|---|
| [agent-pattern-choice.md](agent-pattern-choice.md) | Which rung on the ladder | `agentic-system-design` |
| [model-vs-code.md](model-vs-code.md) | What the model may decide | `agentic-system-design` |
| [multi-agent-split.md](multi-agent-split.md) | One agent vs orchestrator + workers | `agentic-system-design` |
| [triggers.md](triggers.md) | Event vs schedule vs manual | `workflow-patterns` |
| [human-gates.md](human-gates.md) | When a human must approve | `workflow-patterns` |
| [agent-frameworks.md](agent-frameworks.md) | Custom loop vs SDK vs LangGraph | `claude-integration` |

## Retrieval

| Card | Owns | Skill |
|---|---|---|
| [chunking.md](chunking.md) | Unit of retrieval | `retrieval-and-memory` |
| [embeddings.md](embeddings.md) | Model, dimensions, re-embed | `retrieval-and-memory` |
| [rag-patterns.md](rag-patterns.md) | Naive vs hybrid vs agentic vs none | `retrieval-and-memory` |
| [vector-stores.md](vector-stores.md) | Where vectors live | `retrieval-and-memory` |
| [indexing-ingestion.md](indexing-ingestion.md) | How documents enter the index | `retrieval-and-memory` |
| [context-assembly.md](context-assembly.md) | What enters the window | `retrieval-and-memory` |
| [memory.md](memory.md) | Working / episodic / semantic / profile | `retrieval-and-memory` |

## Data

| Card | Owns | Skill |
|---|---|---|
| [relational-data.md](relational-data.md) | Schema, migrations, audit tables | `api-and-integration` |
| [state-and-checkpoints.md](state-and-checkpoints.md) | What survives a step, run, restart | `claude-integration` |
| [apis.md](apis.md) | Resources, status codes, errors | `api-and-integration` |
| [webhooks-and-events.md](webhooks-and-events.md) | Signatures, at-least-once, outbox | `api-and-integration` |
| [idempotency.md](idempotency.md) | Stable keys, unique constraints | `workflow-patterns` |
| [commit-boundaries.md](commit-boundaries.md) | Fire after commit | `workflow-patterns` |
| [files-and-blobs.md](files-and-blobs.md) | Documents, size limits, signed URLs | `api-and-integration` |

## Tools

| Card | Owns | Skill |
|---|---|---|
| [tool-design.md](tool-design.md) | Names, schemas, read vs write | `claude-integration` |
| [mcp.md](mcp.md) | When MCP beats in-process tools | `claude-integration` |
| [permissions-and-blast-radius.md](permissions-and-blast-radius.md) | Least privilege per tool | `claude-integration` |

## Runtime

| Card | Owns | Skill |
|---|---|---|
| [model-selection.md](model-selection.md) | Which model for which job | `claude-integration` |
| [structured-outputs.md](structured-outputs.md) | Validated object, not a parsed string | `claude-integration` |
| [agent-runtime.md](agent-runtime.md) | Loop, dispatch, retries, step caps | `claude-integration` |
| [claude-api-current.md](claude-api-current.md) | Current Claude API facts | `claude-integration` |
| [prompt-caching.md](prompt-caching.md) | Breakpoints, TTL, when not to cache | `claude-integration` |
| [error-taxonomy.md](error-taxonomy.md) | Retryable vs terminal vs needs-a-human | `claude-integration` |

## Evals

| Card | Owns | Skill |
|---|---|---|
| [eval-design.md](eval-design.md) | Golden sets, pass@k, regression gates | `testing-and-evals` |
| [judges-and-rubrics.md](judges-and-rubrics.md) | When LLM-as-judge is valid | `testing-and-evals` |
| [trajectory-tests.md](trajectory-tests.md) | Right tools, order, args | `testing-and-evals` |

## Production

| Card | Owns | Skill |
|---|---|---|
| [observability.md](observability.md) | Traces, what to log and never log | `production-readiness` |
| [cost-and-budgets.md](cost-and-budgets.md) | Token and dollar caps | `production-readiness` |
| [reliability.md](reliability.md) | Retries, DLQ, model-down | `production-readiness` |
| [security-agentic.md](security-agentic.md) | Tool misuse, excessive agency | `production-readiness` |
| [prompt-injection.md](prompt-injection.md) | Untrusted content is data | `production-readiness` |
| [rollout.md](rollout.md) | Shadow → suggest → approve → autonomous | `production-readiness` |

## Surfaces

| Card | Owns | Skill |
|---|---|---|
| [run-inspector.md](run-inspector.md) | Why it did what it did | `workflow-patterns` |
| [approvals-ui.md](approvals-ui.md) | Pending queue, concurrent decide | `workflow-patterns` |
| [dashboards.md](dashboards.md) | Pending, completed, **failed** | `workflow-patterns` |

## Do not write these as catalog cards

They stay as phase method:

- [wiki/1-frame/consulting-craft.md](../1-frame/consulting-craft.md) — how you narrate and take a hint
- [wiki/6-land/demo-and-handoff.md](../6-land/demo-and-handoff.md) — how you close
- [wiki/2-design/agentic-system-design.md](../2-design/agentic-system-design.md) — full pattern ladder (catalog has a thin choice card)
- [wiki/3-build/workflow-patterns.md](../3-build/workflow-patterns.md) — the three operational shapes

Test craft and the spoken launch checklist live in [mental-model.md](../mental-model.md) (phases 4–5) and [`fde-engagement`](../../.cursor/skills/fde-engagement/SKILL.md) until the Evals and Production cards are written. Do not recreate `4-prove/` or `5-operate/` folders.

Do **not** recreate `decision-design.md`, `trigger-design.md`, `context-and-memory.md`, `data-model.md`, `api-design.md`, `integration-patterns.md`, `claude-integration.md`, `error-handling.md`, or `frontend.md` under phase folders. Those names are retired. The cards above replaced them.

## Generation order

Re-ordered for the current engagement: **Retrieval moved last.** Nothing in the present scope touches chunking, embeddings, or vector search, so those 7 cards sit behind the 25 that map to the work actually being built. Restore the original position if the scope changes.

| Order | Family | Cards | State |
|---|---|---|---|
| 0 | Engagement | 10 | **Written** |
| 1 | Architecture | 6 | Placeholder |
| 2 | Data + Tools | 10 | Placeholder |
| 3 | Runtime | 6 | Placeholder |
| 4 | Surfaces | 3 | Placeholder |
| 5 | Evals | 3 | Placeholder |
| 6 | Production | 6 | Placeholder |
| 7 | Retrieval | 7 | Placeholder — deferred |

Within a family, order still matters:

- **Runtime:** write [claude-api-current](claude-api-current.md) first — the other five Runtime cards and [tool-design](tool-design.md) all rest on its facts.
- **Data:** [triggers](triggers.md) → [commit-boundaries](commit-boundaries.md) → [idempotency](idempotency.md) are one decision split three ways; idempotency is undefined until the trigger's delivery guarantee is fixed. Write them together.
- **Architecture:** [model-vs-code](model-vs-code.md) is the keystone — Tools, Runtime, and Evals all inherit their scope from it.
- **Cross-wave:** [human-gates](human-gates.md) (Architecture) depends on [permissions-and-blast-radius](permissions-and-blast-radius.md) (Tools). Draft the gate card after the blast-radius card, or accept a revisit.
- **Evals:** [eval-design](eval-design.md) is the parent; judges and trajectories are methods inside it.
- [observability](observability.md) and [run-inspector](run-inspector.md) are one trace rendered for two audiences — operator and end user. Keep them consistent.
