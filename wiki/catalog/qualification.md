---
status: written
family: Engagement
wave: 0
skill: fde-engagement
---

# Qualification

**Owns:** Rule vs workflow vs agent — which rung this problem actually needs

**Family:** Engagement · **Wave:** 0 · **Paired skill:** `fde-engagement`

## When this card is needed

After the problem is stated, before any design. Also reach for it whenever someone describes a step as needing AI — this card is the check on that claim. It decides the **rung**; once a rung is chosen, [model-vs-code](model-vs-code.md) decides what the model is allowed to decide *within* it.

## The decisions

The rungs differ by one thing: **who chooses the next step.**

| Option | Use when | Cost of being wrong |
|---|---|---|
| Don't automate | Volume is low, or the process is still changing weekly | None if true — the cheapest correct answer there is |
| Improve the manual process | The process is broken rather than slow | Reads as unambitious; frequently right anyway |
| Rule / code | Inputs enumerable, logic fits in a table, table is stable | If the input is genuinely fuzzy: brittle, and an endless exception list |
| Workflow — model in fixed steps | Steps known in advance; model extracts, classifies, or drafts | If steps truly vary per case, you rebuild the pipeline constantly |
| Agent — model chooses steps | The steps genuinely cannot be known until runtime | Cost, latency, non-reproducible failures; needs evals instead of assertions |
| Human plus better information | Judgment is genuinely human, volume is modest | Gets dismissed as "just a dashboard" even when it is the right answer |

**The test: if you can write the assertion, write the code.** Being able to state the correct output for every input means you have described a function — so write the function.

Most problems presented as needing an agent are workflows. A meaningful minority are rules. The word "AI" attaches to the *project*, and then leaks onto every step inside it.

## Anti-patterns

**Calling a workflow an agent.** Costs nothing technically and everything in clarity — the accurate word makes testing, cost, and failure handling all easier to reason about.

**A threshold comparison in a prompt.** Slower, costlier, untestable, and wrong some percentage of the time, in exchange for nothing.

**Climbing a rung for the demo.** Autonomy is impressive in a demo and expensive in production. Climb when a measurement forces it, and write down the measurement.

**Skipping "don't automate".** If it is never on the list, the list is a sales document rather than an analysis.

## Production checks

- [ ] The chosen rung is named out loud, using the accurate word
- [ ] Why the rung below is insufficient is stated in one sentence
- [ ] The measurement that forced the climb is recorded, if one exists
- [ ] The model-vs-code split within the rung is written down
- [ ] Per-run cost at the chosen rung has been estimated

## Current defaults

`as of 2026-09` — Start at the lowest rung that could work and climb only under evidence. Default split: **the model classifies, extracts, and drafts; code decides, routes, and writes.** Arithmetic, thresholds, authorisation, and state transitions stay in code regardless of rung.

## Pointers

- Cards: [model-vs-code](model-vs-code.md) — what the model may decide once a rung is chosen; [agent-pattern-choice](agent-pattern-choice.md) — which pattern within the agent rung; [business-decisions](business-decisions.md), [issue-to-idea](issue-to-idea.md)
- Long form: [../1-frame/qualification.md](../1-frame/qualification.md) · pattern ladder in [../2-design/agentic-system-design.md](../2-design/agentic-system-design.md)
- Skill: [`fde-engagement`](../../.cursor/skills/fde-engagement/SKILL.md)
- Catalog index: [README.md](README.md)
