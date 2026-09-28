# Planning catalog for agentic system projects

Every consideration that `cashflow-copilot/docs/` answers, generalized. For each concern, **Decide** lists the questions the plan must answer, **Cashflow** gives the reference answer, and **Lands in** says where the answer is written. Mark a concern "not applicable" explicitly rather than skipping it.

## Contents

1. Scope and business contract
2. Pattern and model-versus-code split
3. Synthetic data and oracle
4. Delivery target and modes
5. Runtime, packaging, versions
6. Configuration and secrets
7. Domain contracts, time, errors, events
8. Persistence and tenant isolation
9. Identity and authorization
10. Shared model foundation
11. Agent specifications
12. Tool contracts
13. Tool protocol boundary (MCP)
14. Agent-to-agent delegation (A2A)
15. Retrieval
16. Workflow orchestration and state
17. Loops, budgets, termination, retries
18. Memory
19. Side effects: approval, execution, outbox
20. API, workers, queue, cancellation
21. User interface
22. External integrations
23. Evaluation
24. Observability and audit
25. Agentic security threats
26. Deployment units and containers
27. Operations and release
28. Demonstration and handoff

---

## 1. Scope and business contract

**Decide:** Which user outcome is being delivered? Which roles exist and who may approve? What is explicitly excluded in version one? What are the success measures? What is the demo script, including one blocked action?
**Cashflow:** One agency, a 14-day forecast, a receivables investigation, and reminders approved by a human. USD only. No money movement, lending, tax, or bookkeeping writes. The demo includes one successful review and one blocked action.
**Lands in:** Spine §3 item 1; phase 00.

## 2. Pattern and model-versus-code split

**Decide:** Which rung of the pattern ladder does this use, and what measurement forced it? What may the model decide, and what must code decide? What does each framework own, and what does it *not* own?
**Cashflow:** LangGraph owns durable transitions and approval pauses. Pydantic AI owns the specialist tool loop. The domain layer owns arithmetic and policy. Models select investigations, explain, and draft. A second model agreeing does not establish correctness.
**Lands in:** Spine §2 ownership table; the L2 diagram in `wiki/diagrams/`; the 06A and 10 decision gates; `agentic-system-design`.

## 3. Synthetic data and oracle

**Decide:** What is the frozen snapshot and hash? What is the golden answer, and is it recomputed independently? Which traps exist? Which holdouts have already been inspected? Which data gaps are listed for later?
**Cashflow:** Seed 42, `as_of` 2026-09-26, 2 tenants, 18 cases (4 holdout, already inspected), 8 scenarios. Future gaps: refunds, credit notes, multiple currencies, large corpora.
**Lands in:** Phase 00; the data dictionary; the evaluation guide.

## 4. Delivery target and modes

**Decide:** What is the required delivery target, and what is optional? Are model mode (fake, local, or hosted) and external-action mode (simulated or live) independent? Which missing accounts must *not* block completion?
**Cashflow:** Everything runs locally with Docker Compose. AWS is optional phase 18. A real model can run while sending stays simulated. Sandboxes for QuickBooks and messaging are optional exercises.
**Lands in:** The spine's opening status block; spine §3 item 10; the deployment plan.

## 5. Runtime, packaging, versions

**Decide:** Which application runtime and package manager? Which dependency groups (runtime, dev, eval, UI)? When are versions resolved and locked? Are existing scripts kept on their older runtime?
**Cashflow:** Python 3.12 with `uv` and a lock file resolved in phase 01. The data scripts stay on Python 3.9+ with the standard library only. Installed versions are reported only from a verified environment and lock file.
**Lands in:** Spine §3 item 9; phase 01.

## 6. Configuration and secrets

**Decide:** What is the configuration file inventory? What single precedence order applies? Which combinations fail closed at startup? How are secrets redacted? How is the environment injected per service? Where do rotating per-tenant tokens live?
**Cashflow:** Code defaults < base TOML < environment TOML < project `.env` < process environment. Startup rejects fixture identity combined with real actions, and rejects a missing model ID for a selected provider. A `config-check` command reports redacted values. Each container receives only its own variables. OAuth tokens live in encrypted integration storage, not in `.env`.
**Lands in:** Spine §4; phase 01; deployment plan §2.

## 7. Domain contracts, time, errors, events

