# dotfiles-agents

A Claude Code and Codex plugin marketplace of coding-agent extenders (skills, agents, and hooks),
installed by name. Original primitives are maintained here; Carbon builder, PocketBase best practices and
the PPTX base include upstream material under component-specific licenses. See the
[license inventory](https://github.com/hsb3/dotfiles-agents/blob/dev/docs/licenses.md). Every bundle closes with an "Honest scope" section stating what it does
not do.

[Documentation](https://github.com/hsb3/dotfiles-agents/blob/dev/docs/README.md) ·
[Site preview and publication](https://github.com/hsb3/dotfiles-agents/blob/dev/docs/site.md)

## Install

Codex uses the same repository and plugin names:

```sh
codex plugin marketplace add hsb3/dotfiles-agents
codex plugin add atelier@dotfiles-agents
```

Atelier needs [project activation and native role setup](plugins/atelier/README.md#codex-role-setup)
before dispatching isolated workers. To refresh, run `codex plugin marketplace upgrade dotfiles-agents`, then repeat
`codex plugin add <plugin>@dotfiles-agents` and rerun that plugin’s project setup.
Code-desk and PocketBase also provide project role setup;
Claude slash commands remain convenience entry points for invoking their corresponding skills.


```sh
# Claude Code — add the marketplace once, then install plugins by name
claude plugin marketplace add hsb3/dotfiles-agents
claude plugin install atelier@dotfiles-agents

# Both laydown installers generate at install time, so they run from a clone of the source branch
git clone --branch dev https://github.com/hsb3/dotfiles-agents && cd dotfiles-agents

# Claude Code, skill by skill — no marketplace
scripts/install_claude_skills.sh --global                        # ~/.claude/skills/
scripts/install_claude_skills.sh --project <dir> --only handoff  # <dir>/.claude/skills/

# opencode — generated non-Atelier lane
scripts/install_opencode.sh --global            # ~/.config/opencode/{skills,agents}/
scripts/install_opencode.sh --project <dir>     # <dir>/.opencode/{skills,agents}/
```

Both clones are pinned to `dev` because the installers live on the source branch, not the
published one. **To refresh either laydown, pull that clone and re-run the installer.**
Uninstall by deleting the folder.

The skill laydown is the fine-grained alternative to a bundle: `--only <id>[,<id>]` takes a
subset, and a laid-down skill is invoked as `/<name>` where the same skill from a plugin is
`/<plugin>:<name>`. It carries **skills only** — agents, hooks, commands, and the MCP servers
a few skills need arrive with a plugin, and the generated laydown README names every primitive
that stays behind and why. Plugins still install from the marketplace.

A refresh of the **skill** laydown replaces only the skill folders it installed: each carries
a `.laydown` marker, and the installer refuses any folder that lacks one rather than
overwriting a skill you wrote. The older **opencode** installer has no such marker and
overwrites whatever sits at the destination — check that directory before re-running it.

The opencode laydown is a subset of the catalog: skills and agents travel; hooks and commands
do not travel through this laydown (opencode's event surface is TS-on-Bun plugins, so this
repo's script+config hooks would need a per-hook wrapper — deferred, not impossible), and
skills rostered Claude-Code-only stay behind. The installer copies the generated manifest to
`<root>/dotfiles-agents-laydown.md`, which names every primitive left behind and why.
**Atelier is deliberately separate:** install its hand-authored opencode port from
[`hsb3/dotfiles-agents-oc`](https://github.com/hsb3/dotfiles-agents-oc).

## Start here

| I want to… | Install |
|---|---|
| Get a cited research answer, fix a setting that will not take effect, make an honest chart, check that a test can fail, or set up a repo — anything that works on its own and has no plugin of its own | [`solo-skills`](plugins/solo-skills/README.md) |
| Delegate work across subagents and keep long sessions from running out of context | [`atelier`](plugins/atelier/README.md) |
| Decide what a repo's quality gate must enforce, then run review triage, board triage, and status comms through it | [`code-desk`](plugins/code-desk/README.md) |
| Run a planning desk over a tracker (kata first), or lay out/audit/scaffold a repo's in-repo _meta/ structure | [`mise-en-place`](plugins/mise-en-place/README.md) |
| Draw an architecture or flow diagram that renders on GitHub | [`diagrams`](plugins/diagrams/README.md) |
| Build an Obsidian plugin, or drive a vault from the terminal | [`obsidian-toolkit`](plugins/obsidian-toolkit/README.md) |
| Build a PocketBase backend, drive a running one from the terminal, or delegate the build to agents that already carry the backend laws | [`pocketbase`](plugins/pocketbase/README.md) |
| Report a defect in a plugin you are using, without leaving the session | [`plugin-feedback`](plugins/plugin-feedback/README.md) |

## Catalog

| Plugin | Kind | What it does | Contents |
|---|---|---|---|
| [`solo-skills`](plugins/solo-skills/README.md) | bundle | Every skill that stands alone with no topical plugin: harness config, research, test quality, chart design, API and TUI craft, repo setup. | 14 skills |
| [`code-desk`](plugins/code-desk/README.md) | bundle | Set a repo's quality contract and its proven gate, then keep the release loop honest: review triage, board triage, and status comms. | 7 skills · 1 agent · 2 hooks · 1 command |
| [`diagrams`](plugins/diagrams/README.md) | bundle | Structural diagrams with consistent SVG and PNG output: Mermaid, cloud architecture, draw.io, Excalidraw, Graphviz. | 4 skills |
| [`atelier`](plugins/atelier/README.md) | bundle | Tiered delegation agents plus session-discipline hooks: size a task, dispatch to the right model tier, keep every session clearable. | 8 skills · 5 agents · 14 hooks · 1 command |
| [`mise-en-place`](plugins/mise-en-place/README.md) | bundle | A planning desk over a tracker adapter (kata first): layout and memory standards, read-only audit, fill-only scaffold, item-body form. | 6 skills |
| [`obsidian-toolkit`](plugins/obsidian-toolkit/README.md) | bundle | Build Obsidian plugins against the real API (lifecycle, chat UIs, in-plugin MCP servers) and automate vaults from the terminal. | 4 skills |
| [`pocketbase`](plugins/pocketbase/README.md) | bundle | Build and operate PocketBase backends: drive a running instance, and design the schema, API rules, and queries against 63 prioritized rules. | 2 skills · 3 agents · 2 hooks |
| [`carbon`](plugins/carbon/README.md) | standalone | Build and audit IBM Carbon Design System UIs: IBM's official carbon-builder skill driving the hosted Carbon MCP server it registers. | 1 skill · 1 MCP server |
| [`bun`](plugins/bun/README.md) | standalone | The bun toolchain as the default JS and TS runtime: command mapping off npm habits, built-ins that replace dependencies, measured traps. | 1 skill |
| [`kenn-forge`](plugins/kenn-forge/README.md) | standalone | Maintainer triage over a running kenn-forge daemon: review candidates, diffs and CI, local review state, coding-agent handoff. | 1 skill |
| [`plugin-feedback`](plugins/plugin-feedback/README.md) | bundle | Tell every session and worker that plugin defects are reportable, then file one to a fixed template instead of a free-handed gh call. | 2 hooks |

## How the plugins are split

A **bundle** groups things used together on one kind of work, so they toggle as a unit — the
code desk's audit reads the same standard its scaffold writes from, and `atelier`'s skills
are useless without the agents beside them. Anything shipping agents or hooks is a bundle
too, even when it carries no skill at all.

`solo-skills` is the other half of that idea. It is the home for skills that need nothing
beside them — no agent, no hook, no sibling skill — and that no topical plugin already owns,
so its membership is derived rather than curated: `scripts/check_solo_skills.py` re-reads the
skill bodies, their bundled scripts and their bundled examples, works out which ones qualify,
and reads the other assemblies to see which already have a home of their own.

**Per-skill *plugins* are no longer offered — per-skill installs are.** Each of those skills
used to ship as its own one-skill plugin. A plugin is the unit of installation in Claude Code,
so taking `solo-skills` means taking the set rather than picking from it, and progressive
disclosure is what makes that cheap: the model reads each skill's one-line description to
decide what to activate and only loads a body when it fires. When a subset is what you
actually want, `scripts/install_claude_skills.sh --only <id>[,<id>]` copies those skill
folders straight into `~/.claude/skills/` or a project's `.claude/skills/`, with no
marketplace in the loop.

`solo-skills` carries no dual-homed skill. A skill a topical plugin owns ships only from
that plugin (decision-020), and the eighteen that were still dual-homed at the ruling were
swept out of `solo-skills` on kata `8tw0` — enable the topical plugin to get one of those.
The reason is what a session does with two memberships of one source: each skill is one
source symlinked into every assembly that carries it, not a copy, so every bundle ships
identical bytes, but the harness lists that skill once per enabled plugin and neither
plugin can suppress the other.

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
