# pptx-themes

Create, edit, and review PowerPoint presentations with a curated theme layer — semantic
theme tokens, approved color palettes, monospaced typography, and a visual-QA workflow —
composed over Anthropic's vendored `pptx` skill for the underlying `.pptx` machinery.

## When it triggers

Use it for any deck, slide, presentation, or `.pptx` task. Where this skill and the base
`pptx` skill disagree on colors or fonts, this skill wins — it overrides the generic
palette/font suggestions with the curated theme system.

## What it is

- **Authored layer** (`SKILL.md`, `assets/theme-tokens.js`, `references/`, `scripts/`,
  `evals/`) — the theme system: it overrides the base skill's generic palette/font suggestions
  with a consistent set of deck themes and an explanatory narrative register.
- **Vendored base** (`base/`) — Anthropic's `pptx` skill, taken **verbatim** for the underlying
  `.pptx` create/edit/validate machinery. It is not modified.

## Attribution

The `base/` directory is the **Anthropic `pptx` skill**, vendored verbatim:

- Source: <https://github.com/anthropics/skills>, path `skills/pptx`
- Pinned ref: `fa0fa64bdc967915dc8399e803be67759e1e62b8`
- License: see `base/LICENSE.txt` (© Anthropic, PBC) — retained unchanged.

The original files (including `base/SKILL.md`, `base/scripts/`, and `base/LICENSE.txt`) are kept
in place and unmodified to satisfy the attribution obligation.

Do not edit `base/` — update the pin instead (a new ref, re-vendored verbatim). The authored
theme layer is what this repo maintains. SKILL.md's "Found an error?" section is where
corrections land, and where upstream-worthy ones get pointed at the anthropics/skills tracker.

## Install

```
claude plugin install code-desk@dotfiles-agents
```

Ships in the `code-desk` bundle.
