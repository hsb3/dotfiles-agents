# repo-meta-structure

The canonical repo meta-structure standard, as consultable reference content. This is the
**single source** for the layout — nothing here is duplicated elsewhere, so when the standard
changes, it changes in these files.

## When it triggers

Use it whenever the question is "what is the standard for X" in a repo's layout: setting up a
new repo, reviewing an existing one, or checking what belongs where.

## What it covers

| Question is about… | Read |
|---|---|
| Directory layout: `_meta/`, `.claude/`, `.github/`, root files, the AVOID list | `references/layout.md` |
| A specific compliance check, its ID, or its pass condition | `references/checklist.md` |
| Planning-doc frontmatter in `_meta/plans/`, or communication-package intake | `references/planning-docs.md` |

It also ships the templates the standard describes under `assets/` — `.github/` template set,
gitignore and lefthook templates, and docs scaffolding.

## Reference only

This skill answers questions; it does not act. Two sibling skills read this same content and
do the work: `repo-compliance-audit` measures a repo against `references/checklist.md`, and
`mise-en-place-scaffold` creates missing structure from `assets/`. If the ask is "check this
repo" or "scaffold this repo", reach for those instead.

## Install

```
claude plugin install repo-meta-structure@dotfiles-agents
```

Also ships as a member of the `code-desk` bundle.
