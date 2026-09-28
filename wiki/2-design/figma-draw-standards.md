# Figma Draw Standards

Detailed reference for [`.cursor/skills/figma-draw-standards/SKILL.md`](../../.cursor/skills/figma-draw-standards/SKILL.md). The skill holds the notation; this page holds the derivation, the measured numbers behind the palette, and the order to build the Figma library in.

## Drawing is not designing

These are two different disciplines that both live in Figma, and conflating them is why most architecture boards look busy and read badly.

| | Design system | Draw standard |
|---|---|---|
| **Goal** | Reuse, and handoff to code | Correct decoding, at a glance |
| **Palette carries** | Brand | Meaning |
| **Success looks like** | A developer builds the screen correctly | A reader explains the system back to you |
| **Consistency serves** | Product coherence | Comparability between diagrams |
| **Wrong-ness looks like** | Off-brand, inconsistent spacing | Ambiguous — two readers disagree about what it says |

The practical consequence: **never put the product's brand colors on a diagram.** Brand palettes are chosen to look like the company, which means they are often analogous hues with deliberately low contrast between them. That is the opposite of what a notation needs. And never put this palette in the product UI — it is chosen for discrimination, not beauty.

The second consequence is that a diagram is judged by being *read*, not by being looked at. The test in the checklist — screenshot it in grayscale and confirm it still reads — is the whole philosophy in one action.

## Why four channels, and why color is the weakest

The notation carries meaning in position, shape, color, and border. They are orthogonal on purpose: each answers one question, so no mark is ambiguous.

Color ranks last deliberately, and that was not an aesthetic judgment. It came out of the derivation below.

The Figma architecture layout already places nodes in spatial lanes. **Position therefore identifies the lane unambiguously, with no perceptual work at all.** Once that is true, color has nothing left to carry — so it becomes reinforcement, which is exactly what makes the diagram survive grayscale printing, a low-quality screenshot pasted into a ticket, and a reader with a color vision deficiency.

This is the difference between "we chose accessible colors" and "the diagram does not depend on color". Only the second is actually robust.

## Deriving the palette

The starting point was the Wong palette mapped onto the six lanes. Measuring it killed that first attempt.

### What measurement caught

Simulating protanopia, deuteranopia, and tritanopia (Viénot 1999 matrices on linear RGB) and computing pairwise CIE76 ΔE in Lab space gave:

| Vision | Worst pair | ΔE |
|--------|-----------|-----|
| Normal | client vs service | 26.4 |
| Protanopia | client vs async | 20.7 |
| **Deuteranopia** | **gateway vs external** | **1.3** |
| Tritanopia | client vs datastore | 16.2 |

Vermillion `#D55E00` and orange `#E69F00` are **effectively the same color** under deuteranopia, which affects roughly 8% of men. Worse, those were the two lanes — gateway and external — that both use dotted edges, so the two most confusable colors sat on the two most confusable edge styles.

A palette can be built entirely from a published color-blind-safe set and still fail. Wong's eight hues are pairwise distinguishable; a six-hue *subset* of them need not be, and nobody checks.

Two further failures showed up in the same pass. `#E69F00` and `#56B4E9` give only 2.25:1 and 2.31:1 against white, below the 3:1 minimum for non-text — so they cannot be used as strokes at all. And the light fills collapsed to ΔE 7.3 under deuteranopia, confirming that **fill tint cannot carry identity** at any hue assignment.

### The search

Rather than hand-patch, the six hues were selected by search. Twenty-one candidates from the Wong, IBM, and Tol color-blind-safe palettes were filtered to those admitting a stroke variant meeting both 3:1 against white and 3:1 against their own fill, then all 54,264 six-subsets were scored by *worst-case* minimum pairwise ΔE across all four vision types.

The unconstrained optimum scored 15.3 but was three muddy reds and browns — technically separable, semantically useless, since "brown means datastore" is not a thing anyone remembers. Constraining the set to contain a recognizable blue and green cost 0.6 ΔE and produced something teachable.

### Result

