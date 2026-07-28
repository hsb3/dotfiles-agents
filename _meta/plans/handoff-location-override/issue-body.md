## What

A per-project override for where foreman-kit looks for and writes the session-handoff file,
honored by all three consumers of the hardcoded path list:

- `primitives-core/hooks/session-handoff-surfacer/hook.py:48-53` — `CANDIDATE_PATHS` is the
  fixed trio `_meta/HANDOFF.md` / `HANDOFF.md` / `.claude/HANDOFF.md`, even though the hook
  already carries env-override plumbing (`_env_int`, `_env_path`) for its other knobs.
- `primitives-core/hooks/handoff-freshness-guard/hook.py:43-47` — same fixed trio; its
  "no handoff file found" message (`hook.py:151-152`) names only those three paths.
- `primitives-core/skills/handoff/SKILL.md:3,24,39-40` — the skill's description and body
  hardcode the trio and the discovery precedence.

When the override is set, it takes precedence; when absent, the standard trio applies
unchanged.

## Why

The trio bakes in the code-desk `_meta/` taxonomy. A project that manages tasks with a
different system has no sanctioned home for its handoff: motivating case is
`~/developer/tmp-learn-pocketbase`, which uses Backlog.md instead of the code-desk
conventions — there is no `_meta/`, and the natural doc home is Backlog.md's own tree. Today
foreman-kit's hooks silently find nothing (or nag about a missing handoff) and `/handoff`
writes `_meta/HANDOFF.md` into a layout that doesn't want it. foreman-kit is supposed to be
convention-light (delegation + session continuity); the handoff location is the one place it
imports a code-desk convention.

**Open owner decision — override mechanism** (recommend 1):

1. `.claude/foreman-kit.local.md` frontmatter key (e.g. `handoff_path:`) per the documented
   plugin-settings pattern — discoverable, per-project, trackable; hooks parse the one key
   with stdlib.
2. Env var (e.g. `FOREMAN_KIT_HANDOFF_PATH`) via the project's `.claude/settings.json` `env`
   block — least code (hooks already read env), but invisible to the skill prose and easy to
   lose.

## Done when

- [ ] With the override set to a non-standard path (e.g. `backlog/HANDOFF.md`),
      `session-handoff-surfacer` surfaces that file on cold start and
      `handoff-freshness-guard` checks that file's freshness — proven by unit tests, not
      inspection.
- [ ] The freshness guard's "no handoff file found" message names the override mechanism
      alongside the default trio.
- [ ] `skills/handoff/SKILL.md` documents the override; `/handoff` and `/handoff init`
      read/write the overridden location when set.
- [ ] No override present → behavior byte-identical to today (existing tests still pass).
- [ ] Tests are stdlib-only (`python3 -m unittest`), fixtures under `tests/` tempdirs; and
      `make ci` (roster check + build-check + test) is green with `dist/` regenerated via
      `make build`.

## Context

- Sibling issue: #221 (bundle refocus / standalone-useful components), same motivating
  project.
- foreman-kit is the sole home of the handoff skill + the four delegation hooks
  (`primitives-core.yaml:25-27`, ADR 0016).
- The "existing handoffs: never relocate; update where it lives" rule
  (`skills/handoff/SKILL.md:39-40`) should extend naturally: an overridden path is just a
  fourth possible "where it lives".
