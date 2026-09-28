# Consulting Craft

> Method, not a catalog card. How you narrate and take a hint. Decision sheets for Frame are in [catalog Engagement](../catalog/README.md#engagement).

Detailed reference for the narration, hint-taking, and stuck sections of [`fde-engagement`](../../.cursor/skills/fde-engagement/SKILL.md). The phrasings that make technical work legible to the person paying for it.

## The principle

A client cannot evaluate your code. They can evaluate **whether they knew what was coming**. Almost everything below follows from that.

The engineer's instinct is to disappear into the problem and re-emerge with a result. It feels efficient and respectful of everyone's time. What it actually produces is a client with no information for twenty minutes and then a fait accompli — no chance to redirect while redirecting was cheap. Narration is not performance; **it is giving people the option to stop you.**

## Narrate before, not after

The ordering carries the whole meaning.

> "I'm going to put the threshold logic in code rather than the prompt, because I want it deterministic and testable."

Said *before*, that is a decision offered for comment. Said *after*, it is a justification for something already done. Identical words, opposite social function — one invites a correction, the other defends against it.

State: what you are about to do, why that rather than the obvious alternative, and what would change your mind.

## The phrase card

The moments that matter most, with language ready so the cognitive load goes to the problem instead of the wording.

### Opening

> "So the goal is X, and success looks like Y — have I got that right?"

> "Before I start: [one question]. It changes whether I do [A] or [B]."

> "Here's my plan — [step one], then [step two]. I'll build the smallest version that runs end to end first, then we look at it together."

### Making a tradeoff

> "Two ways to do this. A is faster to build but [cost]. B is more robust but [cost]. Given [constraint they told you], I'd take A — sound right?"

> "I'd normally do [thorough thing] here, but given the time I'm doing [pragmatic thing] and flagging it."

### A deliberate shortcut

> "I'm stubbing this for now and flagging it so it doesn't look finished."

> "This is hardcoded on purpose — it becomes config in the next pass."

### Explaining model behaviour

> "The model does one job here: read this and return structured fields. It doesn't decide the outcome — that's this function, comparing against the rule. So the decision is deterministic and I can test it."

> "If the model returns something that doesn't validate, this path catches it and routes to a human rather than guessing."

### Before testing

> "I'll test three things: the happy path, the boundary at exactly the limit, and what happens when [dependency] is unavailable."

### When stuck

> "I'm getting [exact error]. My first guess is [X] — checking [specific thing]."

> "I haven't hit this one before. Give me thirty seconds to look it up."

> "I've spent a couple of minutes here. Do you know if [specific thing] is configured in this environment?"

### Taking a hint

> "Good catch — changing that now."

> "Say more about that?"

> "That's better, because [reason]."

### Disagreeing

> "I'd gently push back — [reason]. But it's your call, and if you'd rather [their way], I'll do that."

### Closing

> "Here's what's built, here's what I'd do next, and here's what I'd want before this went near production."

## On being stuck

Being stuck is expected and universal. **Being silently stuck is the only version that damages you**, because from outside, silent-and-stuck and silent-and-working are identical until time runs out.

The professional version is narrating the hypothesis rather than the confusion. "I'm confused" transfers anxiety. "I'm getting this error, my first guess is X, checking Y" transfers a mental model and lets the other person help — they often know instantly that it is not X.

Looking things up is normal engineering. Doing it out loud is the version that reads as competence rather than gap-hiding. Timebox it at roughly two minutes, then ask — and ask a *specific* question, because specificity is what makes it cheap to answer.

Asking where something lives or how a component works is expected and costs nothing. The cost is in guessing, building on the guess, and discovering it was wrong.

## On hints

A hint is a test of whether you listen. This matters more than being right initially, because **a collaborator who takes input is more valuable than one who needs less of it** — the second kind is only better until they are wrong.

Act on it visibly and immediately. Change the code while they watch. The worst response is agreeing and continuing unchanged, which reads as dismissal even when it was only absent-mindedness.

Three seconds of *why* the hint is better proves you understood rather than merely complied: *"That's better — it means the retry doesn't double-charge."*

If you genuinely disagree, say so once, briefly, then defer. One round of disagreement reads as having a spine; two reads as not listening. And defer genuinely — a deferral followed by doing it your way is worse than arguing.

## On explaining AI

Be able to say, unprompted, **what is model judgement and what is code.** Cover briefly: what goes into the prompt, what shape comes back, what happens when it returns something invalid, and roughly what it costs per run.

If you cannot explain why the model returned what it returned, you cannot support the system in production — and "the model decided" is not an explanation, it is the absence of one.

The version that lands:

> "One model call. Input is the record text plus a short instruction; output is a structured object I validate. If validation fails it goes to the human queue rather than guessing. Everything after that point is ordinary code, so I can unit-test the decision."

## Tone

**Use their nouns.** If they say "cases", never say "tickets". Their vocabulary encodes distinctions their business makes.

**Say "I don't know" cleanly**, then say what you would do to find out. The follow-up is the whole value of the admission.

**Flag incompleteness before they find it.** Naming the stub makes it sequencing; letting them find it makes it an oversight.

**Do not over-apologise.** One acknowledgement, then the fix. Repeated apology makes a small problem look large and moves the other person into reassuring you.
