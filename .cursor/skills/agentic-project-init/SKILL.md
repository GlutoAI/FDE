---
name: agentic-project-init
description: Creates a new agentic system project in this workspace in about two minutes by copying the tested, ready-to-run template at templates/agentic-project/ with templates/new_project.py, which replaces the project name, title, environment prefix, and CLI name and creates a protected .env. The copy includes a FastAPI backend (main.py, database.py, routers/), validated settings, OpenAI/Anthropic/fixture providers behind a ModelProvider ABC, one BaseAgent with a typed connection agent, versioned prompts, working bases for a SQLite database with CSV import, embeddings with a vector store and retriever, preference and conversation memory, an example tool served by a stdio MCP server with role allowlists, 182 offline tests, a Vite React frontend, Docker Compose, and scripts/check.sh as the one-command gate. Use when starting, initializing, bootstrapping, or scaffolding a new agent, copilot, or multi-agent project. For the phased plan documents afterwards, use agentic-project-planning.
---

# Agentic Project Init

Milestone 0 of an agentic project is **a skeleton that runs end to end offline**. It already exists as a tested template: [`templates/agentic-project/`](../../../templates/agentic-project/). Initializing a project means copying it, adapting four names, writing one purpose sentence, and running its gate. Do not rebuild or re-derive the foundation code.

What every project gets from the copy:
- a backend that loads validated configuration and runs one typed agent through a fixture model;
- working bases for the four things almost every agentic system needs (a database with CSV import, embeddings with retrieval, memory, and tools served over MCP), each with one neutral example: `ExampleRecord`, `get_example_record`, and a synthetic two-tenant corpus in the tests;
- a frontend that calls the backend, a protected `.env`, an empty `data/` whose layout is agreed, Docker images for both halves with one Compose file and no secrets, and `scripts/check.sh`.

Business data, business agents, business tools, and workflows are later milestones. The planning step belongs to [`agentic-project-planning`](../agentic-project-planning/SKILL.md).

References:
- **The template and its script:** [`templates/agentic-project/`](../../../templates/agentic-project/) and [`templates/new_project.py`](../../../templates/new_project.py). The template's README has the "Adapting the examples" table and next steps that every project inherits.
- **Design of what is in it:** [foundation.md](foundation.md) (layout, contracts, providers, configuration, why each choice) and [foundations.md](foundations.md) (database, RAG, memory, tools, MCP). Read them to explain or change the code, not to create a project.
- **Worked examples:** [`expense-review-copilot/`](../../../expense-review-copilot/) (the same skeleton on an expense domain) and [`cashflow-copilot/`](../../../cashflow-copilot/) (where the code was first tested, with an older flat layout).

## Non-negotiables

- [ ] Project name, one-sentence purpose, and environment prefix are known before the script runs
- [ ] The project is created with `templates/new_project.py`, never by hand-copying another project; no data is generated or copied into `data/`
- [ ] The README's first lines say what the project is for and what exists versus what is only planned
- [ ] `.env` is gitignored, mode `0600`, with empty keys. Preserve existing values; update only a key the user explicitly supplies. No key is printed
- [ ] The frontend never receives a secret; no image contains `.env`, tests, or data; no container receives a key
- [ ] `./scripts/check.sh` passes (and `--docker` when a Docker daemon is available; otherwise report the Docker gate as not run). A fixture pass is never called a verified API connection
- [ ] A live probe runs only when the user supplies a key for that purpose or asks for one: once per requested vendor, bounded, no retries. Otherwise live verification is reported as not run

## Step 0: Intake

Use the conversation; ask only for what is still missing. If the purpose itself is unclear, use [`fde-engagement`](../fde-engagement/SKILL.md) first.

| Must know | Example | Default |
|---|---|---|
| Project name, kebab-case `<domain>-<role>` | `expense-review-copilot` | none |
| One sentence: who it helps, with what decision, where a person stays in control | "Helps a small-business owner review expenses, with every correction approved by a person." | none |
| Environment prefix, UPPER_SNAKE without `_` | `EXPENSE` | first word of the name |
| CLI command name | `expense` | the prefix in lowercase |
| Expected raw input kinds, described not supplied | "Card exports (CSV), receipts (PDF), the expense policy (Markdown)" | leave the template's generic text |

