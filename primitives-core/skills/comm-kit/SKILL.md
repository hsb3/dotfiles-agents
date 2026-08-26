---
name: comm-kit
description: Spec-driven engine for recurring communication deliverables - one YAML/JSON spec in, a validated, voice-linted, themed HTML/PDF deck out, plus an optional spoken companion. Ships deliverable types (morning briefing so far), 7 named themes, and named voice profiles; a bare legacy slides.json array still renders. Use when asked for a comm-kit deliverable or a spec-driven briefing, status deck, comm package, or deck narration/audio.
---

# comm-kit

One engine for the workflow every comm shares: structured input -> style/tone config by name
-> package -> check -> refine -> present. Authored once here, never per-use.

## Pipeline

1. **Package** - pick the deliverable type (`deliver.py types` lists sections, page budgets,
   guide strings, and the runnable source-gathering commands). Gather state with the type's
   `sources` commands - accuracy is the whole job. Author one spec file (YAML or JSON).
2. **Check** - `deliver.py check <spec>`: spec schema, sections vs the type definition,
   block schema, and voice lint, all errors at once with rule ids. Fix and re-run to clean.
3. **Refine** - `deliver.py build <spec> --html out.html`, open it, trim overflow. There is
   no autofit: content past a 1280x720 slide clips; overflow means the slide does too much.
4. **Present** - `deliver.py build <spec> --pdf out.pdf` (headless Chrome; if absent, ship
   the self-contained HTML). Deliver with SendUserFile so it opens in a viewer.
5. **Narrate** (optional) - `deliver.py narrate <spec> --script out.txt` drafts a spoken
   companion in deck order (markup stripped, the type's audio guidance in a `#` header).
   Rewrite it as speech, then `narrate out.txt --audio out.m4a`; `#` lines are never spoken.

## Spec

```yaml
type: morning-briefing        # deliver.py types; scaffold one with: deliver.py new <type>
title: "Morning briefing - 2026-08-26"
repo: owner/name              # linkifies bare issue refs (hash + number)
theme: boardroom              # optional - type default; 7 themes under themes/
voice: self-blunt             # optional - type default; profiles under voices/
waive: []                     # lint rule ids waived, visible in review
sections:                     # section ids from the type; each holds slides
  title: [ {blocks: [{type: heading, text: "..."}]} ]
```

Slides use the 17-block dialect (heading, subtitle, lead, bullets, columns, stat, callout,
divider, table, steps, timeline, matrix, quote, code, image, svg, chart) - unsupported
blocks are a hard error, never a silent drop. A bare top-level ARRAY of slides (the legacy
deck shape) is accepted as-is with defaults, so prior decks still render.

## Config, selected by name

- **Types** (`types/*.json`) - a deliverable's sections in order, each with a page budget
  and guide string, plus gather commands and default theme/voice. A new deliverable type is
  one JSON file; the engine does not change.
- **Themes** (`themes/*.json`) - 7 palettes x 28 semantic tokens, injected as CSS custom
  properties: actuarial-signal, boardroom (default), carbon-white, clinical-intelligence,
  human-outcomes, ivory, midnight (dark).
- **Voices** (`voices/*.json`) - register (fragments vs sentences), id policy
  (plain-English label first, id second), numeric budgets, and guidance strings. Doctrine
  is lint, not prose: every finding carries a rule id and can be waived per-spec.
- **Project defaults** (`.claude/comm-kit.local.md`) - YAML frontmatter, flat keys `theme` /
  `voice` / `repo` / `audio`, found by walking up from the spec. Precedence: **CLI flag >
  spec field > project local > type default**. `audio` picks the narration provider (`say`,
  `none`, or a `{script}`/`{out}` command template - no vendor SDK ever becomes a
  dependency). Absent: silent. Unreadable, or an unknown key: warn, then ignore.

## Output layout

A deliverable is a dated folder `<project>/_meta/briefings/<YYYY-MM-DD><type-slug>/` holding
the spec, exported deck, and a `sources.md` provenance file (claim-by-claim; the board or
registry is the live truth). Worked example: `examples/morning-briefing.spec.json`.
