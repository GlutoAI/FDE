---
status: written
family: Engagement
wave: 0
skill: fde-engagement
---

# Customer interviews

**Owns:** How to run discovery: which questions, in what order, when to stop asking

**Family:** Engagement · **Wave:** 0 · **Paired skill:** `fde-engagement`

## When this card is needed

At the very start, and every time scope shifts afterwards. You reach for this when you have a request but not a problem — someone has told you what to build and you do not yet know what hurts. Also reach for it mid-build, when an assumption you have been carrying silently turns out to matter.

## The decisions

Pick the **mode** first — it determines what you can learn and what it costs.

| Option | Use when | Cost of being wrong |
|---|---|---|
| Artifact-first — read tickets, sheets, logs, code before asking | Data exists and is richer than memory | Skipping it means you burn interview time on facts you could have read, and ask leading questions |
| One deep interview with the person who does the work | A single role owns the process end to end | You encode one person's idiosyncrasy as the specification |
| Group walkthrough across roles | The pain is in handoffs between teams | The loudest voice defines the process; quiet exceptions stay hidden |
| Shadow a real run | Stated process and actual process are known to differ | Expensive in calendar time, and often not permitted |
| Async written questions | Schedules do not align, or stakes are low | No follow-ups, and no silence — you lose the qualifier that arrives after the pause |

**Stop when the next answer would not change what you build.** That is the whole stopping rule. Curiosity beyond that point is billed to someone.

Within a session, the ordering that works is: *worst-case question → scope question → access question*. In that order, because the first reframes the conversation from features to consequences and the other two get cheaper once it has.

## Anti-patterns

**Requirements gathering.** Transcribing what they asked for and building it. They stated a hypothesis, not a problem.

**Stacked questions.** Three questions in one breath gets the last one answered and the others lost.

**Filling silence.** The three seconds after someone finishes is where *"...although the ones from the regional team come in differently"* arrives. That qualifier is usually the hardest part of the build.

**Asking what you could read.** It signals you did not prepare, and it spends the goodwill you need for the questions only they can answer.

**Vocabulary drift.** They say "cases", you say "tickets". Reads as not listening, and their nouns encode distinctions their business actually makes.

## Production checks

- [ ] Can state problem, success, never-do, and first slice in four sentences they would agree with
- [ ] Every open assumption has been said out loud, not carried silently
- [ ] The person who gets blamed when it goes wrong has been identified and spoken to
- [ ] Their vocabulary is written down and being used

## Current defaults

`as of 2026-09` — Artifact-first, then one deep interview with whoever does the work daily, then a short group session only if handoffs are implicated. In a timeboxed session, two or three questions before touching the keyboard, then keep asking as you go. Discovery is a habit, not a phase you exit.

## Pointers

- Cards: [current-state](current-state.md), [stakeholder-map](stakeholder-map.md), [constraints](constraints.md), [issue-to-idea](issue-to-idea.md)
- Long form: [../1-frame/discovery.md](../1-frame/discovery.md) — the full question bank and why those questions
- Skill: [`fde-engagement`](../../.cursor/skills/fde-engagement/SKILL.md)
- Catalog index: [README.md](README.md)
