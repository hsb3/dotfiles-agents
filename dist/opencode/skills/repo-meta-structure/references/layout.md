# The canonical repo layout

The standard every adopted repo follows. Per-repo variance (e.g. a `dev` default branch)
lives only in that repo's `_meta/mise-en-place.yml` manifest — the standard defines the
invariants, the manifest defines the knobs. The machine-checkable form of every item below
is a row in [`checklist.md`](checklist.md).

## `_meta/` — the local working desk

Tracked by default; the only ignored path is `operations/` content, plus tool caches and
OS litter (Decision: ADR-0006 — see [`../assets/gitignore.template`](../assets/gitignore.template)).
Desk content is clone-survivable by default; deliberately-local scratch belongs in
`operations/` or outside the repo.

| Entry | Purpose |
|---|---|
| `_archive/` | Superseded working material — moved, never deleted |
| `briefings/` | Dated readouts (`yyyy-mm-dd-subject/`) |
| `plans/` | The **code planning desk** — issue bodies and build plans authored by coding agents (the `planning-desk` skill's workspace). Also holds `inbox/` for communication-package intake — see [`planning-docs.md`](planning-docs.md) |
| `operations/` | Live URLs, credentials, runbooks with secrets — never tracked, never in `docs/` |
| `research/` | Live investigations; findings graduate to `docs/` or issues |
| `HANDOFF.md` | Cold-start bridge — tracked, secret-free |
| `README.md` | States this taxonomy |
| `mise-en-place.yml` | Per-repo variance manifest — tracked (format owned by the mise-en-place scaffold skill: `skills/mise-en-place-scaffold/references/manifest.md`) |

## `.claude/`

| Entry | Note |
|---|---|
| `agents/`, `hooks/`, `memory/`, `rules/`, `skills/` | `memory/` is git-tracked (taxonomy and index rules owned by the memory taxonomy standard, packaged as the project-memory skill); hooks are script + config dirs, never inline in settings (packaging depth owned by the hook-composition standard) |
| `commands/` | Present-but-discouraged per the skills-over-commands decision — the audit flags command usage as migration debt, not a structural gap |
| `worktrees/` | Harness-managed agent worktrees; always ignored |
| `settings.json` | Tracked (project policy) |
| `settings.local.json` | Machine-local; ignored |

**Headless-run note:** several settings are set globally on the maintainer's machine and do
**not** transfer to devcontainers or GitHub Actions runners — the tracked `settings.json`
must carry anything a headless run depends on.

## `.github/`

- `ISSUE_TEMPLATE/` — `config.yml`, `bug.yml`, `feature.yml`, `epic.yml`. The issue forms
  ship **label-less by design**: a hardcoded label name assumes a taxonomy the target repo
  may not have (and the scaffold neither creates nor verifies labels). Labels are declared
  per-repo in `_meta/mise-en-place.yml` (`gh_issue_labels`), provisioned by the
  github-project-board skill, and applied at issue creation.
- `workflows/` — `ci.yml`, `claude-review.yml` (Claude reviews PRs), `claude.yml` (tag
  Claude in issues/comments); `release.yml` only if the repo publishes releases. These ship
  as **templates** (see [`../assets/github/workflows/`](../assets/github/workflows/));
  authoring new CI behavior is out of scope for this standard.
- `dependabot.yml`, `PULL_REQUEST_TEMPLATE.md`

## Root

- `README.md` (value-and-proof style), `CLAUDE.md`, `AGENTS.md`, `Makefile`, `lefthook.yml`
  (template: [`../assets/lefthook.template.yml`](../assets/lefthook.template.yml) — pre-push `make ci` by default; hooks mirror CI),
  `.gitignore`, `.mcp.json`
- `docs/`, `scripts/`, `tests/`
- `CHANGELOG.md` only if the repo publishes releases
- Optional: `.githooks/`, `.gitattributes`

**Task-runner note:** the standard names **Makefile** as the v1 default task runner; the
Makefile-vs-justfile-vs-mise.toml weighing is an open decision. If it lands differently, this
line and the single `ROOT-04` checklist row change — nothing else.

## `docs/`

The floor (checklist rows `DOCS-01..05`):

| Path | What |
|---|---|
| `README.md` | Orientation: what `docs/` holds, the docs-vs-`_meta/` boundary (durable, audience-facing vs local working desk). Templated skeleton — the repo fills the index. |
| `CHARTER.md` | The **one canonical page with a stated precedence rule** ("if anything disagrees with this page, this page wins"). Authored content — the scaffold never creates it. |
| `decisions/` | ADRs: `NNNN-kebab-title.md`, zero-padded sequential, append-only (supersede or correct-with-dated-erratum, never rewrite). |
| `decisions/README.md` | The convention + the index of decisions. |
| `decisions/0000-template.md` | The ADR template (Status · Context · Decision · Consequences · Affects). |

Deeper taxonomy — design workspaces, `operations/`, `api/`, `images/`, `sops/` — is
**per-repo shape**, guidance only, never rows. Two boundaries hold: secrets never live in
`docs/` (they live in untracked `_meta/operations/`), and fast-moving working notes belong
in `_meta/`, not `docs/`.

## AVOID list

- `TODO.md`, `NOTE.md`, `NOTES.md` or similar at root — this material belongs in `_meta/`.
  The audit flags these; the scaffold's migration guidance moves their content into `_meta/`.

## `.gitignore` conventions

The conforming template is [`../assets/gitignore.template`](../assets/gitignore.template).
The load-bearing parts (Decision: ADR-0006):

- **`_meta/` is tracked by default** — no broad-ignore, no negation machinery. Every desk
  subtree (`_archive/`, `briefings/`, `plans/`, `plans/inbox/`, `research/`) and every
  durable file (`README.md`, `HANDOFF.md`, `mise-en-place.yml`) tracks with no extra rule
  (checklist rows `IGNORE-02..06`, `IGNORE-13..16`).
- **`operations/` content is the one ignored `_meta/` path** — the pair
  `_meta/operations/*` + `!_meta/operations/.gitkeep` keeps secrets/live-ops material local
  while the empty dir survives a fresh clone (checklist rows `IGNORE-01`, `IGNORE-15`).
- **The global litter/cache rules apply again inside `_meta/`** now that no negation
  re-includes them: the top-of-file `.DS_Store` rule covers `_meta/` Finder litter, and the
  targeted `_meta/plans/_utils/__pycache__/` rule keeps desk-toolkit bytecode out (checklist
  rows `IGNORE-18`, `IGNORE-17`).
- **`.env*` with `!.env*.example`** — secrets ignored, example files tracked.
- **The `.claude` narrow-ignore stanza** — ignore `settings.local.json`, `worktrees/`,
  `*.lock`, `**/.DS_Store`; everything else in `.claude/` (memory, rules, skills,
  settings.json) stays tracked.
