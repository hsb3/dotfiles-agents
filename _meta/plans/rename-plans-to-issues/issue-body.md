Rename `_meta/plans/` to `_meta/issues/` so the directory name states its purpose: each subfolder is a GitHub issue's working desk (`issue_body.md` = the contract, `plan.md` = build detail), not a loose "plan."

This is a **planning-desk skill change**, not a one-off `git mv` — the name is baked into the skill, its toolkit, and every reference across both host repos.

## Deliverable
Rename the directory and update every place the path is encoded:
- `primitives-core/skills/planning-desk/` — `SKILL.md`, `references/*`, `assets/plans-README.md`, `assets/_config.template.md`, and the seven `_utils/*.py` scripts (`reconcile.py`, `coverage.py`, `sync-bodies.py`, `sequence.py`, etc. — they hardcode `_meta/plans`).
- This repo's live desk: `_meta/plans/` -> `_meta/issues/`, `_meta/plans/_config.md`, `_meta/plans/README.md`.
- `.gitignore` negation stanza (`!_meta/plans/**` -> `!_meta/issues/**`).
- All references in `CLAUDE.md`, `AGENTS.md`, `docs/`, other plans, and the sibling ra-platform desk if it adopted the skill.
- Rebuild `targets/` (planning-desk is a distributed primitive).

## Acceptance criteria
- `rg -n "_meta/plans" ` returns zero hits outside historical `_meta/_archive/`.
- `python3 _meta/issues/_utils/reconcile.py` runs clean against the renamed desk.
- `make ci` green; `targets/` regenerated (no hand-edits); planning-desk deployed bundle reflects the new name.
- Skill docs and `_config` refer to `_meta/issues/` throughout.

## Dependencies & gates
- **Blocks on:** nothing; coordinate with the both-files rule (sibling issue) since both edit the same toolkit + skill.
- **Gates:** `make ci` + `make build-check` (planning-desk edit regenerates `targets/`); `project-workflow` plugin version bump; canonical-doc amendment (CLAUDE.md path references).
