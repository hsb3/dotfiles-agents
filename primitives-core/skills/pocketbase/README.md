# pocketbase

Operate a PocketBase backend — standalone binary or Go package mode — with bundled Python
helpers and on-demand references.

## When it triggers

Any PocketBase operational task: collection and record CRUD, superuser/user auth, backups,
migration file generation (JS and Go), Go hooks and custom routes, and design guidance for
API rules, relations, and security patterns.

Pairs with `pocketbase-best-practices`, which ships in the same plugin: this skill is the
**operational** surface (how to drive a running instance); that one is the **design** surface
(63 prioritized rules for schema, rules, and performance).

## What it is

- `SKILL.md` — mode detection, bootstrap, and the operational procedure.
- `scripts/` — Python helpers for auth, collections, records, backups, config, migration
  templating, e2e helpers, and health checks. Stdlib-only; run with `--help` first.
- `references/` — sixteen detail docs loaded on demand (API surfaces, field types, relation
  patterns, JSVM hooks, Go framework/migrations, e2e testing, gotchas).
- `assets/` — JS and Go migration templates.

## Provenance

**Self-authored (`origin: authored`). No upstream exists to pin.**

This skill was written outside any public repository and reached its consuming projects by
hand-copying, so it has no resolvable upstream, no license grant from a third party, and no
ref to track. It therefore fails the "pinnable + attributable" criterion in
the source repo's vendoring rule and is **not** vendored content —
it is first-party, maintained here.

Consolidated from four hand-copied divergent copies. Three were byte-identical; the fourth
carried the only substantive edit, which is preserved here:

- `references/file-handling.md` — **file-token erratum.** The earlier text claimed a protected
  file token is *single-use, invalidated after first successful use*. That is wrong. The token
  is reusable for its full lifetime (~2 minutes), proven live against PocketBase v0.39.9 by
  fetching the same protected file repeatedly and getting 200 each time.
- `SKILL.md` — dropped a non-standard `allowed-tools` frontmatter key.

The pre-consolidation original is unrecoverable; the earliest surviving copy is the effective
baseline. Further modifications held in other checkouts are harvested into this copy as they
surface — this directory is the single source of truth from here on.

## Install

```
claude plugin install pocketbase@dotfiles-agents
claude plugin install solo-skills@dotfiles-agents
```

Ships in the `pocketbase` and `solo-skills` bundles.
