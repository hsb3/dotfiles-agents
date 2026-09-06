---
name: comms
description: Produce your recurring communication deliverables - a morning status briefing, end-of-day wrap-up, weekly planning briefing, advisor board status readout, or client product overview - as a deck (plus optional spoken companion) to a consistent standard. Use when you ask for any of those by name, or for a "briefing", "status deck", "status readout", "board deck", "comms package", or deck narration/audio. Self-comms build through a bundled stdlib-Python engine (spec in, validated, voice-linted, themed HTML/PDF out; no MCP server). Composes with the pptx-themes skill (external decks) and the handoff skill (EOD wrap-up); it does not replace them.
---

# Comms

Your communication deliverables, produced to one standard so each is fast to make and
consistent to read. A deliverable is a dated folder `<briefings-dir>/<YYYY-MM-DD>-<slug>/`
holding the deck source, exported deck, optional audio, and a `sources.md` provenance file.
`<briefings-dir>` is `_meta/briefings/` when the repo already has a `_meta/` tree (the
mise-en-place standard), else `briefings/` at the repo root — never create `_meta/` for this.

The shared machinery lives in **`references/comm-package-standard.md`** (read it first). Each
comm type has a self-contained playbook + a real worked example in **`examples/<type>/`**.

## Which comm (decision table)

| If you want | Comm type | Toolchain | Audio | Playbook |
| --- | --- | --- | --- | --- |
| the decision for today | morning briefing | `deliver.py` (type `morning-briefing`) | yes (2-3 min) | `examples/morning-briefing/playbook.md` |
| to close today, tee up tomorrow | end-of-day wrap-up | `deliver.py` (light) | optional | `examples/end-of-day-wrapup/playbook.md` |
| the week's plan + where we stand | weekly planning briefing | `deliver.py` | yes (3-4 min) | `examples/weekly-planning/playbook.md` |
| a board status readout + the ask | advisor board readout | pptx-themes | optional | `examples/advisor-board-readout/playbook.md` |
| what a client gets + why to trust it | client product overview | pptx-themes | optional | `examples/client-product-overview/playbook.md` |

The split is by **audience and stakes**: the three self-comms are fast, decision-first, and
build through **`scripts/deliver.py`** (bundled, stdlib-only Python - no MCP server); the two
external comms are polished, hand-laid, and use the **pptx-themes** skill. Audience drives
toolchain, theme, voice, and how honest framing is phrased.

## Workflow

1. **Resolve which comm** from the table; if ambiguous, ask. Read its `playbook.md` and look
   at the `sample.*` artifact next to it - the sample is the template for voice and structure.
2. **Read `references/comm-package-standard.md`** for the per-project parameters (auto-detect
   `<owner>/<repo>`, handoff file, gates), the toolchain pipeline, voice baseline, and gotchas.
3. **Gather current state** per the playbook - accuracy is the whole job (handoff + live counts
   + git log for internal comms; charter + product thesis for external comms). A typed
   deliverable lists its runnable gather commands under `deliver.py types`.
4. **Author** the source: a spec (`deliver.py new <type>` scaffolds one; a bare `slides.json`
   array still builds) or `deck.js` for pptx-themes, to the playbook's structure.
5. **Build**: `deliver.py check` until clean, `build --html` to trim overflow, then `--pdf`
   (self-comms); or render + visual-QA (pptx-themes). Narrate if the comm calls for it.
6. **Write `sources.md`** - claim-by-claim provenance; the board / registry is the live truth.
7. **Deliver** with `SendUserFile` so it opens in a viewer, not the terminal.

## The engine (`scripts/deliver.py`)

`check <spec>` reports every problem at once with rule ids - spec schema, sections vs the
type definition, block schema, voice lint. `build <spec> --html/--pdf` renders (headless
Chrome for PDF; the HTML is self-contained if Chrome is absent). `narrate <spec> --script`
drafts a spoken companion in deck order; rewrite it as speech, then `narrate <script>
--audio` renders it (macOS `say` by default). `types` and `new <type>` list and scaffold.

Config is selected by name, never restated per use: **types** (`types/*.json` - sections,
page budgets, guide strings, gather commands; a new deliverable type is one JSON file),
**themes** (`themes/*.json` - 7 palettes x 28 semantic tokens), **voices** (`voices/*.json` -
register, id policy, numeric budgets; doctrine runs as lint, waivable per spec), and
**project defaults** (`.claude/comms.local.md`, flat keys `theme` / `voice` / `repo` /
`audio`). Precedence: CLI flag > spec field > project local > type default. Slides use the
17-block dialect; an unsupported block is a hard error, never a silent drop. There is no
autofit: content past a 1280x720 slide clips, and overflow means the slide does too much.

## Hard rules (the standard's spine - never skip)

- **Lead with the outcome / the decision; bury the detail.** The reader's standing complaint:
  "I'm drowning in details I don't really need before I get to what I need to know."
- **Honest framing only.** Describe what is actually proven; call out gaps explicitly; never
  blanket accuracy or certification claims; never round up. External comms guard this hardest.
- **Numbers live in systems; the deck points** to the board / registry, as-of the date.
- **Pitch to the audience.** Self-comms are blunt and may name issue/PR ids — plain-English
  label first, id second; no bare ids or unexplained shorthand. External comms (board, client)
  drop internal jargon and unexplained ids, carry a confidential footer, and commit to no
  roadmap dates.

## Composes with

- **pptx-themes** - owns the palette, semantic theme tokens, typography, and visual QA for the
  two external comms. Invoke it when building an advisor or client deck.
- **handoff** - the EOD wrap-up is the readout; `/handoff` writes the canonical `HANDOFF.md`.
  Run `/handoff` first, then build the wrap-up from the refreshed file. Do not duplicate state.
- **readme-value-and-proof** - capture real app screenshots for the client overview's "what it
  looks like" slide; never use mockups where a real surface exists.

## Files

- `references/comm-package-standard.md` - shared toolchains, parameters, pipeline, voice, gotchas
- `examples/<type>/playbook.md` - per-comm one job, deck structure, gather, voice deltas
- `examples/<type>/sample.*` - a real worked artifact for that comm type (where one exists)
- `scripts/deliver.py`, `types/`, `themes/`, `voices/` - the engine and its named config

Done when `deliver.py check` is clean, the exported deck/PDF is delivered via `SendUserFile`,
and `sources.md` traces every claim back to a live source.
