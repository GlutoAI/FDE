---
status: written
family: Engagement
wave: 0
skill: fde-engagement
---

# Business decisions

**Owns:** Go / no-go, buy vs build vs configure, and whose budget pays

**Family:** Engagement · **Wave:** 0 · **Paired skill:** `fde-engagement`

## When this card is needed

Once the problem is stated and before design starts. Also any time the build is about to grow past what was agreed — a scope expansion is a fresh buy-vs-build decision wearing a small hat.

## The decisions

| Option | Use when | Cost of being wrong |
|---|---|---|
| Build custom | The workflow is the differentiator, or no vendor fits the actual process | You now own maintenance, on-call, and model spend forever |
| Buy or configure a vendor | Commodity problem, credible vendors exist | Integration limits found late; roadmap is not yours; per-seat cost scales against you |
| Configure the system they already own | The existing platform does most of it already | Discovering the platform's hard limit after committing publicly |
| Improve the manual process first | The process is broken, not the tooling | Reads as unambitious — and is very often the correct answer |
| Defer or decline | Value does not clear the bar | Credibility damage if the pain is real, visible, and you walked |

**Whose budget pays determines the metric.** Operations money means the metric is hours. Risk money means the metric is exposure. Product money means the metric is a customer outcome. The same build succeeds or fails depending on which one was funding it, so find out before you choose what to optimise.

Ask directly: *"who is paying for this, and what do they get asked about in their quarterly review?"*

## Anti-patterns

**Building because the meeting was about building.** By the time you are in the room the decision often feels made. It has not been tested against buy or configure.

**Not asking who pays.** You then optimise for the person talking, who is frequently not the person funding it.

**Ignoring the run cost.** A custom build has a per-run model bill and an on-call rota. Compare it against the vendor's licence honestly, including the year-two number.

**Treating "do nothing" as failure.** It is a real option with a real cost, and pricing it makes every other option legible.

## Production checks

- [ ] Named sponsor and named budget line
- [ ] Buy and configure were explicitly considered and rejected with a reason
- [ ] The cost of doing nothing is stated
- [ ] Ongoing run cost — model spend, maintenance, support — is estimated, not just build cost
- [ ] Who supports this in year two is named

## Current defaults

`as of 2026-09` — Default to the cheapest reversible option that tests the bet. Prefer configure over buy, and buy over build, unless the workflow is genuinely the differentiator. Price year-two run cost alongside build cost; agentic systems carry a recurring bill that traditional software does not, and it is routinely left out of the comparison.

## Pointers

- Cards: [problem-statement](problem-statement.md), [qualification](qualification.md), [stakeholder-map](stakeholder-map.md), [constraints](constraints.md)
- Long form: [../1-frame/qualification.md](../1-frame/qualification.md)
- Skill: [`fde-engagement`](../../.cursor/skills/fde-engagement/SKILL.md)
- Catalog index: [README.md](README.md)
