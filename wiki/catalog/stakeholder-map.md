---
status: written
family: Engagement
wave: 0
skill: fde-engagement
---

# Stakeholder map

**Owns:** Who decides, who uses it, who gets blamed — and whose interest wins when they conflict

**Family:** Engagement · **Wave:** 0 · **Paired skill:** `fde-engagement`

## When this card is needed

In the first week, and again the moment two people give you contradictory requirements. The contradiction is not usually confusion — it is two roles with different exposure, and resolving it requires knowing which role you are serving.

## The roles

Five, and they are rarely the same person:

- **Sponsor** — pays, and gets asked about it at their review
- **Operator** — uses it daily; decides whether it is actually adopted
- **Owner of record** — accountable when it produces a wrong outcome
- **Gatekeeper** — security, compliance, IT, data governance; can veto but cannot approve
- **Beneficiary** — downstream, often absent, often the reason any of it matters

## The decisions

When interests conflict, you are choosing whose to optimise for.

| Option | Use when | Cost of being wrong |
|---|---|---|
| Optimise for the operator | Adoption is the main risk | The sponsor's metric does not move, so it does not get renewed |
| Optimise for the sponsor | Funding is the main risk | Operators route around it; usage dies quietly and nobody reports it |
| Optimise for the owner of record | Regulated, or errors are expensive and attributable | Over-gated, slow, and the value never materialises |
| Serve the gatekeeper early | Access or approval is on the critical path | Weeks in review; the most common schedule slip there is |
| Escalate the conflict rather than resolve it | Two funded stakeholders genuinely disagree | Looks like indecision — but silently picking a side is worse |

**The gatekeeper is the one discovered late.** They cannot approve your project but they can stop it, and their queue is measured in weeks. Contact them before you need them.

## Anti-patterns

**Treating the room as the map.** The person briefing you is one role. Assume the other four exist until shown otherwise.

**No operator contact.** Building from the sponsor's description produces something demo-friendly that the people doing the work will not use.

**Finding security in week three.** Access is a lead-time problem, not a technical one. Ask on day zero.

**Ignoring the owner of record.** They will set the approval requirements, and if they are surprised late they will set them conservatively.

## Production checks

- [ ] A named person for each of the five roles, or an explicit "none"
- [ ] The operator has been spoken to directly, not via the sponsor
- [ ] The gatekeeper has been contacted and their lead time is known
- [ ] The owner of record has stated what they need to see before go-live
- [ ] Known conflicts between roles are written down, not smoothed over

## Current defaults

`as of 2026-09` — Map all five in week one. Contact the gatekeeper before the build starts, not when access is needed. Where sponsor and operator conflict, serve the operator on workflow and the sponsor on reporting — that combination usually satisfies both without a fight.

## Pointers

- Cards: [customer-interviews](customer-interviews.md), [business-decisions](business-decisions.md), [constraints](constraints.md), [success-metrics](success-metrics.md)
- Long form: [../1-frame/discovery.md](../1-frame/discovery.md)
- Skill: [`fde-engagement`](../../.cursor/skills/fde-engagement/SKILL.md)
- Catalog index: [README.md](README.md)
