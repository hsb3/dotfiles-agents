---
name: author-primitive
description: >-
  Scaffold a new primitives-core/<type>/<id>/ body plus its primitives-core.yaml roster
  row for this repo, so a new skill or agent starts conformant with the roster schema,
  the per-item README template, and the identity-neutrality lint. Use when adding a new
  skill or agent to this marketplace. Project-local: this scaffold hardcodes this repo's
  own conventions (the roster schema, make ci, the ADR 0017 symlink-assembly layout), so
  it is never rostered or shipped in a plugin.
---

# Author a primitive

Scaffold the source-of-truth body and roster row for a new skill or agent. Fill in the
`TODO` placeholders afterward; this only gets you to a conformant starting point.

## Run it

```sh
python3 .claude/skills/author-primitive/scripts/scaffold.py skill <id> [--description TEXT]
python3 .claude/skills/author-primitive/scripts/scaffold.py agent <id> [--description TEXT]
```

This creates:

- **skill**: `primitives-core/skills/<id>/{SKILL,README}.md`, a `type: skill` roster row,
  and a `plugins/solo-skills/skills/<id>` symlink — a fresh skill is dependency-free by
  construction, so `solo-skills` is its derived home (`scripts/check_solo_skills.py`).
- **agent**: `primitives-core/agents/<id>.md` + a `type: agent` roster row. No symlink —
  no assembly derives agent membership.

Both roster rows default `origin: authored`, `disposition: untriaged`,
`targets: [claude-code]`. Fails loudly (no overwrite) if the id already exists on disk, in
the roster, or (skill) in `plugins/solo-skills/skills/`.

## After scaffolding

Write the real `SKILL.md`/agent body and README content. For a scaffolded **skill**,
`make ci` stays red until you close two gates by hand — deliberate repo design: these are
human-facing claims a fresh stub has nothing true to say for yet, so a scaffold must not
fabricate them.

1. Root `README.md` — bump the `solo-skills` row's `Contents` cell (`<n> skills`). Gate:
   `check_catalog.py` (in `make ci`).
2. `plugins/solo-skills/README.md` — name the new member. Gate: `check_readmes.py` (in
   `make ci`).
3. `plugins/solo-skills/.claude-plugin/plugin.json` + `marketplace.json` — bump
   `version`. Gate: `check_version_bump.py` (CI-only, a ship-time human call).

If the skill should NOT ship solo, earn that with a real dependency (a sibling skill
path, an agent dispatch, a hook) or a `SYSTEM_EXEMPTIONS` entry in
`scripts/check_solo_skills.py`, and remove the symlink. Shipping in any OTHER plugin is
its own hand-authored step (ADR 0017) — add `skills/<id>` (or `agents/<id>.md`) there
plus its `## Install` line.

## Removing a scaffolded primitive

```sh
rm -rf primitives-core/skills/<id> plugins/solo-skills/skills/<id>  # skill
rm -f primitives-core/agents/<id>.md                                # agent
git checkout -- primitives-core.yaml    # restores the roster row byte-for-byte
```
