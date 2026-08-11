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
| Get a cited research answer, fix a setting that will not take effect, make an honest chart, draw a diagram, set up a repo, or ship a recurring briefing — anything that works on its own | [`solo-skills`](plugins/solo-skills/README.md) |
| Delegate work across subagents and keep long sessions from running out of context | [`atelier`](plugins/atelier/README.md) |
| Bring a repo up to a documented structure standard, then plan and report the work through it | [`code-desk`](plugins/code-desk/README.md) |
| Draw an architecture or flow diagram that renders on GitHub | [`diagrams`](plugins/diagrams/README.md) |
| Build an Obsidian plugin, or drive a vault from the terminal | [`obsidian-toolkit`](plugins/obsidian-toolkit/README.md) |
| Report a defect in a plugin you are using, without leaving the session | [`plugin-feedback`](plugins/plugin-feedback/README.md) |

## Catalog

| Plugin | Kind | What it does | Contents |
|---|---|---|---|
| [`solo-skills`](plugins/solo-skills/README.md) | bundle | Every skill that stands on its own, in one install: harness config, session discipline, research, diagrams, repo setup, comms, Obsidian dev. | 31 skills |
| [`code-desk`](plugins/code-desk/README.md) | bundle | Audit a repo against a documented structure standard, scaffold the gaps, then plan, track, and report the work that follows. | 10 skills |
| [`diagrams`](plugins/diagrams/README.md) | bundle | Structural diagrams with consistent SVG and PNG output: Mermaid, cloud architecture, draw.io, Excalidraw, Graphviz. | 4 skills |
| [`atelier`](plugins/atelier/README.md) | bundle | Tiered delegation agents plus session-discipline hooks: size a task, dispatch to the right model tier, keep every session clearable. | 8 skills · 4 agents · 9 hooks · 1 command |
| [`kaneo`](plugins/kaneo/README.md) | bundle | Track a repo's work on a live Kaneo board instead of in-repo task files, with board authority narrowing down the delegation chain. | 1 skill · 1 agent · 2 hooks |
| [`obsidian-toolkit`](plugins/obsidian-toolkit/README.md) | bundle | Build Obsidian plugins against the real API (lifecycle, chat UIs, in-plugin MCP servers) and automate vaults from the terminal. | 4 skills |
| [`plugin-feedback`](plugins/plugin-feedback/README.md) | bundle | Tell every session and worker that plugin defects are reportable, then file one to a fixed template instead of a free-handed gh call. | 2 hooks |

## How the plugins are split

A **bundle** groups things used together on one kind of work, so they toggle as a unit — the
code desk's audit reads the same standard its scaffold writes from, and `atelier`'s skills
are useless without the agents beside them. Anything shipping agents or hooks is a bundle
too, even when it carries no skill at all.

`solo-skills` is the other half of that idea. It carries every skill that needs nothing
beside it — no agent, no hook, no sibling skill — so its membership is derived rather than
curated: `scripts/check_solo_skills.py` re-reads the skill bodies and their bundled scripts
and works out which ones qualify.

**Per-skill installs are no longer offered.** Each of those skills used to ship as its own
one-skill plugin. A plugin is the unit of installation in Claude Code, so consolidating them
means taking the set rather than picking from it. Progressive disclosure is what makes that
cheap: the model reads each skill's one-line description to decide what to activate and only
loads a body when it fires.

Some skills are dual-homed, shipping in `solo-skills` and in a bundle. Each is one source
symlinked into both assemblies, not a copy, so both ship identical bytes and installing both
loads the skill once.

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
