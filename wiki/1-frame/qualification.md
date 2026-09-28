# Qualification

> Decision sheet (placeholder until filled): [catalog/qualification.md](../catalog/qualification.md). This page is the long form.

Detailed reference for the qualification section of [`fde-engagement`](../../.cursor/skills/fde-engagement/SKILL.md). Deciding whether a problem deserves an agent, a workflow, or plain code — before building any of them.

## The rung you pick is the bill you pay

There are three rungs, and they differ by **who chooses the next step**.

| Rung | Who chooses the step | What it costs |
|---|---|---|
| **Rule / code** | You, at write time | Milliseconds, no per-run cost, fully testable, behaves identically every time |
| **Workflow** | You, at design time — the model fills fixed slots | One or more model calls, testable per step, mostly predictable |
| **Agent** | The model, at run time | Many calls, variable path, variable cost, requires evals rather than assertions |

Every rung up buys flexibility on unpredictable input and pays in latency, spend, and debuggability. The pattern that holds across engagements: **most problems presented as needing an agent are workflows, and a meaningful minority are rules.**

The reason is that the word "AI" is attached to the *project*, so it gets attached to every step in it. But a project can be an AI project while most of its steps are ordinary code — and usually should be.

## The model-vs-code split

This is the same decision at a finer grain, and it is the highest-leverage call in the whole design. The default that holds up:

> **The model classifies, extracts, and drafts. Code decides, routes, and writes.**

A threshold comparison is never a model's job. Neither is a lookup, a fixed routing table, arithmetic, or anything with an enumerable answer set and a known-correct output. Those are code, because code is faster, free, deterministic, and unit-testable — and because a model will get some percentage of them wrong forever, for no benefit.

What the model is uniquely good at is the fuzzy edge: turning unstructured input into structured facts, judging similarity, summarizing, and drafting language. Give it those, take the structured output, and let ordinary code make the decision.

The practical test: **if you can write the assertion, write the code.** If you find yourself able to specify exactly what the right answer is for every input, you have just described a function, and you should write that function.

This split is also what makes the system explainable. When someone asks why a case was routed a certain way, "the model classified it as X, and the rule for X is Y" is an answer. "The model decided" is not.

## Cost of error sets the autonomy

Two axes determine how much the system may do alone. Place the action on both.

| | **Reversible** | **Irreversible** |
|---|---|---|
| **Narrow blast radius** | Act autonomously. Sample for quality. | Act, but log richly and alert. Make undo a feature. |
| **Wide blast radius** | Act with monitoring and a kill switch. Roll out gradually. | **Human gate, always.** No exceptions for confidence scores. |

The bottom-right cell is the one people argue about, usually via "but the model is 97% accurate." Accuracy is the wrong frame for irreversible wide-blast actions, because the question is not how often it is right but **what happens the one time it is wrong**, and whether anyone finds out before the damage compounds.

The useful reframe: instead of raising the confidence threshold, make the action reversible. An action that can be undone moves to a friendlier cell and can then run autonomously. Designing for undo buys more autonomy than any amount of model tuning.

## When to say it shouldn't be an agent

Say it plainly and early. **Naming the cheaper solution is a credibility move** — it demonstrates that you optimize for the client's outcome rather than for the interesting build, and it is the fastest way to be trusted on the calls where you *do* recommend the expensive thing.

Signals that the answer is code, not an agent:

- The logic fits in a table, and the table is stable.
- Someone can already state the rule in one sentence without hedging.
- The inputs are already structured — there is no extraction to do.
- The client can enumerate every case and there are fewer than a few dozen.
- The expensive part is an integration, and the "AI" is decoration on top of it.

Signals that a workflow beats an agent:

- The steps are always the same; only the content varies.
- You can name the steps in advance, in order.
- Each step's output is checkable before the next begins.

Reserve the agent for the case where the steps genuinely cannot be known until runtime — where the system must look at what it found and decide what to do next.

## Worked example

A team wants "an AI agent that handles incoming requests." Decomposed:

| Step | Rung | Why |
|---|---|---|
| Read the request and pull out structured fields | **Model** | Unstructured input, genuinely fuzzy |
| Check the extracted amount against a limit | **Code** | A comparison. Deterministic, testable, free |
| Look up the owner for that category | **Code** | A table lookup |
| Decide the route | **Code** | Enumerable outcomes given the fields above |
| Draft the notification text | **Model** | Language generation |
| Send it | **Code** | An API call — with an idempotency key |

One "AI agent" becomes two model calls with fixed roles and four deterministic steps. It is cheaper, faster, mostly unit-testable, and when someone asks why a request was routed a certain way there is a real answer.

It is also honestly described as a **workflow**, not an agent — which is worth saying out loud, because the accurate word makes everything downstream easier to reason about.

## Output

Qualification is done when you can state, in one line each:

1. The **rung** and why the one below it is insufficient.
2. The **split** — which decisions the model makes and which stay in code.
3. The **autonomy level**, justified by reversibility and blast radius.
4. The **gate** — the one action that needs a human, if any.
