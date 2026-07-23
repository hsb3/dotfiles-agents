# pptx-themes

Create, edit, and review PowerPoint presentations with a curated theme layer — semantic
theme tokens, approved color palettes, monospaced typography, and a visual-QA workflow —
composed over Anthropic's vendored `pptx` skill for the underlying `.pptx` machinery.

## When it triggers

Use it for any deck, slide, presentation, or `.pptx` task. Where this skill and the base
`pptx` skill disagree on colors or fonts, this skill wins — it overrides the generic
palette/font suggestions with the curated theme system.

Attribution for the vendored `pptx` base (source, pinned ref, license) lives in the skill's
own `README.md` and in the repo's `externals.yaml` — see the shipped skill body.

## Install

```
claude plugin install pptx-themes@dotfiles-agents
```

Also ships as a member of the `code-desk` bundle.
