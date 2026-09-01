---
name: comms
description: Produce your recurring communication deliverables - a morning status briefing, end-of-day wrap-up, weekly planning briefing, advisor board status readout, or client product overview - as a deck (plus optional audio) to a consistent standard. Use when you ask for any of those by name, or for a "briefing", "status deck", "status readout", "board deck", or "comms package". Self-comms render through a bundled stdlib-Python script (no MCP server needed). Composes with the pptx-themes skill (external decks) and the handoff skill (EOD wrap-up); it does not replace them.
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
| the decision for today | morning briefing | `render_deck.py` | yes (2-3 min) | `examples/morning-briefing/playbook.md` |
| to close today, tee up tomorrow | end-of-day wrap-up | `render_deck.py` (light) | optional | `examples/end-of-day-wrapup/playbook.md` |
| the week's plan + where we stand | weekly planning briefing | `render_deck.py` | yes (3-4 min) | `examples/weekly-planning/playbook.md` |
| a board status readout + the ask | advisor board readout | pptx-themes | optional | `examples/advisor-board-readout/playbook.md` |
| what a client gets + why to trust it | client product overview | pptx-themes | optional | `examples/client-product-overview/playbook.md` |

The split is by **audience and stakes**: the three self-comms are fast, decision-first, and
render through **`scripts/render_deck.py`** (bundled, stdlib-only Python - no MCP server); the
two external comms are polished, hand-laid, and use the **pptx-themes** skill. Audience drives
toolchain, theme, voice, and how honest framing is phrased.

## Workflow

1. **Resolve which comm** from the table; if ambiguous, ask. Read its `playbook.md` and look
   at the `sample.*` artifact next to it - the sample is the template for voice and structure.
2. **Read `references/comm-package-standard.md`** for the per-project parameters (auto-detect
   `<owner>/<repo>`, handoff file, gates), the toolchain pipeline, voice baseline, and gotchas.
3. **Gather current state** per the playbook - accuracy is the whole job (handoff + live counts
   + git log for internal comms; charter + product thesis for external comms).
4. **Author** the source (`slides.json` for `render_deck.py`, `deck.js` for pptx-themes) to the
   playbook's structure, mirroring the sample.
5. **Build**: `render_deck.py --validate` then `--pdf` (self-comms), or render + visual-QA
   (pptx-themes); narrate + export audio if the comm calls for it.
6. **Write `sources.md`** - claim-by-claim provenance; the board / registry is the live truth.
7. **Deliver** with `SendUserFile` so it opens in a viewer, not the terminal.

## Hard rules (the standard's spine - never skip)

- **Lead with the outcome / the decision; bury the detail.** The reader's standing complaint:
  "I'm drowning in details I don't really need before I get to what I need to know."
- **Honest framing only.** Describe what is actually proven; call out gaps explicitly; never
  blanket accuracy or certification claims; never round up. External comms guard this hardest.
- **Numbers live in systems; the deck points** to the board / registry, as-of the date.
- **Pitch to the audience.** Self-comms are blunt and may name issue/PR ids — plain-English
  label first, id second; no bare ids or unexplained shorthand (HB 2026-07-02). External comms
  (board, client) drop internal jargon and unexplained ids, carry a confidential footer, and
  commit to no roadmap dates.

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
