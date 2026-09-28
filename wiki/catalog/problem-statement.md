---
status: written
family: Engagement
wave: 0
skill: fde-engagement
---

# Problem statement

**Owns:** The written statement, with a number in it, that the sponsor would sign

**Family:** Engagement · **Wave:** 0 · **Paired skill:** `fde-engagement`

## When this card is needed

After discovery, before design. This is the artifact that makes everything downstream checkable: a scope argument, a design tradeoff, and a closing demo all resolve by pointing back at it. Write it even when nobody asked for it — the act of writing is what exposes which of the four sentences you are still guessing at.

## The decisions

The pain is one thing; the **frame** you write it in is a choice, and it determines whose budget pays and what success means.

| Option | Use when | Cost of being wrong |
|---|---|---|
| Labour cost — hours × rate | Process is manual and headcount-heavy | Invites "then hire cheaper people" as a competing answer |
| Error or rework rate | Quality is the pain and mistakes are expensive | Needs a measured baseline, which often does not exist yet |
| Cycle time | Someone waits — a customer, a close, a shipment | The business may genuinely tolerate the delay; annoyance is not cost |
| Capacity ceiling | Growth is the driver and the process will not scale | Speculative until the growth is real; easy to dismiss |
| Risk or compliance exposure | Audit or regulatory pressure is the trigger | Hard to size, and reads as fear-selling if not concrete |

Pick the frame the **sponsor's budget** already speaks. A statement written in a frame nobody funds is correct and useless.

The shape that works:

> **[Who]** experiences **[what]**, **[how often]**, costing **[number]**. Today they **[current workaround]**. Success is **[metric]** moving from **[x]** to **[y]** by **[when]**.

## Anti-patterns

**No number.** "Manual review takes too long" cannot be improved, demonstrated, or defended at renewal.

**A solution in disguise.** "We need an agent to triage incoming records" describes a build, not a problem. Delete every implementation noun and see whether a problem survives.

**A statement only you would sign.** If the sponsor would not say it unprompted in their own words, you wrote your understanding of their problem, not their problem.

**Precision theatre.** A fabricated number is worse than a range. `~200/week, unmeasured` is honest; `194/week` invented is a trap you will be held to.

## Production checks

- [ ] Contains a number, and the number's source is stated
- [ ] Contains no implementation nouns
- [ ] The sponsor has heard it back and agreed, in their words
- [ ] Names what happens if nothing is done
- [ ] Baseline is dated — see [success-metrics](success-metrics.md)

## Current defaults

`as of 2026-09` — Four sentences, one frame, one number with its provenance attached. Where the number is unmeasured, write it as an explicit estimate with a range rather than omitting it. Re-read it aloud at the closing demo; if it no longer matches what was built, say so rather than quietly restating the goal.

## Pointers

- Cards: [issue-to-idea](issue-to-idea.md), [success-metrics](success-metrics.md), [business-decisions](business-decisions.md), [stakeholder-map](stakeholder-map.md)
- Long form: [../1-frame/scoping.md](../1-frame/scoping.md)
- Skill: [`fde-engagement`](../../.cursor/skills/fde-engagement/SKILL.md)
- Catalog index: [README.md](README.md)
