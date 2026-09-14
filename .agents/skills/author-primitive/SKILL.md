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
python3 .agents/skills/author-primitive/scripts/scaffold.py skill <id> --description TEXT
python3 .agents/skills/author-primitive/scripts/scaffold.py agent <id> [--description TEXT]
```

`--description` is required for `skill` (one line, no `|`) — it is used verbatim in
`SKILL.md`'s frontmatter and in the derived artifacts below, so a stub has nothing
honest to put there. Optional for `agent` (defaults to a `TODO` placeholder).

This creates:

- **skill**: `primitives-core/skills/<id>/{SKILL,README}.md`, a `type: skill` roster row,
  a `plugins/solo-skills/skills/<id>` symlink (a fresh skill is dependency-free by
  construction, so `solo-skills` is its derived home — `scripts/check_solo_skills.py`), a
  member row in its README's `**Uncategorized**` table, and the derived count fixed in
  the root `README.md` catalog row — both from the same `--description`, not invented prose.
- **agent**: `primitives-core/agents/<id>.md` + a `type: agent` roster row. No symlink,
  no README edits — no assembly derives agent membership.

Both roster rows default `origin: authored`, `disposition: untriaged`,
`targets: [claude-code]`. Fails loudly (no overwrite) if the id already exists on disk, in
the roster, or (skill) in `plugins/solo-skills/skills/`.

## After scaffolding

`make ci` is green right after scaffolding a skill. Two things remain for a human, neither
gated by `make ci`: move the `**Uncategorized**` row into its real category once you
write the real body (editorial — the scaffold can't choose it), and bump
`plugins/solo-skills`'s version in `plugin.json` + `marketplace.json` at ship time
(`scripts/check_version_bump.py`, CI-only — a human call, not something to script).

**A helper script the skill needs ships as an asset**: a stdlib-only script goes under
`skills/<id>/scripts/` and the body runs it as `python3 "<plugin-root>/skills/<id>/scripts/<name>.py"`.
Never a machine-local CLI — not in the body, not as `requires: cli:<name>` (`make identity` flags both).

If the skill should NOT ship solo, earn that with a real dependency (a sibling skill
path, an agent dispatch, a hook) or a `SYSTEM_EXEMPTIONS` entry in
`scripts/check_solo_skills.py`, and undo the symlink/README row/count fix by hand.
Shipping in any OTHER plugin is its own hand-authored step (ADR 0017) — add `skills/<id>`
(or `agents/<id>.md`) there plus its `## Install` line.

## Removing a scaffolded primitive

```sh
rm -rf primitives-core/skills/<id> plugins/solo-skills/skills/<id>       # skill
rm -f primitives-core/agents/<id>.md                                     # agent
git checkout -- primitives-core.yaml README.md plugins/solo-skills/README.md
```
