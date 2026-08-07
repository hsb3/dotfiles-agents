# dotfiles-agents

A Claude Code plugin marketplace of coding-agent extenders (skills, agents, and hooks),
installed by name. Everything is authored in this repo unless it says otherwise:
`pptx-themes` layers a curated theme system over Anthropic's `pptx` skill, vendored verbatim
with its license. Every bundle closes with an "Honest scope" section stating what it does
not do.

## Install

```sh
# Claude Code — add the marketplace once, then install plugins by name
claude plugin marketplace add hsb3/dotfiles-agents
claude plugin install atelier@dotfiles-agents

# opencode — generated at install time from the source branch
git clone --branch dev https://github.com/hsb3/dotfiles-agents && cd dotfiles-agents
scripts/install_opencode.sh --global            # ~/.config/opencode/{skills,agents}/
scripts/install_opencode.sh --project <dir>     # <dir>/.opencode/{skills,agents}/
```

The opencode clone is pinned to `dev` because the installer lives on the source branch, not
the published one. That laydown is a subset of the catalog: skills and agents travel, hooks
do not (opencode has no equivalent event surface), and skills rostered Claude-Code-only stay
behind.

## Start here

| I want to… | Install |
|---|---|
| Delegate work across subagents and keep long sessions from running out of context | [`atelier`](plugins/atelier/README.md) |
| Bring a repo up to a documented structure standard, then plan and report the work through it | [`code-desk`](plugins/code-desk/README.md) |
| Draw an architecture or flow diagram that renders on GitHub | [`diagrams`](plugins/diagrams/README.md) |
| Build an Obsidian plugin, or drive a vault from the terminal | [`obsidian-toolkit`](plugins/obsidian-toolkit/README.md) |
| Get a researched, cited answer instead of one web lookup | [`deep-research`](plugins/deep-research/README.md) |
| Choose between competing tools and defend the choice with primary sources | [`tech-eval-research`](plugins/tech-eval-research/README.md) |
| Fix a permission, hook, or setting that is not taking effect | [`claude-code-config`](plugins/claude-code-config/README.md) |
| Author or debug a Claude Code skill, hook, or agent | [`claude-code-expertise`](plugins/claude-code-expertise/README.md) |
| Make a chart that is legible and honest rather than merely colorful | [`dataviz`](plugins/dataviz/README.md) |
| Ship a status briefing or board readout on a recurring cadence | [`comms`](plugins/comms/README.md) |
| Get a batch of decisions from a human without a wall of chat questions | [`owner-signoff`](plugins/owner-signoff/README.md) |
| Give a repo tracked editor config for both VS Code and Zed | [`editor-project-config`](plugins/editor-project-config/README.md) |

## Catalog