**Decide:** How is exact arithmetic represented? How does the injected clock separate business dates from elapsed time? What is the typed error taxonomy? What observable event schema exists? What identifiers are used for idempotency and versioning?
**Cashflow:** `Money` in integer cents, an immutable `TenantContext` built from identity, and a `Clock` with a frozen implementation. Errors include stale source, missing evidence, invalid approval, budget exceeded, and uncertain delivery. Events are defined for model calls, tools, transitions, approvals, and execution.
**Lands in:** Phase 02.

## 8. Persistence and tenant isolation

**Decide:** Which database and extensions? Migrations from empty? Composite keys so a record cannot reference another tenant's record? Row-level security plus application scoping? Separate migration and application roles? Tenant settings local to each transaction on pooled connections? Is import idempotent? Do tests run against the real engine?
**Cashflow:** PostgreSQL with pgvector and RLS, with owner and bypass behavior addressed. Repositories require a `TenantContext`. There is no SQL generated by the model. Tests run against PostgreSQL, not only a SQLite substitute.
**Lands in:** Phase 03.

## 9. Identity and authorization

**Decide:** Which fixture identity is used in tests, and which real local issuer for the demo? Are sessions opaque and server-side? Is membership checked on every request? Is a stronger capability required to approve or execute than to read? Are CSRF protection, expiry, and logout revocation in place? Are resource-bound credentials used for tool servers?
**Cashflow:** Fixture identity only in local and test modes. A local OIDC test issuer drives the browser flow. Roles are never read from request bodies or model output. UI sessions and provider tokens are never forwarded to tool servers.
**Lands in:** Phase 04; deployment plan §6.

## 10. Shared model foundation

**Initialization prerequisite:** Follow [foundation.md](../agentic-project-init/foundation.md): Pydantic request/result contracts, `ModelProvider` ABC with fixture, OpenAI, and Anthropic implementations (one key per vendor), `BaseAgent`, a connection agent, central model profiles, versioned YAML prompts, offline tests, and a separately authorized live probe. Report missing credentials, authentication/permission, quota, timeout/network, and malformed output separately. Never treat a fake response as proof of key validity.

**Decide:** What are the named model profiles, and how do roles map to them? Is there a registry so agent files never construct providers? Is there one runner that applies budgets, deadlines, prompt versions, telemetry, and redaction? Are transport retries and output-repair retries separate? Is there a fake model that can request tools and simulate faults? Is unknown cost labelled unknown rather than zero?
**Cashflow:** `ModelProfile`, `ModelRegistry`, `AgentRunner.run(spec, input, context, budget)`, and a `fake` profile for local and test runs. `transport_attempts = 2` means one retry. Unregistered profiles fail.
**Lands in:** Initialization; phase 01 extends configuration; runtime plan §§1–4 and phase 05 extend the full harness.

## 11. Agent specifications

**Decide:** For each agent: a `<Role>Agent` name and one sentence of responsibility, the decisions it may make, input and output schemas, an incomplete-result status, evidence requirements, allowed tools, a versioned prompt, deterministic post-validation, and fake-model scripts for good and bad paths. When does it ask for clarification?
**Cashflow:** A baseline agent first, then an analyst, an investigator, and a collections specialist, each with a typed output and a minimal toolset. No agent can send, and no agent can invent a promise to satisfy its schema.
**Lands in:** The runtime plan §5; phases 09–10.

## 12. Tool contracts

**Decide:** For each tool: a stable name and version, typed arguments with no tenant or role override, the required capability, a result schema with source, version, and freshness, the side-effect class (read-only, idempotent internal write, or external action), allowed agents, timeout and result limits, failure semantics (not found versus inaccessible versus stale), and an operation key for writes.
**Cashflow:** `get_invoice:v1`, `project_cashflow`, `get_collection_eligibility`, and similar. There is no generic SQL, HTTP, or shell tool. Sending is absent from every agent toolset.
**Lands in:** The runtime plan §6; phase 06.

## 13. Tool protocol boundary (MCP)

**Decide:** Is a protocol boundary required? Which servers exist, split by data authority? Are they thin wrappers over the same tested services? Is authorization enforced at the server and not only by client allowlists? Is there a compatibility spike that pins the protocol, SDK, and client adapter? Is stdio used first and then authenticated HTTP? Is the catalog validated by hash? Is there no silent fallback to direct database access?
**Cashflow:** Selected at 06A: Finance, Evidence, and Collections MCP servers, each with its own database role. Evidence and Collections are scaffolded early and activated in 08 and 12. Direct results and MCP results must match. A project without separate data authorities or shared tool consumers can defer this and keep in-process typed tools behind the same contracts.
**Lands in:** The protocol plan §§1–9; phase 06A.