Both vendors (OpenAI and Anthropic) and OpenAI embeddings are configured by default; the fixture provider and embedder always exist. Restate the purpose in one sentence, then proceed; existing authorization is sufficient.

## Step 1: Create

From the workspace root; the name must not already exist there:

```bash
python3 templates/new_project.py <name> --prefix <PREFIX> --cli <cli> \
  --purpose "<one sentence>"
```

It copies the template without environments, builds, or caches; replaces `agentic-project-template`, `Agentic Project Template`, `TEMPLATE_`, and `template-cli`; creates `.env` from `.env.example` with mode `600`; and leaves a one-time marker so the first check formats lines whose length changed. Standard library only, under a second, no network.

The workspace is one Git repository. Do not create a nested `.git/` or `.github/workflows/`.

## Step 2: Adapt (minutes, not hours)

Only these edits belong to initialization:
- **`README.md`:** after the status bullets, one sentence on which planned capabilities the examples will grow into (for example "the example record becomes the expense record").
- **`data/README.md`:** replace the generic raw input kinds with the intake's, if given.
- **A vendor not wanted:** remove its profile and its `[vendor_profiles]` line in `backend/config/models.toml`, and its key line in `.env.example`.

Leave `ExampleRecord`, `get_example_record`, and the document types in place. Replacing them is the first build phase, done when the first real CSV and tool are defined, following the README's "Adapting the examples" table.

## Step 3: Verify

Name the checks, then run them:

```bash
cd <name>
./scripts/check.sh --docker            # or without --docker when no daemon is running
git check-ignore .env                  # prints .env
git check-ignore .env.example          # exits 1: the template stays tracked
stat -f '%Lp' .env                     # 600 (macOS; on Linux: stat -c '%a')
git check-ignore data/raw/example.csv  # prints the path: raw contents are ignored
git check-ignore backend/data/app.db   # prints the path: runtime state is ignored
```

`check.sh` installs from the lock (bootstrapping `uv` into the ignored `.tools/` when needed), runs pytest, ruff, the format check, mypy, and the fixture `smoke`, fails on any moderate or worse `npm audit` finding, builds the frontend, and with `--docker` starts Compose, checks the response bodies on ports 8000 and 3000, runs `smoke` inside the API container, and stops the stack. It takes about 75 seconds with `--docker` on a warm machine. Uses ports 8000 and 3000; stop other stacks first.

Then write the observed results into the README's Verification section.

## Step 4: Report and hand off

Report which checks were **verified** (run, with output observed) and which are **assumed**:
- the path and the commands to run it;
- the `check.sh` result, the Docker gate (or not run), and live status per vendor (`passed`, `failed` with a safe reason, or `not run`);
- the deliberate shortcuts: no migrations, no pgvector, MCP tenant fixed at launch, examples not yet replaced;
- the next step: the plan with [`agentic-project-planning`](../agentic-project-planning/SKILL.md), including how raw data arrives.

## Maintaining the template

Change the template, never a generated project, when a base improves. After any template change:
1. In `templates/agentic-project/`, run `./scripts/check.sh`.
2. Generate a throwaway project into an ignored or temporary directory, run its `./scripts/check.sh --docker`, then delete it and its Docker volume.
3. Update the reference-status tables in [foundation.md](foundation.md) and [foundations.md](foundations.md) with what was observed.

Keep domain code out of the template: its examples stay neutral, and its placeholders must stay exact strings that appear nowhere else.

## Anti-patterns

- **Re-deriving the skeleton.** Copying another project and renaming its domain by hand takes twenty minutes and breaks tests; the script takes a second.
- **Replacing the examples during initialization.** It turns a two-minute step into a build phase without a plan.
- **Scaffolding the proposed tree.** Empty `workflows/` or `agents/<business>/` directories, or Dockerfiles for services that do not exist yet, are noise. Directories appear when their phase begins.
- **Passing `.env` into containers.** No `env_file: .env` and no key in `ENV` or `ARG`. When a service later needs a key, map that one variable in its `environment`.
- **A live call on startup or in default tests.** Only commands given `--live` (`smoke`, `index-documents`, `search`) make hosted requests.
