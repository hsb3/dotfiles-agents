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

- **skill**: `primitives-core/skills/<id>/SKILL.md` + `README.md`, plus a `type: skill`
  roster row appended to `primitives-core.yaml`.
- **agent**: `primitives-core/agents/<id>.md`, plus a `type: agent` roster row.

Both roster rows default `origin: authored`, `disposition: untriaged`,
`targets: [claude-code]`. Fails loudly (no overwrite) if the id already exists on disk or
in the roster.

## After scaffolding

Write the real `SKILL.md`/agent body and README content, then run `make ci`. Shipping the
primitive in a plugin is a separate, hand-authored step (ADR 0017: plugin membership is
symlink assemblies, not a roster field) — add `skills/<id>` (or `agents/<id>.md`) to the
chosen `plugins/<id>/` assembly and update the README's `## Install` line. A brand-new
standalone skill with no plugin yet will fail `make symlinks`' solo-skills membership
check until it is wired into a plugin (`solo-skills` for a dependency-free skill).

## Removing a scaffolded primitive

```sh
rm -rf primitives-core/skills/<id>      # or primitives-core/agents/<id>.md
git checkout -- primitives-core.yaml    # restores the roster row byte-for-byte
```
