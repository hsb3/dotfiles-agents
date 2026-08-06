# dotfiles-agents

A Claude Code marketplace of proven coding-agent extenders, assembled from a single canonical
source (`primitives-core/`) into installable plugin bundles.

The lineup is organized around desk sets: one desk bundle — **code-desk** (next-release
execution under a documented repo standard, now also carrying the executive-desk overhead:
planning, comms, board triage, deck themes) — plus three kits — **foreman-kit** (tiered
delegation agents and session-discipline hooks, enabled on every desk), **diagrams**
(structural diagrams: Mermaid, Python cloud-architecture diagrams, draw.io, Excalidraw,
Graphviz), and **obsidian-toolkit** (Obsidian plugin-dev guidance and vault automation) —
and eleven standalone one-skill plugins (**claude-code-config**, **claude-code-expertise**,
**dataviz**, **deep-research**, **github-project-board**, **opencode-expertise**,
**owner-signoff**, **pptx-themes**, **private-fork**, **project-memory**,
**tech-eval-research**). Cross-desk items ship standalone, never inside a desk bundle.
One source tree serves both runtimes (ADR 0017): the marketplace resolves by name as
`<plugin>@dotfiles-agents` for Claude Code, and opencode installs by laydown.

## Install

```sh
# Claude Code — add the repo as a marketplace, install plugins by name
claude plugin marketplace add hsb3/dotfiles-agents
claude plugin install code-desk@dotfiles-agents

# opencode — generated at install time from the same source tree
git clone https://github.com/hsb3/dotfiles-agents && cd dotfiles-agents
scripts/install_opencode.sh --global            # ~/.config/opencode/{skills,agents}/
scripts/install_opencode.sh --project <dir>     # <dir>/.opencode/{skills,agents}/
```

## Layout

| Path | What |
|---|---|
| `primitives-core/` | the single source copy of every primitive (`skills/`, `agents/`, `hooks/`); a skill's README travels with it (`skills/<id>/README.md`) |
| `plugins/` | thin symlink assemblies (ADR 0017): one dir per plugin, hand-authored `plugin.json`/`hooks.json`/bundle README, everything else symlinked into `primitives-core/` |
| `.claude-plugin/marketplace.json` | the marketplace root manifest — each plugin listed by relative `./plugins/<id>` source |
| `primitives-core.yaml` | the roster — provenance manifest of every primitive (ADR 0017: membership lives in the assemblies, not here) |
| `translation.yaml` | the opencode capability matrix, read by `scripts/gen_opencode.py` at install time (task-4) |
| `scripts/` | floor + assembly guards and `gen_opencode.py` |
| `tests/` | stdlib-only unit tests (zero install) |
| `backlog/decisions/` | decisions: the in-repo ADR mirrors + backlog-native rulings |
| `flow.yaml` + `backlog/docs/FLOW.md` | the repo-flow DAG — the home of every part, machine-checked by `make flow` |

## Build interface

`make ci` is the task interface (CI runs it on every PR). See `make help`.

| Target | Does |
|---|---|
| `make check` | roster ↔ disk drift guard (provenance-manifest schema) |
| `make symlinks` | symlink-assembly lint (ADR 0017): `plugins/` links resolve in-repo; marketplace ↔ assemblies 1:1 |
| `make test` | run the unit tests |
| `make ci` | all gates: floor + assembly/flow guards |

**Nothing generated is tracked** (ADR 0017). Change a primitive under `primitives-core/` and
it is live everywhere it ships — the assemblies are pointers, and `make ci` fails if a link
breaks or an assembly and the marketplace manifest disagree.

## Governance

`dev` is the source branch; every change lands via PR into `dev`. `main` is CI-published
(publish-only). See `backlog/decisions/` for the dev/main rule and `.claude/HANDOFF.md` for the
current build state.
