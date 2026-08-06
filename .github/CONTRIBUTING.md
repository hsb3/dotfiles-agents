# Contributing

This marketplace ships **primitives** (skills, agents, hooks) authored in `primitives-core/`,
listed in the `primitives-core.yaml` roster, and distributed as thin symlink assemblies under
`plugins/<id>/` (ADR 0017 — no build step; nothing generated is tracked). This page is the
single entry point for landing a change; the canonical rules live
in [`../CLAUDE.md`](../CLAUDE.md) and [`../primitives-core/README.md`](../primitives-core/README.md)
(source-of-truth — this page links, it does not restate them).

## The contribution loop

1. **Branch off `dev`.** All work integrates on `dev`; `main` is CI-published and off-limits
   (publish is `.github/workflows/publish.yml`, never a local checkout). Never commit to or merge
   into the default branch.
2. **Edit `primitives-core/` only.** It is the single canonical source copy of every primitive.
   `plugins/<id>/` are thin symlink assemblies over it (ADR 0017) — hand-authored
   `plugin.json`/`hooks.json`/bundle READMEs, symlinks for everything else; the root
   `.claude-plugin/marketplace.json` lists each plugin. An edit at source is live everywhere
   the primitive ships — there is no build step. (Shipping a primitive in another plugin =
   one more symlink in that assembly + nothing else.)
3. **Gate locally:** `make ci` (see below) must be fully green.
4. **Open a PR into `dev`.** CI re-runs `make ci` on every PR into `dev`.

```bash
git switch -c my-change dev
# …edit under primitives-core/ , update primitives-core.yaml if adding/removing a primitive…
make ci         # run the full gate; must be green
git push -u origin my-change
gh pr create --base dev
```

`make help` lists every target.

## The roster (`primitives-core.yaml`)

The roster — not a directory listing — is the provenance manifest (ADR 0017); the drift guard
reads it. Every entry carries the schema (fields and values in
[`../primitives-core/README.md`](../primitives-core/README.md#roster-entry-schema-provenance-manifest-adr-0017)):
`id`, `type`, `source` (must exist on disk), `origin`, `disposition`, `targets`, `requires`.
Plugin **membership** is not a roster field — membership is the symlink assemblies under
`plugins/<id>/`.

- **`origin: authored | sourced`** is provenance and is immutable per entry.
  `primitives-core/` holds **self-authored** bodies only — every entry sourced from under
  `primitives-core/` must be `origin: authored`
  ([ADR 0015](../backlog/decisions/0015-self-authored-primitives-only.md)). Third-party material is
  recorded **by reference** in [`../externals.yaml`](../externals.yaml) (non-null `upstream` +
  `ref`), never copied into the source tree ([ADR 0003](../backlog/decisions/0003-externals-tracked-not-vendored.md)).
- Primitive layout: `skills/<id>/SKILL.md` (+ optional `references/`, `scripts/`, `assets/`),
  `agents/<id>.md` (frontmatter), `hooks/<id>/hook.py` (+ `config.json`) — the ratified hook-dir
  layout.

## What `make ci` enforces

`make ci` runs the machine floor plus the drift guards; each is also a standalone target:

| Command | Enforces |
|---|---|
| `make check` | **Roster ↔ disk drift** — every roster `source` exists; provenance-manifest schema valid; no orphaned bodies. |
| `make identity` | **Identity-neutrality** — no hardcoded name/org/repo/issue in any *shipped* body (`primitives-core/{skills,agents,hooks}` + the `plugins/` assemblies; skill READMEs travel with their skill). Root docs, this file, ADRs, and `backlog/` are exempt (they don't ship). |
| `make provenance` | **Provenance** — every `primitives-core/` body is `origin: authored`; every `externals.yaml` entry has non-null `upstream` + `ref` (ADR 0015 / ADR 0003). |
| `make hook-layout` | **Hook layout** — hooks use the ratified `hooks/<name>/hook.py` dir layout, never flat handlers or inline-in-settings. |
| `make symlinks` | **Symlink-assembly lint** (ADR 0017) — every link under `plugins/` resolves in-repo; the root marketplace manifest and the assemblies match 1:1. |
| `make harness-coupling` | `harness/` imports only itself + stdlib (no repo coupling). |
| `make flow` | **Repo-flow DAG** — every tracked top-level path is homed in `flow.yaml`; a new top-level path must claim a node there. |
| `make test` | **Unit tests** — `python3 -m unittest`, **stdlib-only** (zero install is an invariant; fixtures live under `tests/`, never under `primitives-core/`). |

Adding a whole new top-level path also needs a home in `flow.yaml` (the `make flow` guard). Files
that nest under an already-homed path (e.g. under `primitives-core/`, `backlog/`,
`.github/`) need no flow change.

## Generated artifacts

Nothing generated is tracked (ADR 0017). If something must be generated (e.g. the opencode
laydown via `gen_opencode.py` + `translation.yaml`), it is generated at install/run time by
a deterministic generator — never committed. A tracked artifact that needs a regen step is a
design smell; raise it before adding one.

## Where work is tracked

**Backlog.md is the task system** (backlog decision-1): planned work, drafts, decisions, and
milestones live in the `backlog/` tree (`backlog board` for the live view). **GitHub issues
are bug-report intake only** — the bug template is the only one offered. A reported bug gets
a backlog task when it is planned; after the fix merges into `dev`, close the issue by hand
(a `Closes #N` in a PR into `dev` does NOT auto-close — auto-close fires only on the default
branch).
