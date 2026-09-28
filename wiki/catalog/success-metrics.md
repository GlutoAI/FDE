---
status: written
family: Engagement
wave: 0
skill: fde-engagement
---

# Success metrics

**Owns:** What number moves, how it is measured, and what guards it from being gamed

**Family:** Engagement · **Wave:** 0 · **Paired skill:** `fde-engagement`

## When this card is needed

Immediately after the problem statement, and before the first line of code — because the baseline has to be captured **before** anything changes. A metric agreed after the build is a metric chosen to flatter the build.

## The decisions

| Option | Use when | Cost of being wrong |
|---|---|---|
| Throughput — items per period | A backlog is the visible pain | Rises while quality silently falls |
| Cycle time | Someone is waiting | Gameable by batching and cherry-picking the easy items |
| Touch rate — % handled without a human | Labour reduction is the goal | Rises while error rate rises; meaningless unpaired |
| Error or escape rate | Quality is the pain | Requires ground truth, which frequently does not exist yet |
| Cost per item | The sponsor is finance | Model spend can quietly swallow the labour saving |
| Adoption or usage | The main risk is that nobody uses it | A proxy for value, not value |

**Pair every volume metric with a quality metric.** Throughput, cycle time, and touch rate are all improvable by doing the work worse. The pairing — the *guardrail metric* — is what makes the headline number honest.

A guardrail is a number that must **not** move: escape rate, appeal rate, rework rate, or cost per item.

## Anti-patterns

**"Reduce manual work"** with no number. Unmeasurable, therefore undemonstrable, therefore unfunded next cycle.

**Measuring the model instead of the business.** Classification accuracy is a debugging metric. It is not what anyone is paying for, and a system can improve on it while the business outcome worsens.

**No baseline.** Without a dated before-number there is no claim to make at the end, only an assertion.

**A single metric.** One number is always gameable. Two — one to move, one to hold — is the minimum honest set.

**Measuring what is easy.** The instrumented thing is rarely the thing that hurts.

## Production checks

- [ ] Baseline measured and **dated**, before any change ships
- [ ] Measurement method written down and reproducible by someone else
- [ ] A guardrail metric named, with the threshold that would count as harm
- [ ] The sponsor agrees this is the number they care about
- [ ] Instrumentation exists to measure it after launch, not just before

## Current defaults

`as of 2026-09` — One headline metric plus one guardrail, both baselined and dated before the build starts. For anything with model spend, track cost per item from day one — it is the number most often discovered late, and the one most likely to reverse the business case.

## Pointers

- Cards: [problem-statement](problem-statement.md), [current-state](current-state.md), [business-decisions](business-decisions.md), [eval-design](eval-design.md), [cost-and-budgets](cost-and-budgets.md)
- Long form: [../1-frame/scoping.md](../1-frame/scoping.md)
- Skill: [`fde-engagement`](../../.cursor/skills/fde-engagement/SKILL.md)
- Catalog index: [README.md](README.md)
