# Document outlines

Section skeletons for each planning document, taken from `cashflow-copilot/docs/`. The architecture diagram (L1/L2/L3) comes from `wiki/diagrams/` under `agentic-system-design`. Other Mermaid in these documents, such as a state machine or an improvement loop, only illustrates a process and never stands in for the architecture diagram. Keep the numbered sections so cross-references stay stable ("runtime plan §9"). Each bullet says what the section must contain; open the matching cashflow section for a worked example.

Every document starts with this header:

```markdown
# <Title>

Status: <proposed design | partially implemented: list exactly what exists>. <One sentence saying what this does NOT imply exists.>

**Local first:** <what runs locally; what is optional and deferred>.

<One line linking to the spine and sibling documents.>
```

## implementation_plan.md (the spine)

- **Opening block.** Status; current delivery scope; the required phase path in one sentence; model hosting kept separate from app hosting; reading order of the other documents; a note on protocol revisions (which inserts are required and which are conditional).
- **§1 Possible directory structure.** A tree relative to the project root, a one-line comment per file, and conditional paths marked "create only if …". End with "avoid empty placeholders; introduce a module when its behavior and ownership are clear" and the CI location note.
- **§2 Overview.** The business outcome; the L2 topology diagram from `wiki/diagrams/<project>-l2.mmd`, written to `agentic-system-design` (it should show user → UI → API → runs/outbox → queue → worker → harness → agents → tools → services → stores, plus review → gate → executor); the process layout; the access path; the technology ownership table `Component | Owns | Does not own`; framework citations.
- **§3 Decisions before the first agent.** About 12 numbered decisions: scope, shared model foundation, typed contracts, deterministic core, trust boundary, side effects, evidence boundary, versioning, runtime, delivery target, tool boundary, conditional protocols.
- **§4 Configuration inventory.** A table `File or settings group | Define before use`; the precedence order; secret handling; the startup rejection list; environment injection per service.
- **§5 Build order and component plans.** One paragraph on ordering and inserts, then each phase in the block format from SKILL.md.
- **§6 Teaching structure for every session.** The nine-step loop, and a note that planned command names are interfaces, not runnable commands.
- **§7 First implementation session, in exact order.** Ten numbered steps ending in "a reproducible foundation"; specialist agents come only after the harness, the tools, and the evaluation harness exist.

## agent_runtime_plan.md

- **Initialization handoff.** List the existing typed contracts, provider ABC, shared base agent, configured model, YAML prompt directory, and offline/live probe results. Preserve them as the foundation for phase 05. Connectivity does not prove business quality.
- **§1 What "a base model for all LLM calls" means.** Three foundations (data contracts, shared model configuration, shared execution harness); one configuration does not mean one model; do not invent a framework.
- **§2 Runtime responsibilities and files.** A table `File | Responsibility | Key acceptance condition`, and how the rules are enforced (a lint or import rule plus integration tests).
- **§3 Proposed model configuration.** A TOML sketch with profiles, roles, per-agent and per-workflow limits, and execution mode, with values labelled as hypotheses to tune. Include an embedding profile and a pricing table.
- **§4 Harness contract.** `AgentRunner.run(spec, input, context, budget) -> result`; the fields of the spec and context; the runner's ordered steps; the crash window after a provider call.
- **§5 Build each specialist in the same order.** The ten-step checklist and a table `Specialist | Inputs | Typed output | Permitted tools`.
- **§6 Tool contracts and authorization.** The tool definition field table; no generic SQL, HTTP, or shell tools; server-side checks; idempotent internal writes; operation keys.
- **§7 Inner model/tool loop.** The pseudocode loop, the termination conditions, the no-progress fingerprint, and a note on verifying framework usage limits.
- **§8 Outer workflow loop.** State contents, what never goes in state, the Mermaid state graph with back-edge counters, run states versus action states, human-wait deadlines, reauthorization.
- **§9 Retry ownership.** A table `Failure | Owner | Allowed response`; checkpoints are not exactly-once; side effects sit in isolated nodes behind a ledger.
- **§10 Budget and context controls.** Atomic reservations, what counts toward usage, enforceable limits versus estimated dollar limits, context priority, cache keys.
- **§11 Observability from the first invocation.** The questions an operator must be able to answer, the event fields, the tool-protocol spans, and the harness demo list (valid, denied, limit stop, no-progress, malformed, cancel, restart, uncertain).

## <protocol>_plan.md (tool boundary and conditional delegation)

