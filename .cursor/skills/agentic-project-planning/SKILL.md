---
name: agentic-project-planning
description: Breaks an agentic system project into a planning document set and ordered phases with verifiable exit gates, modelled on cashflow-copilot/docs. Covers the implementation plan (destination directory tree, overview diagram, technology ownership, decisions before the first agent, configuration inventory, phases labelled required, optional, or conditional), the agent runtime plan, the tool-protocol (MCP/A2A) plan, the evaluation harness plan, and the local-first deployment plan, plus a catalog of the planning considerations. Use after agentic-project-init, or when writing or reviewing a project plan, roadmap, phase breakdown, milestones, or exit gates for an agent or multi-agent system. For choosing the architecture pattern, use agentic-system-design; for drawing it in Figma, use figma-draw-standards.
---

# Agentic Project Planning

A plan is **a sequence of exit gates that someone else can verify**, not a list of layers. Each phase names what it depends on, the files it introduces, numbered steps, and a gate that is demonstrated rather than asserted. The reference is [`cashflow-copilot/docs/`](../../../cashflow-copilot/docs/implementation_plan.md). Open the matching document there before writing its counterpart.

Initialization already owns the small foundation described in [foundation.md](../agentic-project-init/foundation.md). Preserve it and plan how to extend it; do not recreate its provider or base-agent abstractions. A connection check is separate from the headline business slice and quality evaluation.

This skill starts after [`agentic-project-init`](../agentic-project-init/SKILL.md). The pattern choice and every architecture diagram belong to [`agentic-system-design`](../agentic-system-design/SKILL.md). The plan records that choice and links to its diagrams; it never draws a competing architecture diagram of its own.

## Non-negotiables

- [ ] Every document opens with a **Status** line that separates proposed work from implemented work. Nothing is described as existing unless it runs
- [ ] Deterministic business logic is planned and tested before any model touches business data; the initialization connection probe uses only a fixed synthetic prompt
- [ ] The evaluation harness exists **before** agent tuning begins
- [ ] A thin end-to-end slice runs from phase 01, and every later exit gate extends it rather than adding a layer beside it
- [ ] One baseline agent is measured before specialists are considered, and it is kept as the control. Specialists and protocol servers are conditional on a recorded reason
- [ ] Side effects come last, behind approval of an exact version and a separate executor. Agents only propose
- [ ] Every phase has *Depends on*, *Files*, numbered steps, and an observable **Exit gate**
- [ ] Every phase is labelled required, optional, or conditional, and no optional track blocks local completion
- [ ] Every conditional technology has a written decision gate whose default outcome is "deferred by design"
- [ ] Framework claims cite the framework's own documentation, and our choices are labelled as ours ("This division is our design choice")
- [ ] Claim versions as installed only after checking the environment/lock file. Initialization pins its small foundation; later compatibility spikes pin each added framework

## The document set

| Document | Owns | Written by |
|---|---|---|
| `README.md` | Status, scope, commands that run today, links to the roadmap | init, with the roadmap added here |
| `docs/data_dictionary.md`, `docs/evaluation_guide.md` | What the fixture contains and how cases are isolated and scored | init |
| `docs/implementation_plan.md` | **The spine.** Tree, architecture, decisions, configuration, phases, session method. Read first | this skill |
| `docs/agent_runtime_plan.md` | Model profiles, the shared harness, agent specs, tool contracts, inner and outer loops, retries, budgets | this skill |
| `docs/<protocol>_plan.md` (for example `mcp_a2a_plan.md`) | The tool boundary: servers, catalogs, auth, transports, the conditional delegation gate | this skill |
| `docs/evaluation_harness_plan.md` | Harness types, golden examples, splits, runner, modes, graders, reports, release gates, improvement loop | this skill |
| `docs/deployment_plan.md` | Local delivery, CI, queue semantics, monitoring, release and rollback, runbooks, optional cloud | this skill |
| `docs/decisions/`, `docs/lessons/` | Short decision records and runnable walkthroughs | created when the first one exists |

Split a concern into its own document when it has its own acceptance criteria and would take more than about 150 lines in the spine. Each satellite document opens by linking back to the spine and to its sibling documents.

**Writing order:** spine sections 1–4 → the phase list → runtime → tool protocol → evaluation → deployment → cross-links → README roadmap. Section outlines are in [doc-outlines.md](doc-outlines.md).

## Spine structure (`implementation_plan.md`)

1. **Possible directory structure.** The destination tree, annotated per file, created incrementally. Say explicitly: "Avoid creating empty placeholders."
2. **Overview.** The business outcome in one paragraph; the L2 topology diagram, whose source is `wiki/diagrams/<project>-l2.mmd` and follows `agentic-system-design` (link to it, or embed a copy of that file and nothing else); the access path (for example *agent → tool client → authenticated server → service → DB*), and a **technology ownership table** (`Component | Owns | Does not own`).
3. **Decisions to establish before the first agent.** A numbered list covering scope, shared model foundation, typed contracts, deterministic core, trust boundary, side effects, evidence boundary, versioning, runtime, delivery target, tool boundary, and conditional protocols.
4. **Configuration inventory.** `File or settings group | Define before use`, plus one explicit precedence order, the fail-closed startup rules, and the secret-handling rules.
5. **Build order and component plans.** The phases, in the format below.
6. **Teaching structure for every session.** The per-session loop.
7. **First implementation session, in exact order.** Ten or so concrete steps ending in a reproducible foundation.

