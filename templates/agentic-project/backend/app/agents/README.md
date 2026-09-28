# `agents/` — typed agents on one fixed call sequence

An agent here is a **single typed model call** with validation on both sides: a Pydantic input goes in, a Pydantic output comes out, and deterministic code checks everything around the call. It is the lowest rung of the agent ladder, used on purpose: most tasks need one well-bounded call, not an autonomous loop.

## Files

### `base.py` — `BaseAgent[InputT, OutputT]`

The ABC every agent subclasses. Its constructor receives, already built, the Pydantic AI `runtime`, the `provider`, the `prompt`, the `profile`, and the `input_type`. It does no I/O.

**`run_agent(request)`** is the fixed sequence every agent follows. Subclasses do not override it:

1. **Revalidate the input** against `input_type`. Even a typed request is revalidated, because `model_construct()` skips validation and an untyped caller may pass a plain dict. On failure: `AgentInputError`, **before** any model call.
2. **Call the model once**, inside `normalize_model_errors` and `asyncio.timeout(profile.timeout_seconds)`, with `UsageLimits(request_limit=1, tool_calls_limit=0)`. The message is the prompt's `user` text followed by the validated input as JSON. The validated input is also passed as the run's `deps`.
3. **Pydantic AI validates the output** against the output schema; a failure becomes `AgentOutputError`.
4. **`_validate_output(request, output)`**, which the subclass implements: checks that relate the output to the input and that a schema cannot express. It runs outside the error translation, so a bug in it is not misreported as a provider failure.
5. **`_build_result`** attaches provenance and returns an `AgentResult`. For hosted providers it also requires `finish_reason == "stop"` and a reported model name. A response cut off by the token cap is refused instead of half-accepted.

**Model judgement vs deterministic code:** only the content of the output (step 2) is model judgement. Steps 1 and 3 to 5, the limits, and every provenance field are deterministic.

### `connection/` — the connection diagnostic

The one shipped agent; see [`connection/README.md`](connection/README.md). Keep it as the connection probe, and add business agents beside it.

## How it connects

```text
bootstrap.py
  load_prompt ──────────────┐
  load_model_profile ───────┤
  open_model_provider ──────┼──> build_agent_runtime (llm/runtime.py) ──> <Name>Agent(runtime, provider, prompt, profile, input_type=...)
                            │
callers (cli.py, routers/) ─┴──> agent.run_agent(Input(...)) ──> AgentResult[Output]
```

## How to use

```python
import asyncio

from app.agents.connection.models import ConnectionInput
from app.bootstrap import create_connection_agent
from app.core.settings import DEFAULT_PROJECT_ROOT, ProjectLocation, load_settings


async def probe() -> None:
    location = ProjectLocation(root=DEFAULT_PROJECT_ROOT)
    settings = load_settings(location, execution_mode="fixture")  # offline
    async with create_connection_agent(location, settings) as agent:
        result = await agent.run_agent(ConnectionInput())
    print(result.output.marker, result.provider, result.prompt_version)


asyncio.run(probe())
```

## Tutorial: adding a business agent

The example is a `summary` agent; replace the name and fields with your own.

**1. Contracts:** `agents/summary/models.py`. Subclass `Contract` so unknown fields and type coercion are rejected, and describe every field, because the descriptions become the JSON schema the model sees.

```python
from pydantic import Field

from app.llm.contracts import Contract


class SummaryInput(Contract):
    """What the caller sends; validated before any model call."""

    text: str = Field(min_length=1, max_length=4000, description="Text to summarize")
    max_sentences: int = Field(default=3, ge=1, le=5, description="Upper bound on sentences")


class SummaryOutput(Contract):
    """The schema the model must satisfy."""

    summary: str = Field(min_length=1, description="The summary")
    sentence_count: int = Field(ge=1, description="Sentences in the summary")
```

**2. Prompt:** `prompts/summary/v1.yaml` with `agent: summary`, `version: 1`, `system`, `user`, and `model_profile: null` and `model: null` (see [`prompts/README.md`](../prompts/README.md)).

**3. Agent:** `agents/summary/agent.py`. Implement only `_validate_output`, for the rules that relate output to input.

```python
from typing import override

from app.agents.base import BaseAgent
from app.agents.summary.models import SummaryInput, SummaryOutput
from app.core.errors import AgentOutputError


class SummaryAgent(BaseAgent[SummaryInput, SummaryOutput]):
    """Summarizes caller-supplied text in a bounded number of sentences."""

    @override
    def _validate_output(self, request: SummaryInput, output: SummaryOutput) -> None:
        if output.sentence_count > request.max_sentences:
            raise AgentOutputError("unexpected_output: summary exceeds max_sentences")
```

**4. Composition:** in `bootstrap.py`, add `build_summary_agent(provider, prompt, profile)` and `create_summary_agent(location, settings)` next to the connection versions. They mirror those functions line for line: `load_prompt(PromptReference(agent="summary", version=1))`, then `load_model_profile(location, settings, prompt)`, then `open_model_provider`, then `build_agent_runtime(..., input_type=SummaryInput, output_type=SummaryOutput)`.

> **Known shortcut:** `open_model_provider` builds its fixture with `build_fixture_model`, which always scripts a `ConnectionOutput`. A new agent run in fixture mode through that path fails output validation. Until fixtures are made per-agent, build the fixture for the new agent yourself: `FixtureModelProvider(TestModel(profile={"supports_json_schema_output": True}))` generates schema-valid output from `SummaryOutput`, or pass `custom_output_text` for a specific answer.

**5. Model selection (optional):** add `summary = "<profile>"` under `[roles]` in `config/models.toml` to give the agent its own profile. Without it, the agent uses `default_profile`.

**6. Tests:** follow `tests/test_agents.py`. Build the agent over `FixtureModelProvider(TestModel(...))`, then assert on the typed output, the provenance, the rejection of invalid outputs (parametrize over bad `custom_output_text` values), and that invalid input fails before the model is called (`model.last_model_request_parameters is None`).

## Tests

`tests/test_agents.py` (the base sequence and the connection agent) and `tests/test_bootstrap.py` (composition).
