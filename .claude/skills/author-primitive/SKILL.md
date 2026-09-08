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

- **skill**: `primitives-core/skills/<id>/SKILL.md` + `README.md`, a `type: skill` roster
  row, and a `plugins/solo-skills/skills/<id>` symlink — a fresh skill is dependency-free
  by construction, so `solo-skills` is its derived home
  (`scripts/check_solo_skills.py`: membership is derived, not curatorial).
- **agent**: `primitives-core/agents/<id>.md`, plus a `type: agent` roster row. No
  symlink — there is no assembly that derives agent membership.

Both roster rows default `origin: authored`, `disposition: untriaged`,
`targets: [claude-code]`. Fails loudly (no overwrite) if the id already exists on disk, in
the roster, or (skill) in `plugins/solo-skills/skills/`.

## After scaffolding

Write the real `SKILL.md`/agent body and README content, then run `make ci`. If the skill
should NOT ship solo, it must earn that by carrying a real dependency (a sibling skill
path, an agent dispatch, a hook) or a `SYSTEM_EXEMPTIONS` entry in
`scripts/check_solo_skills.py` — remove the symlink to match. Shipping in any OTHER plugin
is a separate, hand-authored step (ADR 0017: membership is symlink assemblies, not a
roster field) — add `skills/<id>` (or `agents/<id>.md`) to that `plugins/<id>/` assembly
and add its `## Install` line. Shipping the `solo-skills` bump for real also needs a
version bump there (`scripts/check_version_bump.py`, CI-only) — a human call at ship time.

## Removing a scaffolded primitive

```sh
rm -rf primitives-core/skills/<id> plugins/solo-skills/skills/<id>  # skill
rm -f primitives-core/agents/<id>.md                                # agent
git checkout -- primitives-core.yaml    # restores the roster row byte-for-byte
```
