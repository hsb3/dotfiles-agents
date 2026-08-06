# comms

Produce recurring communication deliverables — a morning briefing, end-of-day wrap-up, weekly
planning briefing, advisor board readout, or client product overview — as a deck, to one
consistent standard. Each deliverable is a dated folder under `_meta/briefings/` holding the
deck source, the exported deck, optional audio, and a `sources.md` provenance file.

## When it triggers

Ask for any of those five by name, or for a "briefing", "status deck", "status readout",
"board deck", or "comms package".

## The split that drives everything

Audience and stakes pick the toolchain, theme, and voice:

| Audience | Comm type | Toolchain |
|---|---|---|
| You | morning briefing · end-of-day wrap-up · weekly planning | deck-builder MCP, fast and decision-first |
| External | advisor board readout · client product overview | `pptx-themes`, polished and hand-laid |

Each type has a self-contained playbook and a real worked example under `examples/<type>/`;
the shared machinery lives in `references/comm-package-standard.md`.

## Hard rules

**Lead with the outcome, bury the detail** — the standing complaint is drowning in detail
before reaching the decision. **Honest framing only** — describe what is actually proven and
call out gaps explicitly. **Claim-by-claim provenance** in `sources.md`; the board or registry
is the live truth, not the deck.

## What it needs

The deck-builder MCP server for the three self-comms. Composes with two sibling skills without
replacing them: `pptx-themes` for external decks, and `handoff` (ships in `foreman-kit`) for
the end-of-day wrap-up. Install those alongside it if you want the full set — none of them
arrive by way of this plugin.

## Install

```
claude plugin install comms@dotfiles-agents
```

Also ships as a member of the `code-desk` bundle.
