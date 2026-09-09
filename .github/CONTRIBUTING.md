# Contributing

This marketplace ships **primitives** (skills, agents, commands, hooks) authored in `primitives-core/`,
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

- **`origin: authored | sourced | vendored`** is provenance and is immutable per entry.
  `primitives-core/` holds **self-authored** bodies only — every entry sourced from under
  `primitives-core/` must be `origin: authored`
  ([ADR 0015](../docs/decisions/0015-self-authored-primitives-only.md)). Third-party material is
  recorded **by reference** in [`../externals.yaml`](../externals.yaml) (non-null `upstream` +
  `ref`), never copied into the source tree ([ADR 0003](../docs/decisions/0003-externals-tracked-not-vendored.md)).
- Primitive layout: `skills/<id>/SKILL.md` (+ optional `references/`, `scripts/`, `assets/`),
  `agents/<id>.md` (frontmatter), `commands/<id>.md` (frontmatter; the command loads a skill
  and drives it rather than restating one — decision-010), `hooks/<id>/hook.py`
  (+ `config.json`) — the ratified hook-dir layout.

## Removing a primitive or a plugin

Deletions are the one publish-surface change nothing else can see: a removal moves no
version, breaks no symlink and orphans no roster entry, so every gate stays green while a
skill leaves the marketplace with no record a consumer can read. `scripts/check_removals.py`
closes that — it diffs the published unit set (`origin/main`) against this tree and requires
each missing unit to be **declared by the commit that removed it**.

Removing a unit is four things in one PR:

1. Delete the body under `primitives-core/` and the symlink(s) in every `plugins/<id>/`
   assembly that shipped it (a whole plugin: the assembly directory plus its
   `.claude-plugin/marketplace.json` entry).
2. Drop its `primitives-core.yaml` roster entry.
3. Bump the `version` of every plugin that shipped it — the published bytes changed
   (`scripts/check_version_bump.py`).
4. **Declare it.** The commit message must name the removed unit and say it went. Both:
   the id on its own reads as a refactor, a bare "removed some cruft" names nothing.
   Say where the capability went, or that it has none — that sentence is what lands on the
   release page, so write it for the person who was using the thing.

```
refactor(board-triage): collapse github-project-board into a GitHub Projects adapter script

Retires the standalone skill…: its three scripts merge into one contract-shaped
export/apply adapter beside kata_board.py, and the skill, its roster entry, and its
solo-skills symlink are deleted.
```

The declaration must survive the **squash**: PRs land on `dev` as one squashed commit, so
the sentence has to be in the PR title/description that becomes that commit's message — a
declaration written only in an intermediate branch commit is gone by the time the gate looks.
The gate matches the unit id plus a removal verb (`remove*`/`delete*`/`retire*`/`fold*`)
anywhere in subject or body, case-insensitively. That match is *evidence* of a declaration,
not proof of one; it is deliberately loose because the declaration is prose (decision-013),
and what it actually stops is the removal nobody wrote a sentence about.

`python3 scripts/check_removals.py --notes` renders the same set as the "Removed in this
publish" section of the release page, so the removal reaches consumers and not only CI.

**Recovering something removed before this gate existed** — the history is the record:

```bash
git log --diff-filter=D --name-only -- primitives-core/skills primitives-core/agents
git show <commit>^:primitives-core/skills/<name>/SKILL.md    # read a deleted body
```

## What `make ci` enforces

`make ci` runs the machine floor plus the drift guards; each is also a standalone target:

| Command | Enforces |
|---|---|
| `make check` | **Roster ↔ disk drift** — every roster `source` exists; provenance-manifest schema valid; no orphaned bodies. Also the consumer-catalog guard and the **plugin-README diagram** guard (see below). |
| `make identity` | **Identity-neutrality** — no hardcoded name/org/repo/issue in any *shipped* body (`primitives-core/{skills,agents,commands,hooks}` + the `plugins/` assemblies; skill READMEs travel with their skill). Root docs, this file, and everything under `docs/` (ADRs included) are exempt (they don't ship). |
| `make provenance` | **Provenance** — every `primitives-core/` body is `origin: authored`; every `externals.yaml` entry has non-null `upstream` + `ref` (ADR 0015 / ADR 0003). |
| `make hook-layout` | **Hook layout** — hooks use the ratified `hooks/<name>/hook.py` dir layout, never flat handlers or inline-in-settings. |
| `make agent-refs` | **Agent references resolve** — no shipped body under `primitives-core/` names an agent that is neither a roster agent nor a harness built-in. Reads two shapes only: a `subagent_type`/`agent_type`/`agent` key with a literal value, and a backticked name immediately *before* the word agent/subagent. Unbackticked prose is never a reference, and neither is the mirror shape (`` agent `x` ``), where ordinary prose matches. `python3 scripts/check_agent_refs.py --report` lists every reference with its verdict, and exits non-zero if any dangles. |
| `make symlinks` | **Symlink-assembly lint** (ADR 0017) — every link under `plugins/` resolves in-repo; the root marketplace manifest and the assemblies match 1:1. |
| `make harness-coupling` | `harness/` imports only itself + stdlib (no repo coupling). |
| `make flow` | **Repo-flow DAG** — every tracked top-level path is homed in `flow.yaml`; a new top-level path must claim a node there. |
| `make test` | **Unit tests** — `python3 -m unittest`, **stdlib-only** (zero install is an invariant; fixtures live under `tests/`, never under `primitives-core/`). |

Adding a whole new top-level path also needs a home in `flow.yaml` (the `make flow` guard). Files
that nest under an already-homed path (e.g. under `primitives-core/`, `docs/`,
`.github/`) need no flow change.

## Plugin READMEs

Each `plugins/<id>/README.md` is hand-authored (bundle READMEs are regular files, not
symlinks) and **must carry a Mermaid diagram** under a `## How it fits together` heading,
placed before the section that enumerates the plugin's pieces. The rule for what it must
show — draw the trigger and the flow, never the inventory — plus the format, placement, and
constraints are in
[`../docs/readme-diagram-standard.md`](../docs/readme-diagram-standard.md).
`make check` enforces the mechanical parts.

Render any diagram you write before trusting it — a house-rule violation renders blank on
GitHub with no error:

```bash
npx -y @mermaid-js/mermaid-cli -i diagram.mmd -o /tmp/out.svg
```

## Generated artifacts

Nothing generated is tracked (ADR 0017). If something must be generated (e.g. the opencode
laydown via `gen_opencode.py` + `translation.yaml`), it is generated at install/run time by
a deterministic generator — never committed. A tracked artifact that needs a regen step is a
design smell; raise it before adding one.

## Where work is tracked

**A live kata board is the task system** — project `dotfiles-agents`, bound by `.kata.toml`
and served by the hosted daemon, not files in this tree. Planned work and its status live
there; the board replaced the in-repo Backlog.md tree on 2026-08-11 (via a Kaneo board,
archived 2026-09-02 once its open tasks were carried over; the retired tree is recoverable
from git history). The workflow — search first, claim, keep `work.attention` truthful, close
with evidence — is the kata block in AGENTS.md, and that block is the law.

**GitHub issues stay bug-report intake only** — the bug template is the only one offered. A
reported bug becomes a board task when it is planned; after the fix merges into `dev`, close
the issue by hand (a `Closes #N` in a PR into `dev` does NOT auto-close — auto-close fires
only on the default branch).

Architecture decisions are a separate thing from tracked work: they are ADRs under
[`../docs/decisions/`](../docs/decisions/), append-only, and they stay in the repo.