| Lane | Hue | Fill | Stroke | Solid | Ink/fill | Stroke/white | Stroke/fill |
|------|-----|------|--------|-------|----------|--------------|-------------|
| `client` | Indigo | `#E4DFFC` | `#785EF0` | `#785EF0` | 13.5 | 4.51 | 3.49 |
| `gateway` | Red | `#FCE0E4` | `#D65C6B` | `#BE525F` | 14.0 | 3.75 | 3.02 |
| `service` | Blue | `#E0EBF5` | `#5C8AB8` | `#5179A1` | 14.4 | 3.63 | 3.00 |
| `datastore` | Green | `#D3E7D6` | `#228833` | `#228833` | 13.4 | 4.53 | 3.49 |
| `external` | Gold | `#FFEFCC` | `#B87F00` | `#9E6D00` | 15.3 | 3.46 | 3.04 |
| `async` | Purple | `#EED6E4` | `#AA3377` | `#AA3377` | 12.7 | 6.09 | 4.46 |

Worst-case separation, all four vision types: **ΔE 14.7**, up from 1.3. The closest pairs are now gold vs green under protanopia (15.0), red vs green under deuteranopia (15.7), and green vs blue under tritanopia (14.7) — all comfortably distinguishable.

Every cell clears WCAG: label text ≥ 4.5:1 on fills, strokes ≥ 3:1 against both the canvas and their own fill, white text ≥ 4.5:1 on solids.

The values live in [`diagrams/draw-tokens.json`](../diagrams/draw-tokens.json). Import them as Figma variables rather than typing hex.

### The honest limit

Six-way color discrimination under all three types of color blindness tops out near ΔE 15. That is the ceiling, not a shortcoming of this particular search. It is the strongest possible argument for the rule that color must be redundant — pushed to seven or eight lanes, no assignment works, and any diagram that *depends* on color is already broken for some readers.

Assignment to lanes was then chosen for intuition: blue for services because that is the dominant convention in cloud diagrams; green for storage; gold for external, reading as caution; red for the gateway, reading as a checkpoint; purple for messaging. Indigo went to `client` partly because clients are few, and a vivid hue across many service nodes would shout.

## Why these shapes

One shape per *category*, with the subtype in the label. Thirty shapes would be more precise and completely unlearnable; the catalog is sized to what a reader can hold without consulting the legend.

Three choices are worth the reasoning:

**The model provider is a circle.** It is the one external node present in essentially every agentic diagram, so it gets the shape nothing else uses and is located instantly.

**MCP servers keep one notched "socket" shape in both the `service` and `external` lanes.** The notch means *protocol boundary exposing tools*, which is true whoever runs it. Colour then says who does. The alternative — different shapes for self-hosted and vendor servers — would hide the fact that they are the same kind of thing, and the operationally important difference (who you page when it breaks) is exactly what the lane already encodes.

**All durable state is a cylinder**, with the kind in the stereotype. A vector index and a Postgres table are both "state that survives a restart", which is the property the shape should communicate. Their differences — retention, growth curve, what a rebuild costs — are operational detail that belongs in text.

Working memory and cache are drawn dashed because they are ephemeral. A restart loses them, and that is worth seeing on the picture rather than discovering in an incident.

## Why the border rules earn their place

**Double border = a model decides something inside this box.** This is the single most valuable mark in the notation, because it partitions the system into the part that can be unit-tested and the part that can only be evaluated. Those halves need different tests, different monitoring, and different rollback plans. A diagram where agents and plain services look alike hides the only distinction that changes how you operate the thing.

**4px border = mutating.** Scanning for thick borders answers "what can this system actually break?" in about two seconds. For an agentic system — where the whole anxiety is an autonomous loop taking an irreversible action — that is the first question every reviewer has, and it deserves to be answerable without reading a single label.

Together those two marks mean a reader can find the dangerous combination (a model-driven box with a thick outgoing edge) at a glance. That combination is where a human gate usually belongs, and when the diagram makes it visible, the missing gate becomes obvious during review instead of during an incident.

## Edges stay neutral

Connectors are `#595959`, never a lane color. Lane-colored connectors are the most common way a diagram turns to confetti: every edge crosses lanes by definition, so a colored edge is ambiguous about which end it belongs to, and a dozen of them read as noise. Neutral edges also let the 4px mutating weight stand out, which is the one edge property worth seeing from across the room.

Every edge gets a label in `verb object, qualifier` form. The qualifier slot is what forces the useful disclosure: writing `Reads index, read-only` or `Delegates lookup, max 6 steps` obliges the author to know the side effect and the bound. An unlabeled arrow means nobody decided yet.

## Two tiers, and why generation comes first

**Tier A** is generated from Mermaid. **Tier B** is the hand-built Figma library.

