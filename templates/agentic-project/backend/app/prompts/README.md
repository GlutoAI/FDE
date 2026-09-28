# `prompts/` — versioned YAML prompts

One directory per agent, one immutable file per version: `prompts/<agent>/v<version>.yaml`. Prompts are data, not code. They are loaded by `llm/prompts.py`, validated as a `PromptTemplate`, and fingerprinted with SHA-256, and every agent result records the version and fingerprint it ran with.

## Why prompts are files, versioned, and immutable

- **Reviewable:** a prompt change is a diff in a pull request, not a string buried in code.
- **Reproducible:** `AgentResult.prompt_version` and `prompt_sha256` say exactly which text produced an output, so a result can be traced back to its prompt.
- **Immutable:** once a version is used, do not edit it. Add `v2.yaml` and point the agent at it. Editing `v1.yaml` in place would make old results claim a prompt they did not run with (the SHA-256 would reveal it, but the history would be lost).

## File format

Every field is validated by `PromptTemplate` in `llm/contracts.py`:

| Key | Required | Meaning |
|---|---|---|
| `agent` | yes | Must equal the directory name |
| `version` | yes | Must equal the number in the file name |
| `system` | yes | Trusted instructions (≤ 4000 characters), sent as the runtime's `instructions` |
| `user` | yes | The fixed user message (≤ 4000 characters); the agent appends the validated input as JSON after it |
| `model_profile` | no | A profile name in `config/models.toml` that overrides the role's profile; `null` inherits |
| `model` | no | A model ID that overrides the profile's model but keeps its limits and credentials; `null` inherits. `TEMPLATE_LLM_MODEL` beats it |

A mismatch between `agent`/`version` and the path raises `prompt_identity_mismatch`; any other problem raises `invalid_prompt`. Both are `ConfigurationError`s, raised when the agent is created and never in the middle of a call.

## Directories

- [`connection/`](connection/README.md): the prompt of the connection diagnostic agent.

## How to use

```python
from app.llm.contracts import PromptReference
from app.llm.prompts import load_prompt

prompt = load_prompt(PromptReference(agent="connection", version=1))
print(prompt.template.version, prompt.sha256[:12])
```

## How to add a prompt

1. Create `prompts/<agent>/v1.yaml` with the keys above; `agent: <agent>` and `version: 1`.
2. Keep `system` about behavior and output shape. Do not paste data into it: the input goes in the request, and retrieved passages are untrusted content, never instructions.
3. Load it with `PromptReference(agent="<agent>", version=1)` where the agent is built (see [`agents/README.md`](../agents/README.md)).
4. The YAML files ship inside the `app` package, so no path configuration is needed; `load_prompt` reads them with `importlib.resources`.

## Tests

`tests/test_agents.py` and `tests/test_bootstrap.py` load `connection/v1.yaml`, and check that the returned provenance matches its version and hash.
