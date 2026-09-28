---
status: written
family: Engagement
wave: 0
skill: fde-engagement
---

# Issue to idea

**Owns:** Converting a complaint into a solvable, falsifiable bet

**Family:** Engagement · **Wave:** 0 · **Paired skill:** `fde-engagement`

## When this card is needed

The moment someone says *"we need an AI that…"*. That sentence contains a complaint and a proposed solution fused together, and they arrived fused. This card is the act of separating them — because the proposed solution is their hypothesis, not the problem, and building it directly skips the only step where you add value.

## The decisions

Given a real pain, these are the shapes a response can take. They are ordered roughly by how much they change the world.

| Option | Use when | Cost of being wrong |
|---|---|---|
| Remove the step entirely | It exists because of a constraint that no longer holds | You delete a control nobody documented and find out during an audit |
| Prevent the input upstream | The work is caused by bad data or a broken earlier step | Longest path to value; often owned by someone who did not ask you |
| Automate the step as-is | The step is correct, just manual and high volume | **You automate waste — the same wrong outcome, faster and at scale** |
| Change who or what does it — route, escalate, reassign | The work is fine; the assignment is wrong | Political rather than technical, and may not be yours to change |
| Surface information so a human decides faster | The judgment is genuinely human and low volume | Reads as "just a dashboard" and gets undersold, even when correct |
| Do nothing yet — measure first | The pain is asserted but unmeasured | Looks passive; costs credibility if the pain is real and visible |

**Automating the step as-is is the default everyone reaches for, and it is the one with the sharpest failure mode.** Ask why the step exists before making it faster.

A bet is stated so it can be wrong: *"if we do A, then B should move from x to y."* If no observation could falsify it, it is not a bet, it is a wish.

## Anti-patterns

**Accepting the implied solution.** "We need an agent that reads these emails" is a solution. The problem is whatever happens because the emails are read slowly or badly.

**Automating a workaround.** The workaround exists because something upstream is broken. Automating it makes the breakage permanent and much harder to see.

**Solving the loudest complaint.** Volume of complaint correlates with proximity to you, not with cost to the business.

**A bet with no number.** Unfalsifiable bets cannot be won, which means the engagement cannot be declared successful.

## Production checks

- [ ] The complaint and the proposed solution have been separated, in writing
- [ ] You can state why the step exists, not only what it does
- [ ] The bet is falsifiable — names a metric, a direction, and a rough size
- [ ] Someone other than you would recognise this as their problem

## Current defaults

`as of 2026-09` — Separate complaint from request first. Ask "why does this step exist?" before "how do we speed it up?". Prefer preventing upstream over automating downstream when the upstream owner is reachable; otherwise automate the step and record the upstream issue as a known compromise rather than letting it disappear.

## Pointers

- Cards: [current-state](current-state.md), [problem-statement](problem-statement.md), [business-decisions](business-decisions.md), [qualification](qualification.md)
- Long form: [../1-frame/discovery.md](../1-frame/discovery.md)
- Skill: [`fde-engagement`](../../.cursor/skills/fde-engagement/SKILL.md)
- Catalog index: [README.md](README.md)
