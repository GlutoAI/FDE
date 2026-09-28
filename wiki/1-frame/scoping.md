# Scoping

> Decision sheets (placeholders until filled): [catalog/scoping.md](../catalog/scoping.md), [problem-statement](../catalog/problem-statement.md), [success-metrics](../catalog/success-metrics.md). This page is the long form.

Detailed reference for the slicing section of [`fde-engagement`](../../.cursor/skills/fde-engagement/SKILL.md). Turning an agreed problem into increments that can be shown.

## A slice is only a slice if you can demo it

The definition is operational, not aesthetic. A slice is **one trigger, one decision, one action, visible end to end** — narrow enough to finish, complete enough to show someone.

Layers are not slices. "All the data models, then all the endpoints, then the agent, then the UI" is four layers, and it demos nothing until the last one lands. Every layered plan has the same shape: weeks of *"it's going well"* followed by one integration week where all the risk was hiding.

The test: **at the end of this increment, can I show a person a thing that happened?** If the honest answer is "I can show you the schema," it is a layer.

## Why thin slices beat complete layers

**Risk surfaces early.** Integration is where designs are wrong. A vertical slice does the integration on day one, when being wrong is cheap.

**Feedback arrives while it is still feedback.** Shown a working narrow path, people say *"oh — but it needs to handle X"*. Shown a schema, they say *"looks good"*, because a schema is unfalsifiable to anyone who is not going to use it.

**Progress becomes legible.** A client cannot evaluate 60%-done. They can evaluate one path working and four not yet started, and that legibility is what buys the trust to keep going.

**Something is always deliverable.** If the engagement is cut short, a thin slice is a working feature. Layers at the same point are nothing.

## Order slices by risk

Not by ease, and not by architectural tidiness. **Build the part most likely to be wrong first**, while there is still time to be wrong about it.

Risk usually concentrates in: the integration you have not tested credentials for, the step where the model must be accurate enough, the data quality assumption nobody has verified, and the handoff to a human. Ease concentrates in CRUD. It is tempting to start with CRUD because it produces visible progress fast — and it defers every real question.

A useful opening move is a **spike**: the narrowest possible path through the riskiest part, timeboxed, not intended to ship. *"Before I commit to the design, let me spend fifteen minutes checking that I can actually read from that system."*

## Sizing

A slice should finish inside one sitting — an hour or two of build. If it will not, it is not one slice, and the decomposition is the work.

The two failure modes are symmetric. Slices that are too big stop generating feedback and become layers with better marketing. Slices that are too small generate ceremony — five demos of things nobody can evaluate separately. The heuristic that holds: a slice is right-sized when you can say what it does in **one sentence with no "and" in it.**

## The demo milestone

Every slice has a named observable outcome, agreed before building.

> "At the end of this, when a record is created, you'll see it appear in the queue with a decision and a reason attached."

Naming it does three things: it forces you to build toward something visible, gives the client something concrete to push back on before you spend the time, and makes done unambiguous — no negotiation about whether it counts.

## Risk register

Kept short and live. Four columns: **what might go wrong · how likely · what we'd do · who owns it.**

Its real function is social. Writing a risk down converts *"I'm worried about the data quality"* from a vague anxiety into a tracked item with an owner — which stops it being raised repeatedly, and means that if it fires, it was predicted rather than missed.

Three risks are worth a line on almost every agentic engagement: **access** (credentials arrive later than promised), **data quality** (the real data is messier than the sample), and **accuracy floor** (the model is not good enough at the fuzzy step, and there is no fallback).

## Scoping inside a time-boxed exercise

Compress ruthlessly. Slice one is the **thinnest path that proves the wiring**: trigger fires, something happens, you can see it. Correctness comes in slice two.

Say the plan aloud first, including what you are deliberately leaving out:

> "I'll do the narrow path first — trigger to visible result — with the logic stubbed. Once that runs we replace the stub with the real decision. That way we always have something working."

Deliberately deferred is not the same as forgotten, and the difference is entirely whether you said it. An unmentioned stub looks like an oversight; a mentioned one looks like sequencing.

## Output

Scoping is done when there is:

1. A **slice list**, ordered by risk, each describable in one sentence without "and".
2. A **demo milestone** for the first slice, agreed.
3. A **risk register** with at most a handful of live entries and an owner each.
4. An explicit **not now** list — what is deliberately out of this increment.