Build Tier B by styling a Tier A generation once and publishing the result — never by drawing from scratch. Drawing from scratch produces a board with no `.mmd` source, which is the exact drift problem the [agentic-system-design](agentic-system-design.md) standard exists to prevent.

One constraint to respect: in an **architecture-layout** diagram the generator owns the layout and the shapes, so the shape vocabulary does not survive. Use plain `id["Name (stereotype)"]` there and let lane position and the stereotype carry the kind. The full shape catalog applies to plain flowcharts and to Tier B. Parentheses inside a quoted Mermaid label are safe — Figma's own reference uses `A["Process (main)"]` — which is why the stereotype is written `Name (agent)` rather than with guillemets or angle brackets that risk the parser.

## The six lanes, and why agentic systems fit them

The Figma architecture layout requires every node to sit in one of exactly six subgraphs: `client`, `gateway`, `service`, `datastore`, `external`, `async`. This is a constraint of the tool, and the first reaction is usually that agentic systems do not fit it.

They fit it well, because the lanes encode two of the three classification questions from [agentic-system-design.md](agentic-system-design.md#classifying-every-component) — who runs it, and whether it is durable:

- An **agent is a `service`** because it is code we deploy.
- A **guardrail is a `service`**, not part of the gateway. The tool forbids `gateway→gateway` edges anyway, which enforces the point.
- **Memory is a `datastore`** because it is durable state, whatever the framework bundles it into.
- The **model provider is `external`** because it is a third party.

The third question, whether a model decides, is carried by the double border rather than a lane.

### The edge rules are a linter

Only six edge kinds are legal; everything else must be mediated by a `service`. In practice this behaves like a lint rule for architecture. If a diagram wants a `gateway→datastore` edge, the design has a gateway doing business logic. If it wants `client→external`, a secret is about to live in a browser.

Two constraints catch real mistakes repeatedly:

**Every `service` node needs an in-edge and an out-edge.** A node with no out-edge is usually an agent whose result nobody consumes. A node with no in-edge is usually one that was planned and never wired.

**Forward edges must form a DAG.** A cycle in forward edges means a loop nobody bounded. Being forced to redraw it as an explicit backward edge (`<---`) makes the feedback loop visible — and prompts the question of how many times it runs, which becomes the edge label.

`_` in node IDs breaks routing, so use camelCase. This one is not a design principle, just a trap.

### Why the evaluator loop is a backward edge

In the triage example, `drafter → critic` is forward, and `critic → orch` returns upstream. Written as a forward edge it would create a cycle and the layout would reject it. Written as `orch <---|"Verdict, max 2 rounds"| critic`, the feedback loop is explicit and carries its bound. The constraint produced a better label than we would have written unprompted.

## Unsupported diagram types

**C4's notation is not available through Figma's diagram generator.** C4 is on the explicitly unsupported list, alongside class diagrams, mindmaps, timelines, journeys, quadrants, and pie charts. The design's levels are rendered with supported types: architecture flowchart for L1 and L2, sequence for L3. Flowchart, state, ERD, and Gantt are also supported. In sequence diagrams, `Note over` and its variants are stripped on generation.

## Building the Figma library

In this order. Each step depends on the one before.

1. **Import the variables** from [`diagrams/draw-tokens.json`](../diagrams/draw-tokens.json) into a collection named `diagram`. Do this first — every component built before the variables exist will have hard-coded fills that nobody goes back to fix.
2. **Build one base node component**: auto layout, hug contents, 16px horizontal and 12px vertical padding, 8px radius, 160px min width, three text layers (stereotype 11px uppercase, name 14px medium, qualifier 11px regular).
3. **Add variants** for `lane` (six values) and `border` (`solid`, `double`, `dashed`, `mutating`). Bind fill and stroke to the lane variables so a lane change restyles the node.
4. **Build the shape set** as separate components sharing the base's text and padding: rectangle, rounded rect, hexagon, cylinder, parallelogram, stadium, circle, diamond, notched rect.
5. **Build edge styles**: solid, dashed, and a 4px mutating weight, all `#595959`, each with a label slot.
6. **Build annotations**: budget chip, caveat sticky, trust-boundary container, data-classification tag.
7. **Build the legend frame** as a component, so it cannot be forgotten or drawn inconsistently.
8. **Publish** as a library named `Diagram Kit`.

Name components broad to narrow — `Node / Service / Agent` — because Figma nests slash segments into a tree, and that tree is what makes a growing library navigable for both people and agents reading the file back.

## Worked example: the same node, three ways

A triage orchestrator that writes to a ticketing system.

**Wrong.** A grey rectangle labelled `Orchestrator`. It has no lane, so ownership is unstated; no shape distinction, so a reader cannot tell a model decides inside it; no border weight, so the fact that it mutates external state is invisible; and no bound, so nothing says the loop terminates. Four properties a reviewer needs, none of them present.

**Right, Tier A.** In the `service` lane: `orch["Triage Orchestrator (orchestrator)"]`, blue fill `#E0EBF5`, stroke `#5C8AB8`. Outgoing edge `orch -.->|"Creates ticket, mutating"| tickets` at 4px.

**Right, Tier B.** The same node from the library: `Node / Service / Agent`, lane `service`, border `double` — a model plans the steps — with the stereotype line `ORCHESTRATOR`, the name `Triage Orchestrator`, and the qualifier `max 6 steps`. The outgoing edge is the 4px mutating style, labeled `Creates ticket, mutating`, running to the notched MCP node in the `external` lane.

A reader takes four facts off that last version without reading prose: we run it, a model drives it, it can create something in a system we do not own, and it gives up after six steps.

## Verified and assumed

**Verified by measurement.** Every contrast ratio and ΔE figure on this page was computed, not estimated — WCAG relative luminance for contrast, Viénot 1999 linear-RGB matrices for color-blindness simulation, CIE76 in Lab for separation. The search covered all 54,264 six-subsets of the 21 filtered candidates. Re-derive by re-running the method described above.

**Verified from Figma's documentation.** The six subgraph IDs, the legal edge table, the DAG and dotted-edge constraints, the camelCase/underscore trap, the unsupported diagram types including C4, the stripping of `Note over` in sequence diagrams, the instruction not to call `create_new_file` before `generate_diagram`, the safety of parentheses inside quoted Mermaid labels, and the slash-nesting behavior of component names. Read directly from Figma's `mcp-server-guide` skill references; see [Sources](#sources).

**Generator setup — not verified on this machine at the time of writing.** No Figma MCP server was configured in this project or in the user-level Cursor or Claude config; a search for `mcp.json` found nothing. To use it, the Figma MCP server must be connected in the client (Cursor, VS Code, or Claude Code; only clients in Figma's MCP catalog can connect), and the canvas-writing tools live on the **remote** server — the local server does not expose `generate_diagram`, `create_new_file`, or `upload_assets`.

**Assumed, confirm on first use: the architecture layout flag.** Figma's reference gives `useArchitectureLayoutCode: "FIGMA_DIAGRAM_2026"`, but the value looks version-stamped and the loaded `figma-generate-diagram` skill is authoritative at call time. Use whatever value it specifies rather than hard-coding this one.

**Assumed, confirm on first use.** That `generate_diagram` preserves the richer Mermaid node shapes in *plain* flowcharts. Figma's reference documents styling being stripped for Gantt charts and notes being stripped for sequence diagrams, but says nothing explicit about flowchart node shapes. The Tier A rule — plain `[Label]` in architecture layouts — does not depend on this. Check it the first time a plain flowchart is generated, and record the result here.

**Not yet exercised.** No board has been generated from this repository, so the library build order above is a plan, not a record. Update this section once a diagram has been generated and once `Diagram Kit` exists.

## Sources

Figma MCP and diagram generation: [Tools and prompts](https://developers.figma.com/docs/figma-mcp-server/tools-and-prompts/) · [Figma MCP server introduction](https://developers.figma.com/docs/figma-mcp-server/) · [mcp-server-guide](https://github.com/figma/mcp-server-guide) · [architecture diagram rules](https://github.com/gorkking/figma-mcp-server-guide/blob/main/skills/figma-generate-diagram/references/architecture.md) · [Guide to the Figma MCP server](https://help.figma.com/hc/en-us/articles/32132100833559-Guide-to-the-Figma-MCP-server)

Figma conventions: [Component architecture](https://www.figma.com/best-practices/component-architecture/) · [Best practices to help Figma AI understand your design system](https://help.figma.com/hc/en-us/articles/38978644498199-Best-practices-to-help-Figma-AI-understand-your-design-system) · [Component naming practices](https://www.rootstrap.com/blog/mastering-figma-components-best-naming-practices-for-seamless-design-to-development-workflow/)
