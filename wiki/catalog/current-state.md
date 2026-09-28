---
status: written
family: Engagement
wave: 0
skill: fde-engagement
---

# Current state

**Owns:** Establishing what actually happens today, as opposed to what is documented or believed

**Family:** Engagement · **Wave:** 0 · **Paired skill:** `fde-engagement`

## When this card is needed

Before designing anything, and again whenever a design decision depends on "how do they do it now?" The documented process and the real one always differ, and the difference is usually exactly where the pain is — so this is not a formality, it is where the build gets scoped.

## The decisions

How you capture the current state determines what you see.

| Option | Use when | Cost of being wrong |
|---|---|---|
| Narrate one real recent case | Almost always — start here | Generalities hide the exceptions, and the exceptions are the build |
| "Tell me about the last one that was annoying" | You suspect the happy path is being described | You get the idealised process and discover the mess in week three |
| Process map across roles | Handoffs and queues are implicated | Over-modelling: weeks spent mapping a process you are about to replace |
| Read the artifacts — tickets, spreadsheets, exports | Volume matters, or memory is unreliable | Artifacts record the happy path; failures often are not logged anywhere |
| Shadow a live run | Descriptions have already proven unreliable | Calendar cost, and often not permitted |
| Count it — volume, time per item, error rate | You need a baseline to claim improvement later | Measuring a unit that is not the one that hurts |

**Asking for one real case beats asking for the general process.** People describe processes neutrally and cases honestly.

## Anti-patterns

**Documenting the documented process.** If it is already written down, read it before the meeting and use the meeting for what is not written down.

**Accepting "it's straightforward".** It never is. The follow-up that works: *"walk me through the last one anyway."*

**Missing the spreadsheet.** There is almost always an informal artifact — a sheet, a shared doc, a private queue — holding the state the real system does not. It will not be mentioned unless asked for directly.

**Skipping the failure path.** "What happens when it goes wrong today?" reveals the controls you are about to automate away.

**No baseline.** Without a number captured now, no improvement can be claimed later. The moment to measure is before you change anything.

## Production checks

- [ ] The step that actually hurts is named, not the process in general
- [ ] Volume and time-per-item recorded, with the date measured
- [ ] The current workaround — including informal artifacts — is documented
- [ ] The existing failure path and who notices is understood
- [ ] At least one real case has been traced end to end

## Current defaults

`as of 2026-09` — Read artifacts first, then trace one real recent annoying case out loud, then count the volume. Capture the baseline before touching anything, and date it. Treat any process description containing no exceptions as incomplete.

## Pointers

- Cards: [customer-interviews](customer-interviews.md), [problem-statement](problem-statement.md), [success-metrics](success-metrics.md)
- Long form: [../1-frame/discovery.md](../1-frame/discovery.md)
- Skill: [`fde-engagement`](../../.cursor/skills/fde-engagement/SKILL.md)
- Catalog index: [README.md](README.md)
