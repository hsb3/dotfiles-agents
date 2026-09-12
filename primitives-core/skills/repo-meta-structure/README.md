# repo-meta-structure

The canonical repo meta-structure standard, as consultable reference content. This is the
**single source** for the layout — nothing here is duplicated elsewhere, so when the standard
changes, it changes in these files.

Version 0.5.2 includes the final decision-link and checklist correction after this repository normalized its decision records.

## When it triggers

Use it whenever the question is "what is the standard for X" in a repo's layout: setting up a
new repo, reviewing an existing one, or checking what belongs where.

## What it covers

| Question is about… | Read |
|---|---|
| Directory layout: `_meta/`, `.claude/`, `.github/`, root files, the AVOID list | `references/layout.md` |
| A specific compliance check, its ID, or its pass condition | `references/checklist.md` |
| Planning-doc frontmatter in `_meta/plans/`, which desk files are exempt from it, or communication-package intake | `references/planning-docs.md` |

It also ships the templates the standard describes under `assets/` — `.github/` template set,
gitignore and lefthook templates, and docs scaffolding. The issue forms ship label-less on
purpose: labels are declared per-repo in `_meta/mise-en-place.yml` and provisioned by hand
with `gh`, since nothing in this marketplace creates them for you.

A couple of `references/checklist.md` rows (`CLAUDE-07`, the `HOOK-01` note) embed
worked-example paths from this repo itself — `dotfiles-agents/docs/decisions/...` — inside
their otherwise generic Detail text, since they cite this repo's own ADRs as the illustration.
Those literal paths drift silently if this repo's own ADR location ever moves; the generic
`path-exists-any: docs/decisions/ · backlog/decisions/` guidance in `DOCS-03/04/05` is the
actual checkable rule and is unaffected by that drift.

## Reference only

This skill answers questions; it does not act. Sibling skills read this same content and do
the work: `repo-compliance-audit` measures a repo against `references/checklist.md`,
`mise-en-place-scaffold` creates missing structure from `assets/`, and `planning-desk` runs
inside the `_meta/plans/` desk this standard defines. If the ask is "check this repo",
"scaffold this repo", or "plan this out", reach for those instead.

## Install

```
claude plugin install mise-en-place@dotfiles-agents
```

Ships in the `mise-en-place` bundle.