## The phase ladder

Adapt the names to the domain and keep the order. The reasons are in the ordering rules below.

**The thin slice.** Phase 01 ends with one command that asks the headline question and gets a typed answer through a fake model, with every missing piece a *named* stub. Each later phase replaces a stub with the real component, so the exit gate always includes "the slice still runs, and now goes through X". The phases below say where depth is added. They are not layers built in isolation.

| # | Phase | Label | Exit gate shape |
|---|---|---|---|
| 00 | Business contract and immutable baseline | required; initialization provides only the empty `data/raw` and `data/processed` contract | Another engineer can explain the data, the answer, the approval boundary, and what is not modeled |
| 01 | Package, skeleton, validated configuration, thin slice | required; initialization provides the backend/frontend skeleton, configuration, and connection agent; the thin slice remains | Fixture mode starts offline; invalid production config fails closed; a clean lock install works; the slice command runs end to end on stubs |
| 02 | Domain contracts, clock, errors, events | required | Records representable without floats; no calculation depends on wall-clock time or a model |
| 03 | Persistence, migrations, repositories, import | required | Counts match; re-import is idempotent; cross-tenant reads fail on the real database |
| 04 | Authentication and authorization | required | No unauthenticated or cross-tenant access; roles are never taken from bodies or model output |
| 05 | Extend the initialization foundation into the full execution harness | required | A typed task runs through a fake model and the runner; allowlists and limits cannot be bypassed |
| 06 | Deterministic services and typed tools | required | All oracle checks pass without a model; unauthorized tool calls emit a denial event |
| 06A | Tool protocol boundary (MCP) decision and servers | conditional | Either a recorded reason to stay with in-process typed tools, or a real client reaching authorized tools over the chosen transports with results equal to the direct-service results |
| 07 | Evaluation harness foundation | required | The harness catches deliberately wrong implementations and reports honestly |
| 08 | Retrieval: ingestion, embeddings, citations | required if documents exist | Authorized searches find the trap evidence; other tenants' text never appears |
| 09 | One agent as a measured baseline | required | A reproducible baseline report; output is grounded and bounded; the agent cannot self-approve |
| 10 | Outer workflow, then specialists if measured | workflow required; specialists conditional | The scenario completes in one durable workflow. Specialists are added only if the phase 09 report shows a gap they close, and their improvement and extra cost are measured against the baseline |
| 10A | Agent-to-agent delegation (A2A) decision | conditional | A justified deferral, or a tested remote delegation with recovery |
| 11 | State, memory, and recovery | required | A paused run survives a restart; state is tenant-private; memory cannot override facts |
| 12 | Approval, execution, outbox, uncertain outcomes | required | The fake executor sees only approved current versions; uncertainty is visible to operators |
| 13 | Run API, workers, queue, cancellation | required | Requests return fast; work survives restarts; cancellation is checked at every action boundary |
| 14 | User interface | required | The owner completes the scenario; a lower role cannot act, even by calling the API directly |
| 15 | Integrations (local simulators first) | required locally; real sandbox optional | Sync recovers from expiry, throttling, duplicates, and gaps against the simulator |
| 16 | Full evaluation, resilience, security, observability | required | No critical invariant failures; reproducible reports; operator-visible recovery |
| 17 | Local container delivery and repeatable checks | required | One command starts everything; images contain no answer keys; it runs with cloud settings unset |
| 18 | Cloud deployment and recovery drill | optional, deferred | Only if selected: deployable from infrastructure code, restore and rollback demonstrated |
| 19 | Demonstration, evaluation review, handoff | required | Another engineer can run, explain, test, and recover the local system |

**Numbering:** keep numbers stable once published. Add inserts with a letter suffix (`06A`) instead of renumbering. Give conditional gates a letter too (`10A`). State the required path in one sentence once the decisions are recorded. Cashflow selected MCP and specialists, so its path is *"00–17 plus 06A, then 19; 18 optional; 10A conditional."*

**Conditional is the default for autonomy.** Multiple specialists, protocol servers, and agent-to-agent delegation each climb the pattern ladder in `agentic-system-design`. Plan them as decision gates (format below) whose default outcome is "deferred by design", and select them only with a recorded measurement or ownership reason.

## Ordering rules

Each rule prevents a specific failure:

