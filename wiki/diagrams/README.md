# Diagrams

Mermaid sources for architecture diagrams. **These files are the version we trust.** A Figma/FigJam board is a rendering generated from one of them — see [../agentic-system-design.md](../2-design/agentic-system-design.md).

## Naming

`<system>-l<level>.mmd` — for example `triage-agent-l2.mmd`.

Levels: `l1` context, `l2` topology, `l3` sequence of one run.

## Rules

Commit the `.mmd` in the same change as the design. If a board is edited by hand, port the change back here in that session or discard it — a board that has diverged from its source is worse than no diagram, because it is still trusted.

What a diagram must say is in [`.cursor/skills/agentic-system-design/SKILL.md`](../../.cursor/skills/agentic-system-design/SKILL.md). Constraints the Figma architecture layout enforces (lanes, legal edges, DAG, dotted async/external edges) are listed in [`.cursor/skills/figma-draw-standards/SKILL.md`](../../.cursor/skills/figma-draw-standards/SKILL.md). Validate against them before generating.

## Current files

| File | System | Status |
|------|--------|--------|
| [triage-agent-l2.mmd](triage-agent-l2.mmd) | Support triage agent | **Example only** — illustrates the standard; not built |
| [triage-agent-l3.mmd](triage-agent-l3.mmd) | Support triage agent | **Example only** — illustrates the standard; not built |

Nothing in this project is agentic yet. The two files above exist as a conforming template to copy, not as a record of anything deployed. Delete this note when a real diagram lands.
