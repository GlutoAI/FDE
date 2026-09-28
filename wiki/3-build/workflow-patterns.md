# Workflow Patterns

> Decision sheets (placeholders until filled): [idempotency](../catalog/idempotency.md), [commit-boundaries](../catalog/commit-boundaries.md), [triggers](../catalog/triggers.md), [human-gates](../catalog/human-gates.md). This page is the long form for the three operational shapes.

The three shapes that operational automation almost always takes: **record-triggered work**, **approval**, and **scheduled reporting**. Most "build an agent for this" requests decompose into one or two of them.

Each section gives the flow, the decisions that must be explicit, and the failure modes that separate a demo from something a business can depend on.

## Pattern 1 · Record-triggered workflow

```
committed record → trigger → load authorized context → business rules
    → optional model interpretation → validate → permitted action → persist outcome
```

### What must be explicit

| Question | Why it decides the design |
|---|---|
| Where does the trigger originate? | In-process hook, polling, webhook, or queue — each has different delivery guarantees |
| Is the record committed when it fires? | See commit boundaries below; this is the most common silent bug |
| What decides the outcome? | Model or code — state it plainly; it determines what is testable |
| What happens on redelivery? | Every trigger source will eventually deliver twice |
| How does the outcome become visible? | An outcome nobody can see cannot be supported |

### Commit boundaries

**Triggered work must act on committed state.** Firing the trigger inside the same transaction that created the record means a later rollback leaves you having already sent the email, called the API, or charged the card — an effect for a record that does not exist.

Fire after commit. If the effect must not be lost when the process dies between commit and dispatch, write the intent to the database *in* the transaction and dispatch from that record afterwards — the outbox pattern. Both halves in one transaction, delivery separate.

The cheap version, which is usually the right first version: commit, then dispatch, and accept that a crash in the gap means a missed trigger — *provided* you have said so out loud and there is a way to replay.

### Idempotency

A trigger that fires twice must not produce two effects. This is not hypothetical: webhooks retry, queues deliver at-least-once, users double-click, and a restart replays.

The pattern that works: derive a stable key from the logical unit of work — `(record_id, action)`, not a random UUID — and put a **unique constraint on it in the database.** Application-level "check then act" loses the race; the constraint does not.

> Do not rely on a prompt instruction to prevent duplicates. A model cannot know what already happened, and the database can.

Make the downstream action idempotent too where the API allows it — most payment and messaging APIs accept an idempotency key precisely for this.

## Pattern 2 · Approval workflow

```
pending request → authenticated approver → authorize → validate current state
    → legal transition → permitted follow-up action → audit entry
```

### What must be explicit

| Question | Why |
|---|---|
| Who has authority, on what, up to what limit? | Authority is a data question, not a UI question |
| Which transitions are legal? | `pending → approved` is legal; `approved → approved` is not |
| What happens on a repeated or concurrent decision? | Two approvers clicking at once must not both win |
| What is recorded? | Who, what, when, on what evidence — immutable |
| How does pending work resume? | A request waiting on a human is a paused run that must survive a restart |

### Authority and concurrency

**Validate the actor and the current state at the moment of the transition**, not when the page was rendered. The approver's permissions may have changed, and the request may already have been decided — a thirty-minute-old page is a stale read.

Guard the transition in the write itself:

```sql
UPDATE requests SET status = 'approved', decided_by = ?, decided_at = ?
 WHERE id = ? AND status = 'pending'
```

Zero rows updated means someone got there first. Treat that as a normal outcome with a clear message, not a crash — and never as success.

Separation of duties matters and is cheap to enforce: the submitter should not be the approver, and whoever created a vendor should not approve its payments. One `WHERE` clause.

### The audit entry is the product

For anything involving money or compliance, the audit trail is not a logging detail — it is a deliverable. Append-only, one row per decision, recording actor, action, timestamp, the state before, and the evidence relied on. Never update it; correct by appending a reversal.

If a model contributed, record what it returned and which version or prompt produced it. "Why was this approved?" must be answerable six months later.

## Pattern 3 · Scheduled report

```
scheduled invocation → explicit window → query and aggregate → optional narrative
    → persist and deliver → record run status
```

### The design rule that makes this testable

**The report function takes an explicit window and is callable directly. The scheduler is a thin caller.**

```python
def build_report(window_start: datetime, window_end: datetime) -> Report: ...
```

Not `build_daily_report()` that reads the clock internally. With the window as a parameter you can test month boundaries, empty periods, and leap days in milliseconds; with the clock inside, you can only test by waiting or by monkeypatching time. This single choice is the difference between a scheduled job that is testable and one that is not.

It also gives you backfill and replay for free, and it makes a manual "run it now" button trivial.

### Windows

**Half-open intervals — `[start, end)`.** Closed intervals double-count the boundary record in adjacent periods; this is the classic reporting bug, and it is invisible until someone reconciles two reports and finds one item twice.

**State the time zone.** "Yesterday" is not a fact until you say whose yesterday. Store timestamps in UTC, compute windows in the business time zone, and write down which one you chose.

**Decide about late data.** A record that arrives after its window closed either never appears, or appears in the next report, or triggers a restatement. All three are defensible; silently choosing one is not.

### Run status

Each firing gets a row: the window, when it started, whether it succeeded, and what it produced. Without it you cannot answer "did Tuesday's report run?" — and the absence of a report is indistinguishable from a period with nothing in it.

Handle the boring cases explicitly, because they are the ones that occur: an **empty period** produces a report saying zero, not a crash and not silence. A **repeated run** for the same window is idempotent — same key, same constraint as above. A **missed run** is visible and replayable, which the explicit-window signature already gives you.

## Where the model belongs

Across all three patterns the split is the same:

| Deterministic code | Model |
|---|---|
| Arithmetic and totals | Interpreting free text |
| Threshold comparisons | Classifying ambiguous content |
| Authorization and authority | Drafting explanations and summaries |
| Legal state transitions | Extracting structure from unstructured input |
| Query aggregation | Narrating verified numbers |

**The model proposes; application code validates and decides.** With tool use, the model returns a *proposed* call — your code executes it, and your code enforces authority and validation. A malformed or hostile model response must not be able to cause an unauthorized or invalid action, and the only way to guarantee that is to put the check on the execution side.

So: validate the model's output against a schema before it touches anything. On failure, route to a human — never guess, and never retry blindly into the same action.

Note that the exercise may *call* a fixed automation an agent. Clarify the required behaviour rather than arguing about the word.

## Dashboards

Dashboards read the authoritative business and workflow state. **Do not invent a parallel agent architecture to display state that already exists.**

What makes an operational dashboard useful rather than decorative: pending work, completed work, **failed runs**, report periods, and the definition behind each metric. Failures are the half people omit, and they are the half an operator needs.

Every metric needs a stated definition and provenance — "approved this week" is ambiguous about time zone, about whether it counts decisions or requests, and about which table it came from.

Include the loading, empty, and error states. An empty dashboard and a broken dashboard look identical if neither is designed.

## The boundary test cases

For any feature in these patterns, this set catches most of what matters:

1. A valid record through the happy path.
2. **Both sides of a threshold — and exactly on it.** The `>` versus `>=` bug is the single most common conditional defect.
3. Missing or malformed input.
4. **The same trigger delivered twice.**
5. An unauthorized actor attempting the action.
6. The model unavailable, slow, or returning something invalid.
7. An empty reporting period.
8. The same scheduled window run twice.

Pick the ones that apply to the feature at hand rather than implementing all eight for everything. But 2 and 4 apply nearly always, and nearly always find something.
