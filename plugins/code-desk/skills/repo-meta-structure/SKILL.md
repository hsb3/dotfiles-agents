---
name: repo-meta-structure
description: >-
  The canonical repo meta-structure standard — consult it whenever a question is about
  "what is the standard for X" in a repo's layout: the `_meta/` directory taxonomy
  (_archive/briefings/plans/operations/research + HANDOFF.md + README.md), the `.claude/`
  layout (what's tracked vs machine-local, commands/ as migration debt), the `.github/`
  template set, required root files, the gitignore conventions (track-by-default `_meta/`
  with the `operations/` ignore, `.env*` handling, the `.claude` stanza), the `_meta/plans/` planning-doc
  frontmatter schema, or where communication packages from the strategy desk land
  (`_meta/plans/inbox/`). Use when setting up or reviewing a repo's structure, answering
  layout questions, or checking what belongs where. This skill is reference content only —
  the compliance audit and mise-en-place scaffold are separate sibling skills that read
  this same content.
---

# Repo meta-structure standard

The **single source** for the canonical repo layout. Three consumers read this identical
content: a human/agent session (you, now), the repo-compliance-audit skill (checks against
`references/checklist.md`), and the mise-en-place scaffold skill (produces from `assets/`).
Nothing here is duplicated anywhere else — if the standard changes, it changes in these files.

## How to answer "what is the standard for X"

| Question is about… | Read |
|---|---|
| Directory layout: `_meta/`, `.claude/`, `.github/`, root files, the AVOID list | `references/layout.md` |
| A specific compliance check, its ID, or its pass condition | `references/checklist.md` |
| Planning-doc frontmatter in `_meta/plans/`, or communication-package intake (`inbox/`) | `references/planning-docs.md` |
| The exact `.gitignore` a conforming repo carries | `assets/gitignore.template` |
| The `.github/` file set (issue forms, PR template, dependabot, workflows) | `assets/github/` |

Answer from the reference content directly — do not reconstruct the standard from memory or
from how some other repo happens to look. Repos deviate; the standard does not. Legitimate
per-repo variance lives only in that repo's `_meta/mise-en-place.yml` manifest (owned by the
mise-en-place scaffold skill), never as a silent exception to this content.

## What this skill does NOT do

- **No auditing** — pass/gap verdicts come from the sibling `repo-compliance-audit` skill,
  which reads `references/checklist.md` from this skill's directory.
- **No scaffolding** — creating missing files/folders is the sibling `mise-en-place-scaffold`
  skill, which copies from this skill's `assets/`.
- **No naming grammar** — agent/skill/hook naming is owned by the naming-taxonomy standard.
- **No memory content rules** — `.claude/memory/` placement is layout (here); the memory
  taxonomy, index format, and promotion rules are the memory-taxonomy standard (packaged as
  its own sibling skill).
- **No CI authoring** — the workflow files in `assets/github/workflows/` ship as templates
  copied from the best current instances; what a repo's CI should *do* is out of scope.

## For the audit and scaffold (machine consumers)

- Checklist contract: `references/checklist.md` — a table `ID | Area | Check | Pass condition`
  with stable IDs (`META-xx`, `CLAUDE-xx`, `GH-xx`, `ROOT-xx`, `IGNORE-xx`, `AVOID-xx`,
  `PLANS-xx`). The Check column declares a check type from a closed vocabulary; see the
  file's header. IDs are stable across skill renames.
- Scaffold sources: `assets/gitignore.template` (→ `.gitignore`) and `assets/github/`
  (→ `.github/`, structure-preserving copy).
- Locate this content from a sibling skill via the plugin root:
  `${CLAUDE_PLUGIN_ROOT}/skills/repo-meta-structure/references/checklist.md`.