1. **Contract before code.** Phase 00 turns the fixture into an acceptance matrix and a demo script, including one blocked action. Without it, "done" is negotiable.
2. **Configuration and contracts before persistence.** Typed settings that fail closed stop a fixture identity from ever reaching a real side effect.
3. **Auth before any data tool.** Tenant context is built from verified identity, never from tool arguments or model output.
4. **A shared foundation before any agent.** Initialization creates the provider ABC, shared base agent, validated model config, YAML prompt loader, fake provider, and a one-request connection agent. Phase 05 extends that foundation with authorized context, tool limits, telemetry, and workflow budgets before business agents. No agent file constructs its own provider client or retry loop.
5. **Services → tools → protocol (if selected) → agents.** Each step wraps a tested one. Protocol servers are thin adapters, and the same numbers must come out both ways.
6. **Evaluation before tuning.** Prove that the harness catches a wrong total, a cross-tenant leak, a duplicate, and an unapproved action before trusting a pass.
7. **Baseline before specialists.** Multi-agent designs must beat a single agent on the same cases, tools, and budget accounting, or they are cost without benefit. If the baseline is good enough, phase 10 is only the durable workflow around it.
8. **State → approvals → API → UI.** Durable state must exist before a human can pause a run, and the API must exist before a UI renders its state.
9. **Simulators before real integrations.** A missing external account never blocks the local gate. Report sandbox results separately.
10. **Events early, dashboards late.** Define observable events in phase 02, instrument each component as it lands, and build dashboards in 16 once real events exist.
11. **Local completion before cloud.** The cloud track is a retained checklist, not a completion gate.

## Phase block format

```markdown
### Phase NN — <Name>

**Depends on:** <phase numbers>. **Files:** `<paths this phase introduces>`.
<Optional: **Inputs:** … **Outputs:** … — for phases that turn artifacts into artifacts.>

1. <Imperative step; name the contract before the implementation.>
2. <…>
N. <Test the failure path by name, e.g. "Test an Aurora request using a Copper record ID.">

**Exit gate:** <Observable conditions another engineer can check. Say what is NOT claimed.>

<Optional: one sentence citing the framework's documentation for any behavior we rely on.>
```

Five to twelve steps. Every phase includes at least one step that **breaks it on purpose**.

## Decision gate format for conditional technology

Use this for the protocol boundary (06A), specialists (10), agent-to-agent delegation (10A), and any other capability that adds autonomy or a network hop.

```markdown
### Phase NNA — <Technology> decision

1. Record whether <concrete condition 1>, <condition 2>, or <an explicitly selected exercise> holds.
   Otherwise record "deferred by design" and leave it disabled in config.
2. If selected: <bounded example>, <what it may never do>, <tests against a separate fake peer>.

**Exit gate:** either an explicit, justified deferral, or <tested behavior>. The core scenario does not depend on it.
```

Reports label deferred features "not applicable by design", never "passed".

## Per-session loop (spine section 6)

Business reason → change into the project directory and inspect the planned path → contract first → small implementation → run one reproducible command → break it deliberately → inspect the result, report, and trace → explain the tradeoff → mark the exit gate only when it is demonstrated. Write the lesson note after the commands exist. Planned command names are interfaces, not runnable commands.

## Review before sharing a plan

- [ ] A reader can pick any phase and know what "done" looks like without asking
- [ ] Every phase's exit gate says how the thin slice changed; no phase ends with nothing runnable
- [ ] Each conditional phase has its decision recorded, or is marked "deferred by design"
- [ ] The architecture diagram lives in `wiki/diagrams/` and passes the `agentic-system-design` review checklist, plus the `figma-draw-standards` checklist if it is rendered in Figma
- [ ] Every trap in the fixture has a phase that handles it and a gate that proves it
- [ ] The retry owner is named once for each failure type, so retries are never multiplied across layers
- [ ] Every loop has a counter, a budget, and a terminal state
- [ ] Every side effect has an approval binding, an idempotency key, and an "outcome unknown" path
- [ ] What each tier proves, and what it cannot prove, is stated (fake model versus real model, simulator versus sandbox, local versus cloud)
- [ ] The considerations in [catalog.md](catalog.md) that apply to this project each have an answer or an explicit "not applicable"

## Anti-patterns

- **Layers, not slices.** "All models, then all endpoints" cannot be demonstrated until the last day. Phases deepen one running slice; they do not build layers side by side.
- **Copying the reference's selections.** Cashflow chose MCP servers and three specialists for its own reasons. A new project re-decides both at their gates.
- **Business agent first.** Starting domain agents before deterministic services exist means every bug looks like a model problem. The no-tool initialization probe is a bounded infrastructure check and does not use business records or golden answers.
- **Evaluation last.** Tuning without a harness produces anecdotes, not measurements.
- **Protocols everywhere.** An A2A hop between internal nodes, or a network service per tool, adds failure modes without an ownership reason.
- **Cloud as the finish line.** Making hosted deployment a completion gate blocks the whole project on accounts and cost.
- **"Latest" dependencies.** Unpinned SDKs and protocol revisions make last month's plan wrong. Pin them in a compatibility spike.
- **Policy in the prompt.** Holds, eligibility, and approvals are code. The model explains, investigates, and drafts.
- **Plans that read as done.** "The system uses X" in a proposal misleads the next reader. Write "will use" and keep the Status line current.

## Additional resources

- [catalog.md](catalog.md): the full catalog of planning considerations, grouped by concern, each with the questions to answer, the cashflow answer, and where it lands in the plan
- [doc-outlines.md](doc-outlines.md): section outlines for each document in the set