## 14. Agent-to-agent delegation (A2A)

**Decide:** Is there a separately owned agent with its own runtime and lifecycle, or an explicitly selected interoperability exercise? If not, record "deferred by design" and leave it disabled. If yes, define the bounded task, the minimum evidence shared, peer authentication, task mapping that survives restart, bounded polling, and what the peer can never do.
**Cashflow:** The 10A decision gate. The optional exercise is a remote Receivables Review Agent that returns a review artifact and cannot approve or send.
**Lands in:** The protocol plan §§10–11; phase 10A.

## 15. Retrieval

**Decide:** What is the corpus boundary, and what must never be indexed? What metadata does every chunk carry? Are chunk IDs deterministic, and is ingestion restartable? Which embedding profile and dimension? Is the tenant/ACL filter applied *before* candidate retrieval? What are the precedence rules for amendments and conflicting dates? Exact search first, approximate only after measuring? How are deletion and reindexing handled?
**Cashflow:** Only the documents listed in `documents/index.json`. Authorized searches must find the amendment, the dispute, and the tentative promise. Copper text never appears in Aurora results. Mock embeddings verify wiring only.
**Lands in:** Phase 08.

## 16. Workflow orchestration and state

**Decide:** What are the graph states and branches? Which branches may run concurrently, and with which snapshots? How are typed outputs persisted at node boundaries? Are run states kept separate from action states? Is there a counter on every back edge? What must never be serialized into state? Do old checkpoints resume under their original versions?
**Cashflow:** Run states are `queued`, `running`, `awaiting_input`, `awaiting_approval`, `completed`, `cancelled`, and `failed`. Action states are `reserved`, `dispatching`, `provider_accepted`, `delivered`, `failed`, and `delivery_unknown`.
**Lands in:** The runtime plan §8; phases 10–11.

## 17. Loops, budgets, termination, retries

**Decide:** What are the per-agent and per-workflow caps on requests, tools, transitions, and deadline? Are reservations atomic across parallel branches? Is no-progress detected by fingerprint? Which layer owns retries for each failure type? Does human waiting time count against the active deadline? Does a resumed run keep its budget?
**Cashflow:** Agent limits of 6 requests, 12 tools, and 1 repair. Workflow limits of 18 requests, 30 tools, 24 transitions, and 90 seconds. A retry ownership table covers each failure type. Queue redelivery never resets the budget.
**Lands in:** The runtime plan §§7, 9, 10.

## 18. Memory

**Decide:** How are conversation history, approved preferences, and authoritative facts kept separate? What consent, expiry, and deletion rules apply? What provenance is recorded on remembered facts? Is thread ownership checked before checkpoint reads? Does deletion propagate to indexes, caches, and summaries?
**Cashflow:** Preferences can shape style but never override balances, permissions, holds, or approvals. Financial facts are always refreshed from records.
**Lands in:** Phase 11.

## 19. Side effects: approval, execution, outbox

**Decide:** Is an immutable draft version or hash bound to the approval, together with actor, policy, expiry, and source version? Does an edit invalidate the approval? Are facts rechecked immediately before reserving the action? Are the action reservation and outbox written in one transaction? Is provider acceptance kept distinct from delivery? What happens when the outcome is unknown? Where is the kill switch?
**Cashflow:** A fake sender first. "Delivery unknown" leads to reconciliation or operator review, never a blind resend. The remaining race with external state is documented, not hidden.
**Lands in:** Phase 12; the runtime plan §9.

## 20. API, workers, queue, cancellation

**Decide:** Does the API return `202` with a run ID after durable creation? Are idempotency keys scoped to actor, tenant, and operation? Is the durable queue local first, with leases and fencing, heartbeats, and dead-letter handling? Is cancellation checked before model calls, tools, and actions? Is progress delivered by polling first?
**Cashflow:** A PostgreSQL-backed queue behind an interface. SQS is only an optional future adapter.
**Lands in:** Phase 13; deployment plan §7.

## 21. User interface