| Plugin | Kind | What it does | Contents |
|---|---|---|---|
| [`code-desk`](plugins/code-desk/README.md) | bundle | Audit a repo against a documented structure standard, scaffold the gaps, then plan, track, and report the work that follows. | 10 skills |
| [`diagrams`](plugins/diagrams/README.md) | bundle | Structural diagrams with consistent SVG and PNG output: Mermaid, cloud architecture, draw.io, Excalidraw, Graphviz. | 4 skills |
| [`atelier`](plugins/atelier/README.md) | bundle | Tiered delegation agents plus session-discipline hooks: size a task, dispatch to the right model tier, keep every session clearable. | 6 skills · 4 agents · 7 hooks |
| [`obsidian-toolkit`](plugins/obsidian-toolkit/README.md) | bundle | Build Obsidian plugins against the real API (lifecycle, chat UIs, in-plugin MCP servers) and automate vaults from the terminal. | 4 skills |
| [`claude-code-config`](plugins/claude-code-config/README.md) | standalone | Settings, permissions, hooks, env vars, and MCP servers routed to the right file by precedence, with a take-effect check. | 1 skill |
| [`claude-code-expertise`](plugins/claude-code-expertise/README.md) | standalone | Map of Claude Code's extension surfaces: which one fits a need, what its contract is, and how to debug it. | 1 skill |
| [`comms`](plugins/comms/README.md) | standalone | Recurring status deliverables (morning briefing, wrap-up, weekly plan, board readout) shipped as a deck, to one standard. | 1 skill |
| [`dataviz`](plugins/dataviz/README.md) | standalone | Chart design rules to consult before writing chart code: mark selection, anti-patterns to refuse, colorblind-safe palette. | 1 skill |
| [`deep-research`](plugins/deep-research/README.md) | standalone | Multi-source investigation ending in a cited report: load-bearing claims must survive an attempted refutation before being asserted. | 1 skill |
| [`editor-project-config`](plugins/editor-project-config/README.md) | standalone | Tracked .vscode and .zed folders designed in one pass: associations, toolchain-matched settings, tasks, and cross-editor parity. | 1 skill |
| [`github-project-board`](plugins/github-project-board/README.md) | standalone | Stand up and operate one GitHub Project (v2) board: fields, views, dependencies, and the weekly triage cadence. | 1 skill |
| [`iterm2`](plugins/iterm2/README.md) | standalone | Configure iTerm2 past its silent failures: preferences model, dynamic profiles, shell integration, default-terminal binding. | 1 skill |
| [`mise-en-place-scaffold`](plugins/mise-en-place-scaffold/README.md) | standalone | Create the repo structure a compliance audit found missing; additive only, plans before it applies, never overwrites. | 1 skill |
| [`opencode-expertise`](plugins/opencode-expertise/README.md) | standalone | Reference for opencode's extension surfaces and how each Claude Code equivalent translates onto them. | 1 skill |
| [`owner-signoff`](plugins/owner-signoff/README.md) | standalone | Put a batch of decisions in a local browser form instead of a wall of chat questions; answers land back in the session. | 1 skill |
| [`pptx-themes`](plugins/pptx-themes/README.md) | standalone | PowerPoint decks with a curated theme layer (semantic tokens, approved palettes, visual QA) over Anthropic's pptx skill. | 1 skill |
| [`private-fork`](plugins/private-fork/README.md) | standalone | Run a private mirror of an upstream repo: remotes, a delete-vs-disable rubric, a divergence ledger, and the merge cycle. | 1 skill |
| [`project-memory`](plugins/project-memory/README.md) | standalone | Move a project's agent memory into the repo so it travels with a clone, and recover it after the folder is moved. | 1 skill |
| [`readme-value-and-proof`](plugins/readme-value-and-proof/README.md) | standalone | Rewrite a README as an honest pitch backed by screenshots captured from the app actually running, never mockups. | 1 skill |
| [`repo-meta-structure`](plugins/repo-meta-structure/README.md) | standalone | The repo layout standard as reference content: directory taxonomy, `.claude` and `.github` layout, checks, and templates. | 1 skill |
| [`tech-eval-research`](plugins/tech-eval-research/README.md) | standalone | Comparative technology evaluation: ranked shortlist, capability matrix, and a recommendation built from primary sources. | 1 skill |

## Bundles and standalones

A **bundle** groups skills used together on one kind of work, so they toggle as a unit — the
code desk's audit reads the same standard its scaffold writes from. A **standalone** is a
single skill that stands on its own; install it when you want that one capability without
the rest.

Cross-desk items ship standalone and never inside a bundle. `dataviz`, `deep-research`, and
`claude-code-config` apply to any kind of work, so folding them into a desk would tie an
unrelated toggle to them.

Some skills are dual-homed: they ship both inside `code-desk` and as standalone plugins, and
[the bundle's README](plugins/code-desk/README.md) lists which. Each is one source symlinked
into both assemblies, not a copy, so the bundle and the standalone ship identical bytes.

## How this repo is built

`dev` is the source branch. `main` is publish-only, built by CI, and carries the `plugins/`
tree, `.claude-plugin/marketplace.json`, and this page (plus a `.gitignore`).

Everything else lives on `dev`: the source tree, the guards that check it, and the
contribution loop.

- [`primitives-core/`](https://github.com/hsb3/dotfiles-agents/tree/dev/primitives-core) —
  the one place a skill, agent, or hook is edited. The plugin directories are thin
  assemblies of links over it, so a fix lands everywhere the primitive ships.
- [Agent instructions](https://github.com/hsb3/dotfiles-agents/blob/dev/AGENTS.md): the
  source-of-truth rules and the build interface.
- [Contributor guide](https://github.com/hsb3/dotfiles-agents/blob/dev/.github/CONTRIBUTING.md):
  branch off `dev`, PR into `dev`, and the checks that run.
