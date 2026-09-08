# comms

Produce recurring communication deliverables — a morning briefing, end-of-day wrap-up, weekly
planning briefing, advisor board readout, or client product overview — as a deck, to one
consistent standard. Each deliverable is a dated folder under the project's briefings
directory (`_meta/briefings/` when a `_meta/` tree exists, else `briefings/` at the repo
root) holding the deck source, the exported deck, optional audio, and a `sources.md`
provenance file.

## When it triggers

Ask for any of those five by name, or for a "briefing", "status deck", "status readout",
"board deck", "comms package", or deck narration.

## The split that drives everything

Audience and stakes pick the toolchain, theme, and voice:

| Audience | Comm type | Toolchain |
|---|---|---|
| You | morning briefing · end-of-day wrap-up · weekly planning | `scripts/deliver.py`, fast and decision-first |
| External | advisor board readout · client product overview | `pptx-themes`, polished and hand-laid |

Each type has a self-contained playbook and a real worked example under `examples/<type>/`;
the shared machinery lives in `references/comm-package-standard.md`. The examples run on a
bare install of this skill alone — the advisor-board `sample.deck.js` takes its palette from
`themes/actuarial-signal.json` here rather than reaching into a sibling skill's install
directory, so nothing in `examples/` breaks when only this skill is present.

## Hard rules

**Lead with the outcome, bury the detail** — the standing complaint is drowning in detail
before reaching the decision. **Honest framing only** — describe what is actually proven and
call out gaps explicitly. **Claim-by-claim provenance** in `sources.md`; the board or registry
is the live truth, not the deck.

## The engine

`scripts/deliver.py` is stdlib-only Python bundled with the skill: one YAML/JSON spec in, a
validated, voice-linted, themed HTML/PDF deck out, plus an optional spoken companion. YAML
specs need PyYAML; JSON needs nothing. PDF export shells out to headless Chrome; without it,
ship the self-contained HTML. A bare `slides.json` array (the pre-spec deck shape) still
builds with defaults.

Doctrine is config selected by name, authored once here and never restated per use:

- **`types/`** — a deliverable's ordered sections with page budgets, guide strings, runnable
  source-gathering commands, and default theme and voice. A new type is one JSON file and
  zero engine changes. Shipped so far: `morning-briefing`.
- **`themes/`** — 7 palettes x 28 semantic tokens (transliterated from the pptx-themes token
  contract), injected into the deck CSS as custom properties.
- **`voices/`** — register, id policy, numeric budgets, guidance. Voice doctrine runs as lint
  with rule ids — all errors at once, waivable per spec.

A `.claude/comms.local.md` in a project sets house defaults (`theme`, `voice`, `repo`, the
narration provider `audio`, and `briefings_dir` to override the auto-detected briefings
directory) for every deck built inside it. Precedence: CLI flag > spec field > project local >
type default. `narrate` drafts a script from the deck, you rewrite it as speech, and `--audio`
renders it — macOS `say` by default, any other provider as a `{script}`/`{out}` command
template, so a hosted voice never becomes a dependency.

```sh
python3 scripts/deliver.py types
python3 scripts/deliver.py check examples/morning-briefing/sample.spec.json
python3 scripts/deliver.py build examples/morning-briefing/sample.spec.json --pdf /tmp/briefing.pdf
python3 scripts/deliver.py narrate examples/morning-briefing/sample.spec.json --script /tmp/vo.txt
python3 scripts/deliver.py narrate /tmp/vo.txt --audio /tmp/briefing.m4a   # macOS `say`
python3 scripts/deliver.py briefings-dir .                                # resolved <briefings-dir>
```

Composes with two sibling skills without replacing them: `pptx-themes` for the external decks,
and `handoff` (ships in `atelier`) for the end-of-day wrap-up. Install those alongside it
if you want the full set — neither arrives by way of this plugin.

## Install

```
claude plugin install code-desk@dotfiles-agents
```

Ships in the `code-desk` bundle only — its topical plugin owns it (decision-020).
