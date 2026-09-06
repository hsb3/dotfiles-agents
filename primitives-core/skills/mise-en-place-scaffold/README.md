# mise-en-place-scaffold

Fill the gaps a compliance audit found. The audit measures a repo against the packaged
meta-structure standard; this skill creates the missing pieces — `_meta/` taxonomy, `.github/`
templates, required root files — from the same source the audit reads.

## When it triggers

Use it for "scaffold this repo", "run mise-en-place", "fill the audit gaps", or "set up a new
repo to the standard". One code path serves both brownfield compliance and greenfield setup:
against a fresh `git init` with a filled manifest, a single `--apply` produces the full
standard.

## The loop

Run the compliance audit first, review the gap table with the owner, then plan before applying:

```
python3 "${CLAUDE_PLUGIN_ROOT}/skills/mise-en-place-scaffold/scripts/scaffold.py" --plan
python3 "${CLAUDE_PLUGIN_ROOT}/skills/mise-en-place-scaffold/scripts/scaffold.py" --apply
```

`--plan` lists planned creations, conflicts, and non-mechanical items per checklist ID.
`--init-manifest` writes the commented `_meta/mise-en-place.yml` variance template for
per-repo deviations and GitHub-side knobs.

**Additive-only, by design.** It never overwrites, merges, edits, deletes, or moves an
existing file, never provisions GitHub-side objects, and never authors README, CLAUDE.md, or
AGENTS.md content. A conflict is reported, not resolved.

## Siblings

Measuring compliance is `repo-compliance-audit`; questions about what the standard *says* are
`repo-meta-structure`. All three read the same standard — it lives in one place.

## Install

```
claude plugin install mise-en-place@dotfiles-agents
```

Ships in the `mise-en-place` bundle. Needs only `python3` (stdlib).