**Decide:** Does the UI show evidence, assumptions, and exact draft content? Is there an explicit state for each failure (denied, stale, budget exhausted, awaiting approval, delivery unknown)? Does the UI avoid making authorization decisions or caching one user's client globally? Is untrusted content escaped?
**Cashflow:** the template's React `frontend/`, calling the API same-origin through `/api`, with HttpOnly sessions managed by the backend. The run ID lives in the UI, and authoritative state comes from the API. Do not add a second UI stack.
**Lands in:** Phase 14.

## 22. External integrations

**Decide:** Which provider supplies each input, according to a capability matrix? Which inputs remain manual or imported, with their freshness shown? Is there a local simulator with the same contracts? Are webhook signatures verified, events deduplicated, and then the authoritative entity fetched? Is token refresh serialized?
**Cashflow:** A local accounting simulator and simulated sender are required. A real QuickBooks sandbox is optional and reported separately.
**Lands in:** Phase 15.

## 23. Evaluation

**Decide:** Which harness types exist? What defines a golden example: task, identity, state, evidence, expected facts and actions, and *forbidden* behavior? What is the split strategy, and when is a holdout replaced? Is there a typed case contract that keeps expectations away from the system under test? What are the runner steps? Which modes run, and what can each *not* prove? Which graders exist, and in what order? What are the report format and release gates? What is the improvement loop?
**Cashflow:** Deterministic graders run first. Model graders are used only for semantic quality and never override a money or authorization failure. `required_events` proves that the intended branch was reached. A planning target of 100–150 reviewed cases. Zero observed violations is a release criterion, not a proof.
**Lands in:** The evaluation plan; phases 07 and 16.

## 24. Observability and audit

**Decide:** Do correlation IDs span API, queue, worker, tool client and server, database, model, and action? Which versions are recorded on every run? Is redacted telemetry kept separate from append-only business audit records? Are high-cardinality metric labels avoided? What must never be logged (credentials, hidden reasoning)? Does every alert have an owner and a runbook?
**Cashflow:** An operator can answer who initiated a run, which records were read, what evidence supported the result, which version ran, why it stopped, and who approved what.
**Lands in:** Phase 02 events; the runtime plan §11; deployment plan §8; phase 16.

## 25. Agentic security threats

**Decide:** Is untrusted document, tool, or resource text treated as data? Are cross-tenant IDs rejected at every layer? Is token passthrough prevented? Are catalogs checked for tool-description injection? Are least-privilege database roles assigned per server? Is excessive agency ruled out (no send, SQL, or shell tools)?
**Cashflow:** `trust_level: untrusted_content` on every document. The prompt-injection scenario must produce no unauthorized reads, writes, or sends.
**Lands in:** Phases 04, 06A, 08, and 16; the evaluation plan §9.

## 26. Deployment units and containers

**Decide:** Which units deploy separately, and what scaling signal drives each? Are images built from one lock file, run as non-root, and pinned? Are liveness and readiness checked separately? Do migrations run as a one-shot step? Is the environment injected per service? Are answer keys kept out of images? Is there a clean-machine start?
**Cashflow:** API, worker, UI, and three MCP entry points from one image family, plus PostgreSQL, local identity, and telemetry. Initialization already provides `docker/compose.yaml` with the API and UI; later phases add services to it. Launch with `docker compose -f docker/compose.yaml up --build`, adding `--env-file .env` once a service needs a value from it.
**Lands in:** Deployment plan §§1–3; phase 17.

## 27. Operations and release

**Decide:** Is a release candidate frozen with all its versions? Are migrations compatible with running checkpoints? Is there a backup and restore drill? Is rollback exercised? Are SLOs *measured* before being promised? Is there a runbook for each failure class?
**Cashflow:** Runbooks cover model outage, MCP outage, stale data, delivery unknown, worker failure, tenant-access incident, cost spike, and release rollback. After a restore, reconcile with the provider's history before re-enabling dispatch.
**Lands in:** Deployment plan §§9–12; phase 16.

## 28. Demonstration and handoff

**Decide:** Does the walkthrough show success, a safe failure, and recovery? Are fake-model and real-model results labelled? Are untested integrations named? What does the handoff package contain?
**Cashflow:** Local login, tenant isolation, evidence search, approval, simulated send, and then the disputed invoice, stale data, payment after draft, a failed server, and restart and resume. Business savings are never claimed from synthetic data.
**Lands in:** Phase 19; `fde-engagement` close.