- **§1 Decision and protocol boundaries.** Which protocol is required and which is conditional; a table `Boundary | Mechanism | Project example` from UI down to the database.
- **§2 Version compatibility first.** A compatibility matrix (protocol revision, SDK, client adapter, transport, auth); the lifecycle differences between revisions; dated facts with links.
- **§3 Host, clients, servers.** A table `Server | Introduction phase | Served tools | Data authority`; what no server exposes; a bounded catalog per agent role.
- **§4 What database access through the protocol means.** A Mermaid path, what the protocol does *not* replace, no generic SQL server, database roles per server, pool scoping.
- **§5 Tools, resources, prompts.** Tools first; resources need the same checks; remote text is data.
- **§6 Transport and authorization.** The stdio lesson steps, then the authenticated HTTP steps: resource-bound tokens, run delegation, no passthrough, origin checks, reauthorization.
- **§7 Configuration and directory additions.** The tree and the fields of each configuration file; delegation disabled by default.
- **§8 Required implementation sequence.** Numbered steps mapped to phases, and the acceptance paragraph.
- **§9 Runtime and operational rules.** Deterministic servers, operation keys versus request IDs, transport faults versus domain errors, the trace chain, separate processes.
- **§10 Delegation decision gate and example.** The conditions list, "deferred by design", and one bounded example with its prohibitions.
- **§11 Delegation implementation steps, if selected.** Pinning, card or identity, authentication, task mapping, minimal payload, polling, state mapping, artifact validation, duplicates, limits, local authority retained, comparison with a local equivalent.

## evaluation_harness_plan.md

- **§1 Distinguish the harnesses.** A table `Harness | Runs in | Responsibility`; the system under test uses the real services, prompts, and graph.
- **§2 What makes a golden example.** Task, identity, state, evidence, expected facts and actions, forbidden behavior, and a reviewable reason; what the fixture already supplies.
- **§3 Dataset development and split strategy.** Owners, the dev, regression, and holdout sets, splits by family, lineage fields, holdout replacement, the expansion target.
- **§4 Typed case contract.** The field list, `setup_actions` versus prompts, `required_events`, and separate types for evaluation cases and task requests.
- **§5 Build the runner step by step.** Loader, environment factory, clock and identity, scenario adapter, controlled boundaries, event recorder, real workflow, scheduled events, postconditions, grading, report, cleanup.
- **§6 Evaluation modes.** A table `Mode | Models/retrieval | Purpose | What it cannot prove`.
- **§7 Grader inventory.** A table `Grader | Inputs | Assertion or metric`; limits on model graders; critical invariants versus averages.
- **§8 Map fixtures to implementation layers.** A table `Cases | Minimum layers to test`; new protocol and delegation cases to author.
- **§9 Adversarial, property, and metamorphic checks.** A list of invariants (renaming, reordering, replay, a known delta, tenant additivity, approval invalidation).
- **§10 Trial execution and reproducibility.** Repeated trials, the run manifest fields, no promise of bit-for-bit replay.
- **§11 Report format and release gates.** Output formats, separate status buckets, numbered release rules, statistics caveats.
- **§12 Improvement loop.** A Mermaid loop from baseline through release to feedback; diagnose at the failing boundary; freeze before the holdout run.
- **§13 Local checks and cadence.** A table `Trigger | Required work`; answer keys stay out of images.

## deployment_plan.md

- **Local scope and future mapping.** A table `Capability | Required local implementation | Optional future cloud mapping`; no emulator required.
- **§1 Deployment units.** A table `Unit | Responsibilities | Scaling signal`; boundaries follow operational ownership.
- **§2 Local container sequence.** Numbered build steps, then acceptance, then the planned launch command with notes on environment interpolation versus injection.
- **§3 CI and artifact provenance.** Local commands first; the pipeline stage list; live evaluation kept separate; immutable digests.
- **§4–5 Optional cloud architecture and provisioning order.** Clearly marked as future reference.
- **§6 Authentication, secrets, tenant boundaries.** The browser flow, cookie rules, secret locations, ownership checks, and tool-protocol and delegation authentication.
- **§7 Queue processing and crash behavior.** Atomic dispatch intent, reference-only messages, leases, acknowledge after durable state, bounded retries, safe redrive.
- **§8 Monitoring and audit.** A table `Layer | Signals`, correlation, telemetry versus audit, the initial alerts, each with an owner and a runbook.
- **§9 Candidate service objectives.** What to measure; load tests are test conditions, not promises.
- **§10 Release, rollback, recovery.** Numbered sequence; reconcile after a restore.
- **§11 Required runbooks.** A table `Runbook | Concrete procedure`; each names a role, evidence, first reversible action, escalation, and resume conditions.
- **§12 Cost and handoff.** Cost drivers without invented numbers; the handoff contents.
