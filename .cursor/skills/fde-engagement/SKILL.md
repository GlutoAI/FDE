---
name: fde-engagement
description: How to run a client-facing engineering engagement - discovery questions to ask before building, qualifying whether a problem deserves an agent at all, slicing scope into demoable increments, narrating a plan before writing code, taking feedback mid-task, handling being stuck, and running the closing walkthrough. Use at the start of any task, whenever scope or requirements are unclear, before making a visible technical choice, when blocked, and when presenting finished work.
---

# FDE Engagement

Working with a client is a loop: **clarify → narrate → build the thinnest slice → test in the open → show and ask**. Run it in minutes, not days. The difference between an engineer and a consultant is that the client knows what you are about to do and had a chance to stop you.

## Non-negotiables

- [ ] Asked at least one clarifying question before writing code
- [ ] Stated the plan out loud before executing it
- [ ] Built the thinnest slice that runs end to end, not a layer
- [ ] Named the tests before writing them
- [ ] Acted on every hint given, visibly and immediately
- [ ] Said what is *not* done and what you would do next

## Open a task

Never start with code. Three moves, about ninety seconds:

1. **Restate the goal** in your own words. Cheap, and it catches a mismatch before it costs anything.
2. **Ask one or two questions**, not five. Pick the ones whose answers change what you build.
3. **State the plan and the first slice.** Then start.

> "So the goal is X, and success looks like Y — have I got that right?"
> "Before I start: [question]. That changes whether I [A] or [B]."
> "Here's my plan — [step 1], then [step 2]. I'll build the smallest version that runs end to end first, then we look at it together."

## Discovery questions

Ask the ones whose answers change the build. Ranked by value per second:

| # | Question | What it surfaces |
|---|---|---|
| 1 | **"What's the worst thing this could do by mistake?"** | Cost of error, guardrails, approval design — all in one |
| 2 | "Walk me through what happens today, start to finish." | The real process, including the step nobody documents |
| 3 | "How many of these happen in a week?" | Scale, latency budget, whether cost matters |
| 4 | "What happens when it goes wrong today? Who notices?" | Current controls, who to page, what "broken" means |
| 5 | "If this worked perfectly, what would you stop doing?" | The actual value, in their words |
| 6 | "Who has to believe this works for it to keep running?" | The real stakeholder, often not the person talking |
| 7 | "What systems does it need to touch, and do I have access?" | Integration surface and the blocker you'd hit in hour two |
| 8 | "If we could only fix one step this week, which hurts most?" | The first slice, chosen by them |

Question 1 is the highest-leverage question in the set. It reframes the conversation from features to consequences, which is where production thinking lives.

## Qualify before you build

Climb only as far as the problem forces. Each rung costs latency, spend, and debuggability.

| Rung | Use when | Cost |
|---|---|---|
| **Rule / code** | Inputs enumerable, logic fits in a table | Cheapest, fastest, fully testable |
| **Workflow** (model in fixed steps) | Steps known in advance; model does the fuzzy parts — extract, classify, draft | Moderate |
| **Agent** (model picks steps) | The steps genuinely cannot be known until runtime | Highest on all three |

**Saying "this shouldn't be an agent" is a credibility move, not a lost sale.** A threshold comparison, a lookup, or a fixed routing table is code. Putting it in a prompt makes it slower, costlier, untestable, and wrong some percentage of the time.

> "I'd actually keep that part in code — it's a fixed rule, so it should be deterministic and testable. I'd use the model for [the genuinely fuzzy part]."

## Slice the scope

**A slice is only a slice if you can demo it.** One trigger, one decision, one action, visible end to end. Layers are not slices — "all the models, then all the endpoints" demos nothing until the last day.

> "I'm going to do one narrow path all the way through first — [trigger] to [visible result]. Once that's real we widen it."

Order slices by risk, not by ease. Build the part most likely to be wrong first, while there is still time to be wrong about it.

## Narrate while building

Say the *why*, not the keystrokes. One line per meaningful decision.

| Moment | Say |
|---|---|
| Making a tradeoff | "Two options: A is faster to build, B is more robust. Given [their constraint], I'd take A — sound right?" |
| A deliberate shortcut | "I'm stubbing this for now and flagging it, so it doesn't look finished." |
| A design choice worth defending | "I'm putting this in code rather than the prompt — it's a fixed rule, so I want it deterministic and testable." |
| Before tests | "I'll test three things: the happy path, the boundary at exactly the limit, and what happens when [dependency] is down." |
| Something you'd do differently with more time | "In production I'd add [X] here. For now I'm doing [Y] so we have something running." |

Silence for more than a minute or two reads as being stuck. Narrate or ask.

## Take a hint

Hints are the test. A hint acted on visibly scores far higher than a correct original answer defended.

| Do | Don't |
|---|---|
| "Good catch — changing that now." *(then change it)* | Explain at length why the original was defensible |
| "Say more about that?" | Nod and continue as before |
| "That's better, because [reason] — thanks." | Treat it as criticism to absorb silently |

If you genuinely disagree, disagree once, briefly, then defer:

> "I'd gently push back — [reason]. But it's your call, and if you'd rather [their way] I'll do that."

## When stuck

Being stuck is expected. Being *silently* stuck is the failure. Narrate the hypothesis, not the confusion.

> "I'm getting [exact error text]. My first guess is [X] — let me check [specific thing]."
> "I haven't hit this one before. Give me thirty seconds to look it up."

Looking things up is normal engineering; doing it out loud is the professional version. Timebox it — about two minutes, then ask.

> "I've spent a couple of minutes on this. Do you know if [specific thing] is set up in this environment?"

Asking where something lives or how a piece works is expected and costs you nothing.

## Explain what the AI is doing

When a model is involved, be able to say — unprompted — what is model judgement and what is code.

> "The model does one job here: read this and return a structured classification. It doesn't decide the outcome — that's this function, which compares against the rule. So the decision is deterministic and I can unit-test it."

Cover, briefly: what goes into the prompt, what shape comes back, what happens when it returns something invalid, and what it costs per run. If you cannot explain why the model returned something, you cannot support it in production.

## Close

Five beats, three minutes:

1. **The problem**, one sentence, in their words.
2. **It working**, on a real case.
3. **It failing safely**, on a bad case. ← the move that builds trust
4. **What I'd do next**, ordered.
5. **What I'd want before production** — reliability, security, observability.

> "Here's what's built, here's what I'd do next, and here's what I'd want in place before this went near production."

Beat 3 is the one people skip. Showing a system refuse, escalate, or degrade cleanly proves you designed for failure rather than hoping for success.

## Carry patterns back

After an engagement, ask what was built here that others would need. Recurring shapes are the strongest product signal a company has, and carrying them back is part of the job.

> "This is the third time I've seen [pattern]. That probably belongs in the product rather than in each deployment."

## Detailed reference

Question banks, the qualification grid, slicing worked examples, and the full phrase card: [wiki/1-frame/](../../../wiki/1-frame/) and [wiki/6-land/](../../../wiki/6-land/).

Decision sheets (many still placeholders — do not invent them): [wiki/catalog/](../../../wiki/catalog/README.md#engagement).
