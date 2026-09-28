---
status: written
family: Engagement
wave: 0
skill: fde-engagement
---

# Scoping

**Owns:** The first slice, the demo milestone, and what is explicitly out

**Family:** Engagement · **Wave:** 0 · **Paired skill:** `fde-engagement`

## When this card is needed

Once the problem, metric, and constraints are known, and again at the start of every increment afterwards. Also whenever scope is quietly growing — an unnoticed expansion is the usual reason an engagement ends with nothing demoable.

## The decisions

**A slice is only a slice if you can demo it.** These are the shapes a first slice can take.

| Option | Use when | Cost of being wrong |
|---|---|---|
| Thinnest vertical — trigger to visible result, logic stubbed | The wiring is the unknown | Looks trivial unless narrated; someone reads it as "barely started" |
| Riskiest-first spike | One step might be impossible and everything depends on it | Throwaway code, nothing demoable at the end of it |
| Highest-pain step only | One step dominates the cost and is self-contained | Not end to end, so it cannot be demonstrated working |
| Read-only or shadow slice | Writes are gated, risky, or not yet approved | No visible business effect yet — value has to be argued rather than shown |
| Widest happy path | Wiring is already proven; coverage is what was asked for | Defers every failure case to the end, where there is no time left |

Order slices by **risk, not ease**. Build the part most likely to be wrong while being wrong is still cheap. Risk concentrates in untested integrations, the accuracy floor of a model step, unverified data-quality assumptions, and handoffs to humans — never in CRUD, which is why starting with CRUD feels productive and defers every real question.

Size: **one sentence with no "and" in it.** If it needs an "and", it is two slices.

## Anti-patterns

**Layers, not slices.** "All the models, then all the endpoints, then the UI" demos nothing until the last day, and hides all integration risk in the final week.

**Silent stubs.** A named stub is sequencing; an unmentioned one is an oversight. The only difference is whether you said it.

**No exclusions.** A scope with no "not now" list is not a scope, and every later addition will feel reasonable in isolation.

**No demo milestone.** Without a named observable outcome, "done" becomes negotiable exactly when you cannot afford to negotiate.

**Starting with the easy part.** Produces visible progress and zero information.

## Production checks

- [ ] First slice describable in one sentence, no "and"
- [ ] Demo milestone named and agreed **before** building
- [ ] Slices ordered by risk, with the riskiest first
- [ ] An explicit "not now" list exists and has been shown to the sponsor
- [ ] Every stub has an owner and a date
- [ ] The slice runs end to end — trigger through to something a person can see

## Current defaults

`as of 2026-09` — First slice is the thinnest vertical path that proves the wiring, with the decision logic stubbed and that fact stated out loud. Correctness lands in slice two. Name the demo milestone before starting, and keep the "not now" list visible in [`context/session-notes.md`](../../context/session-notes.md).

## Pointers

- Cards: [problem-statement](problem-statement.md), [success-metrics](success-metrics.md), [constraints](constraints.md), [qualification](qualification.md)
- Long form: [../1-frame/scoping.md](../1-frame/scoping.md)
- Skill: [`fde-engagement`](../../.cursor/skills/fde-engagement/SKILL.md)
- Catalog index: [README.md](README.md)
