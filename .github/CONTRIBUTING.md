# Contributing

This marketplace ships **primitives** (skills, agents, hooks) authored in `primitives-core/`,
listed in the `primitives-core.yaml` roster, and assembled into the distributed `dist/` lanes by
`make build`. This page is the single entry point for landing a change; the canonical rules live
in [`../CLAUDE.md`](../CLAUDE.md) and [`../primitives-core/README.md`](../primitives-core/README.md)
(source-of-truth — this page links, it does not restate them).

## The contribution loop

1. **Branch off `dev`.** All work integrates on `dev`; `main` is CI-published and off-limits
   (publish is `.github/workflows/publish.yml`, never a local checkout). Never commit to or merge
   into the default branch.
2. **Edit `primitives-core/` only.** It is the single canonical source copy of every primitive.
   `plugins/<id>/` are thin symlink assemblies over it (ADR 0017) — hand-authored
   `plugin.json`/`hooks.json`/bundle READMEs, symlinks for everything else; the root
   `.claude-plugin/marketplace.json` lists each plugin. The `dist/` lanes (`dist/claude-code/`,
   `dist/opencode/`) are **generated** — never hand-edit them (they retire with task-3).
3. **Regenerate:** `make build` rewrites the `dist/` lanes deterministically from source.
4. **Gate locally:** `make ci` (see below) must be fully green.
5. **Open a PR into `dev`.** CI re-runs `make ci` on every PR into `dev`.

```bash
git switch -c my-change dev
# …edit under primitives-core/ , update primitives-core.yaml if adding/removing a primitive…
make build      # regenerate the dist lanes from source
make ci         # run the full gate; must be green
git push -u origin my-change
gh pr create --base dev
```

`make help` lists every target.

## The roster (`primitives-core.yaml`)

The roster — not a directory listing — is the authoritative membership manifest; the drift guard
and the assembler read it. Every entry carries the full schema (fields and values in
[`../primitives-core/README.md`](../primitives-core/README.md#roster-entry-schema)):
`id`, `type`, `source` (must exist on disk), `shelf`, `origin`, `disposition`, `targets`,
`plugins`, `requires`.

- **`origin: authored | sourced`** is provenance and is immutable per entry.
  `primitives-core/` holds **self-authored** bodies only — every entry sourced from under
  `primitives-core/` must be `origin: authored`
  ([ADR 0015](../docs/decisions/0015-self-authored-primitives-only.md)). Third-party material is
  recorded **by reference** in [`../externals.yaml`](../externals.yaml) (non-null `upstream` +
  `ref`), never copied into the source tree ([ADR 0003](../docs/decisions/0003-externals-tracked-not-vendored.md)).
- Primitive layout: `skills/<id>/SKILL.md` (+ optional `references/`, `scripts/`, `assets/`),
  `agents/<id>.md` (frontmatter), `hooks/<id>/hook.py` (+ `config.json`) — the ratified hook-dir
  layout.

## What `make ci` enforces

`make ci` runs the machine floor plus the drift guards; each is also a standalone target:

| Command | Enforces |
|---|---|
| `make check` | **Roster ↔ disk drift** — every roster `source` exists; schema + provenance shape valid; no orphaned bodies. |
| `make identity` | **Identity-neutrality** — no hardcoded name/org/repo/issue in any *shipped* body (`primitives-core/{skills,agents,hooks}` + the `plugins/` assemblies; skill READMEs travel with their skill). Root docs, this file, ADRs, and `_meta/` are exempt (they don't ship). |
| `make provenance` | **Provenance** — every `primitives-core/` body is `origin: authored`; every `externals.yaml` entry has non-null `upstream` + `ref` (ADR 0015 / ADR 0003). |
| `make hook-layout` | **Hook layout** — hooks use the ratified `hooks/<name>/hook.py` dir layout, never flat handlers or inline-in-settings. |
| `make catalog` | **Skill-catalog** — standalone-skill eligibility, drift, and one-skill-wrapper byte-identity. |
| `make build-check` | **Marketplace regen drift** — the committed `dist/` lanes match a fresh regen from source (run `make build` if this fails). |
| `make harness-coupling` | `harness/` imports only itself + stdlib (no repo coupling). |
| `make flow` | **Repo-flow DAG** — every tracked top-level path is homed in `flow.yaml`; a new top-level path must claim a node there. |
| `make test` | **Unit tests** — `python3 -m unittest`, **stdlib-only** (zero install is an invariant; fixtures live under `tests/`, never under `primitives-core/`). |

Adding a whole new top-level path also needs a home in `flow.yaml` (the `make flow` guard). Files
that nest under an already-homed path (e.g. under `primitives-core/`, `docs/`, `_meta/`,
`.github/`) need no flow change.

## Generated artifacts

Every generated artifact has a deterministic generator **and** a `--check` drift guard, so the
committed copy can never silently diverge from source. Never hand-edit a generated file — change
the source under `primitives-core/`, then `make build`. Add new generated artifacts the same way,
and wire their `--check` into `make ci`.
