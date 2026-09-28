---
status: written
family: Engagement
wave: 0
skill: fde-engagement
---

# Constraints

**Owns:** Capturing what limits the solution — systems, access, compliance, latency, budget — and deciding how to respond when one bites

**Family:** Engagement · **Wave:** 0 · **Paired skill:** `fde-engagement`

## When this card is needed

Day zero, before design, because the most expensive constraints are the ones with lead times rather than the ones with technical difficulty. Return to it whenever a design assumes access to something nobody has confirmed you can reach.

## What to capture

- **System access and credentials** — which systems, which environment, who grants it, how long it takes
- **Data handling** — PII, residency, retention, what may leave the network, what may reach a model provider
- **Compliance and audit** — what must be recorded, retained, and producible later
- **Latency** — is this interactive, near-real-time, or batch
- **Cost ceiling** — per run, per month, and who notices when it is exceeded
- **Veto holders** — who can stop this, and what would make them
- **Vendor and model approval** — whether this provider is already cleared

## The decisions

When a constraint bites, these are the responses.

| Option | Use when | Cost of being wrong |
|---|---|---|
| Design within it | The constraint is physics, policy, or law and will not move | You accept a permanently worse solution that nobody revisits |
| Negotiate it | It is policy rather than physics, and someone owns it | Time and political capital, spent before you have credibility |
| Defer the slice that needs it | It blocks only part of the scope | Scope shrinks — and the deferred part may have held the value |
| Stub it and proceed | Access is genuinely coming, just late | All integration risk concentrates at the end, where there is no slack |
| Stop | The constraint removes the value entirely | None if true; serious credibility damage if called prematurely |

**Access is the number one schedule risk on agentic engagements** — ahead of model quality, ahead of integration complexity. It is a queue you do not control. Request on day zero, even before you are sure you need it.

## Anti-patterns

**Assuming access.** The single most common week-three surprise.

**Discovering data residency after building.** It invalidates architecture, not just configuration.

**Stubbing without a date.** A stub with no agreed access date is a deferred failure, not a plan.

**Credentials in the wrong place.** Never in code, prompts, config files, reference docs, or browser-visible code. Read from the environment. Do not make a live call merely to check a key works.

**Treating a cost ceiling as advisory.** Without an enforced cap it is a number in a document, and the first expensive week is a surprise.

## Production checks

- [ ] Credentials requested on day zero, with the granting person and lead time recorded
- [ ] The data path is documented — what leaves the network and what reaches a model provider
- [ ] Retention and audit requirements written down
- [ ] Cost ceiling stated **and enforced in code**, not just agreed
- [ ] No secret appears in any tracked file; all read from the environment
- [ ] Every stub has an owner and a date

## Current defaults

`as of 2026-09` — Request access before design. Assume any external model call is a data-egress event and confirm it is permitted before depending on it. Enforce a hard per-run and per-day cap in code from the first commit; a ceiling that is not enforced is not a ceiling.

## Pointers

- Cards: [stakeholder-map](stakeholder-map.md), [business-decisions](business-decisions.md), [scoping](scoping.md), [cost-and-budgets](cost-and-budgets.md), [permissions-and-blast-radius](permissions-and-blast-radius.md), [security-agentic](security-agentic.md)
- Long form: [../1-frame/discovery.md](../1-frame/discovery.md) · always-on rules: [`.cursor/rules/engagement.mdc`](../../.cursor/rules/engagement.mdc)
- Skill: [`fde-engagement`](../../.cursor/skills/fde-engagement/SKILL.md)
- Catalog index: [README.md](README.md)
