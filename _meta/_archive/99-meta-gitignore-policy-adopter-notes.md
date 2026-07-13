---
title: "Adopter migration note — _meta/ track-by-default (ADR-0006)"
type: note
status: active
created: 2026-07-13
purpose: Deliverable D of #99 — how each adopter of the repo-meta-structure gitignore stanza flips from broad-ignore + negation to track-by-default.
---

# Adopter migration — `_meta/` track-by-default (ADR-0006)

_Policy: track `_meta/` by default; ignore only `operations/` content, tool caches, and OS
litter. Canonical decision: `docs/decisions/0006-meta-tracked-by-default.md` (this repo)._

## The flip, per repo

1. **Replace the `_meta` stanza** in `.gitignore` with:

   ```gitignore
   # _meta: tracked by default (ADR-0006, dotfiles-agents); operations/ content is never tracked
   _meta/operations/*
   !_meta/operations/.gitkeep
   ```

   Ensure global `.DS_Store` and `__pycache__/` rules exist (they cover `_meta/` again once
   the negations are gone); add a targeted `_meta/plans/_utils/__pycache__/` line if the
   repo has no global Python section.

2. **MANDATORY pre-flip secrets scan** of everything that becomes trackable:
   `git ls-files --others --exclude-standard -- _meta/` to list the newly visible set, then
   grep it for key/token/DSN/private-key patterns. Anything secret moves to
   `_meta/operations/` before the flip.

3. **Commit or rule-local, nothing ambiguous:** every formerly-ignored `_meta/` artifact is
   either committed or deliberately placed in `operations/`. Litter (`.DS_Store`, caches)
   stays ignored by the global rules.

4. **Verify:** `git check-ignore -v _meta/operations/probe` (ignored) and
   `git check-ignore _meta/research/probe.md` (silent, exit 1 — tracked-by-default), then
   re-run the compliance audit — the IGNORE-01..18 rows test the new policy as of #99.

## Adopters

| Adopter | What to change |
|---|---|
| `dotfiles-agents-workbench` | Full flip (steps 1–4). Its stanza mirrors the old template; re-audit after (the wb#30 charter gap is unrelated). |
| `fleet-dashboard` (pilot, #33) | Full flip (steps 1–4); the #33 re-audit consumes the updated IGNORE rows. |
| `dotfiles` — `claude-code/.claude/rules/project-protocol.md` §2 | Prose only: §2 currently states "_meta/ gitignored by default … durable items tracked via gitignore negations". Reword to track-by-default + operations/-only ignore, citing ADR-0006. Same for any memory-hygiene/instruction stanza that repeats the negation pattern. |
