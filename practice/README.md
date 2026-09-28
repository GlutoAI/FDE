# Practice

Rehearsal scenarios, run against the scaffold under a clock. The point is not to pre-build solutions — it is to find out which step is slow while it is still cheap to fix.

Decision sheets: [wiki/catalog/](../wiki/catalog/README.md). Method: [wiki/mental-model.md](../wiki/mental-model.md). Do not treat catalog placeholders as written guidance.

Scenarios are hypothetical. Real ones arrive during the session.

## Scenarios

| # | Scenario | Exercises |
|---|---|---|
| 1 | A new record routes somewhere under an agreed rule | Record lifecycle, conditions, state, visible outcome |
| 2 | Free text needs model classification before a permitted action | Model/code boundary, schema validation, authority enforcement |
| 3 | A periodic report summarises a defined interval | Explicit window, aggregation, repeat runs, empty periods |
| 4 | A dashboard shows pending, completed, and **failed** work | End-to-end correctness, metric definitions, operational states |
| 5 | A duplicate event or a model timeout causes a failure | Reproduction, tracing, recovery design, narrated debugging |
| 6 | The rule changes halfway through | Clarify, re-scope, smallest responsible change, regression check |

Scenario 5 is the one most worth rehearsing, because it is the only one that practises being stuck in front of someone.

## How to run one

Set a timer for 20 minutes and run the full inner loop: clarify, narrate, build the thinnest slice, test in the open, show and ask. Narrate out loud, to an empty room if necessary — the failure mode under pressure is going silent, and that is a habit, not a knowledge gap.

Afterwards record, in `context/session-notes.md`: where the time actually went, what was looked up, and which step was slower than expected. That record is the real output — it tells you which wiki page to write next.

## Rules for rehearsal

**Do not use the interview-provided Claude key.** It stays unused until the session. Rehearse model steps against a stub that returns fixed structured responses; that exercises every line of your validation, routing, and failure handling without a single API call.

A stub also makes the point that a model-shaped interface should be substitutable — which is the same property that makes it testable later.
