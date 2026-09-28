# Demo and Handoff

Detailed reference for the closing sections of [`fde-engagement`](../../.cursor/skills/fde-engagement/SKILL.md). Presenting finished work, handing it over, and carrying patterns back.

## The five-beat walkthrough

Three minutes, in this order. The order matters more than the content.

1. **The problem**, one sentence, in their words.
2. **It working**, on a real case.
3. **It failing safely**, on a bad case.
4. **What I'd do next**, ordered.
5. **What I'd want before production** — reliability, security, observability.

Beat 1 first, always. Opening with what you built asks the audience to reconstruct why it matters while simultaneously evaluating it. Opening with the problem — in their vocabulary — means everything after lands against a frame they already hold.

Beat 4 before beat 5 keeps them separate. "What's next" is product; "what's needed for production" is engineering rigour. Merging them makes the second sound like more features rather than the cost of being trusted.

## Beat 3 is the one people skip

Showing the system succeed proves it can work. **Showing it fail safely proves you designed for reality.** Anyone can demo a happy path; a happy path is what a prototype has.

So demo the bad case on purpose: malformed input, a missing field, a case that should escalate, the dependency being down. Show the system refuse, route to a human, or degrade cleanly — and narrate the design decision behind it.

> "This one's deliberately broken. The model returns something that doesn't validate, so rather than guessing, it routes to the human queue and logs why. I'd rather it be visibly unsure than quietly wrong."

This single move separates people who have run systems in production from people who have built demos. It is also the most efficient way to answer the reliability question before it is asked.

The corollary: **never demo something you have not run at least once beforehand.** A live failure you did not plan is not beat 3, it is beat 3 happening to you.

## Handoff

The question handoff answers is not *"can they use it?"* but **"can they change it?"** Software nobody can modify is not delivered, it is abandoned in place.

Four things, roughly in value order:

**The decision log.** Why it is built this way — especially the roads not taken. The most expensive thing a successor does is undo a deliberate choice they mistook for an accident. Each entry is three lines: what was decided, what was rejected, what would change the answer.

**A runbook.** The named failure modes and their fixes. What "healthy" looks like, how to tell, what to do when it is not, and who to call. Written before anything breaks, because that is the only time there is any leisure to write it.

**How to change the thing they'll want to change.** There is always one — a threshold, a rule, a prompt, a routing table. Make that path obvious and document it specifically. If changing it requires you, you have not handed over.

**A short tour, recorded.** Fifteen minutes walking the code: where a request enters, where the model is called, where the decision is made, where it is logged. Recorded, because the person who needs it most joins in three months.

What handoff is *not* is exhaustive documentation of everything. Comprehensive docs go stale and get distrusted wholesale. Document the **why** and the **change paths**; let the code carry the what.

## Carrying patterns back

The last responsibility, and the one that separates a contractor from a forward deployed engineer.

After an engagement, ask: **what did we build here that three other customers would need?** Recurring shapes are the strongest product signal a company has, because they are observed rather than speculated — someone paid for it, in their real environment, with their real constraints.

The signal to watch for is **the same workaround appearing twice.** One customer needing something unusual is a customer. Two independently building the same scaffolding around a gap is a product requirement with evidence attached.

Make the report specific and cheap to act on: what the pattern is, how many customers, what each built instead, and what it cost them. Vague field feedback — *"customers want better reporting"* — is noise. *"Three deployments have now hand-rolled an approval queue with the same four states, costing about a week each"* is a roadmap item.

> "This is the third time I've seen this shape. It probably belongs in the product rather than in each deployment."

The flow runs both ways, and that is the point of being deployed forward. Patterns go back to product; product improvements come to every customer. An FDE who only ships customer code is a contractor with better tooling.

## Closing when the work is unfinished

Time runs out; that is normal. What matters is whether the boundary is drawn deliberately.

State clearly: what is **done and tested**, what is **done but not tested**, what is **stubbed**, and what was **not started**. Then the order you would do the rest in, and why that order.

> "The trigger path and the decision are done and tested. The notification is stubbed — it logs instead of sending. Scheduling isn't started. I'd do the notification next because it's the visible half, then scheduling, then the observability I mentioned."

An honest inventory reads as control. Vagueness about state reads as not knowing — which is the more damaging impression, and the one that is actually avoidable.
