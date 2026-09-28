# Discovery

> Decision sheets (placeholders until filled): [customer-interviews](../catalog/customer-interviews.md), [current-state](../catalog/current-state.md), [stakeholder-map](../catalog/stakeholder-map.md), [constraints](../catalog/constraints.md). This page is the long form.

Detailed reference for the discovery section of [`fde-engagement`](../../.cursor/skills/fde-engagement/SKILL.md). The skill holds the question bank; this page holds why those questions and not others.

## What discovery is for

Discovery is not requirements gathering. Requirements gathering assumes the client knows what they want and your job is transcription. Discovery assumes **the client knows their problem and you know what is buildable**, and the useful answer lives in the overlap that neither of you can see alone.

The failure mode on both sides is symmetrical. Ask too little and you build a correct solution to the wrong problem. Ask too much and you burn the goodwill you need later, and look like you are stalling. The resolution is not "ask fewer questions" — it is **ask only questions whose answers change what you build.**

That is the filter. Before asking anything, finish this sentence: *"If they answer A I'll do X, if they answer B I'll do Y."* If you cannot, the question is curiosity, and curiosity can wait until the build is running.

## Why "what's the worst thing this could do by mistake?" is first

It is the highest-value question in the set because it returns four answers at once:

- **Cost of error**, which sets the autonomy level — how much the system may do without a human.
- **Guardrail requirements**, because the named disaster is the thing to make structurally impossible.
- **Approval design**, because the answer tells you exactly which action needs a gate.
- **The real stakeholder**, because whoever owns that disaster is who must sign off.

It also changes the register of the conversation. Most discovery conversations are about features; this one is about consequences, which is where production thinking lives. Asking it early signals that you think about blast radius before you think about happy paths — and that is the distinction between someone who demos and someone who deploys.

The answers vary in a useful way. "It might send a customer a slightly odd email" and "it might approve a payment that shouldn't go out" are the same sentence structurally and completely different systems: one can run autonomously with sampling, the other needs a human in the loop on every decision above a threshold.

## The question bank

### Understanding the problem

| Question | Why |
|---|---|
| "Walk me through what happens today, start to finish." | The documented process and the real one differ. The difference is usually where the pain is. |
| "Who does that, and how long does it take them?" | Converts the problem to hours, which converts it to money. |
| "How many of these happen in a week?" | Sets scale, latency budget, and whether per-run cost matters at all. |
| "What happens when it goes wrong today?" | Reveals existing controls — often you are automating a step that already has a safety net you must preserve. |
| "What's the annoying part?" | People describe processes neutrally and then tell you exactly where the pain is when asked directly. |

The current-state trace is the most valuable single artifact. Ask them to narrate one real recent case rather than describe the general process — **generalities hide the exceptions, and the exceptions are the build.** "Tell me about the last one that was annoying" is often worth more than the whole process description.

### Establishing value

| Question | Why |
|---|---|
| "If this worked perfectly, what would you stop doing?" | The value, in their words, in a form you can demo against. |
| "What number moves, and what is it today?" | Forces a baseline. Without one there is no way to show the thing worked. |
| "Who has to believe this works for it to keep running?" | The person in the room is often not the person who renews. |

A success metric with no baseline is not a metric. "Reduce manual review" is unmeasurable; "cut the 200 items a week that need manual review to under 50" is a target, and it tells you that 75% automation is success and 95% is not required.

### Finding constraints

| Question | Why |
|---|---|
| "What systems does this touch, and do I have access?" | The most common week-one blocker is credentials, not code. Ask on day zero. |
| "Is there anything that can't be automated for legal or contractual reasons?" | Cheaper to hear now than after it is built. |
| "What's the worst thing this could do by mistake?" | See above. |
| "Who signs off before this touches real data?" | Surfaces the approval chain, which is often longer than anyone volunteers. |

### Choosing the first slice

| Question | Why |
|---|---|
| "If we could only fix one step this week, which one hurts most?" | Lets them choose the slice, which makes it theirs. |
| "Is there a piece of this low-risk enough to run for real quickly?" | Finds the path to a production signal early. |

Having the client pick the first slice is worth more than picking the optimal one yourself. A slice they chose gets attention, feedback, and defended budget; a slice you chose gets polite interest.

## Running the conversation

**Ask one question at a time.** Stacked questions get the last one answered and the rest lost.

**Let silence run.** The three seconds after someone finishes are where the qualifier arrives — *"...although, the ones from the regional team come in differently."* That qualifier is usually the hardest part of the build.

**Write down their nouns and use them.** If they say "cases", never say "tickets". Vocabulary mismatch reads as not listening, and the words they use encode distinctions their business actually makes.

**Play back what you heard** before moving on: *"So the goal is X, success looks like Y, and the thing we must never do is Z — right?"* Cheap, and it catches mismatches while they are still free.

## Discovery inside a time-boxed exercise

In a short session, discovery compresses to **two or three questions before touching the keyboard** — but it does not disappear, and skipping it entirely is visible.

Pick from the top of the bank: the worst-thing question, one scope question, one access question. Then restate and start. Ninety seconds spent here changes what you build for the next hour.

Continue asking as you go. Discovery is not a phase you exit — it is a habit. Every ambiguity found mid-build is another chance to demonstrate you would rather ask than assume.

## Output

Discovery is done when you can write, and they would agree with, four sentences:

1. **Problem** — who hurts, how often, what it costs today.
2. **Success** — the number that moves, from what to what.
3. **Never** — the thing this system must not do.
4. **First slice** — the thinnest end-to-end path, and what demoing it looks like.

If any of those four is missing, you are guessing about that one. Say so out loud rather than filling it in silently.
