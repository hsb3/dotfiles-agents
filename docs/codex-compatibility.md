# Codex distribution and runtime contract

Validated against **codex-cli 0.153.4**, macOS arm64, on 2026-09-09. The supported
execution surface is a fresh CLI session with native project roles and trusted hooks.
The existing desktop conversation proved skill discovery only; its already-loaded tool
schema cannot establish native role or hook parity. Work is tracked under kata **64bm**.

## Distribution and setup

The existing `main` marketplace serves both harnesses. Shared primitives and thin symlink
assemblies remain the source; the publish workflow dereferences them. A bundle adds a small
`.codex-plugin/plugin.json` only when it needs a Codex-specific selector such as
`hooks/codex-hooks.json`; skills-only bundles do not duplicate their Claude manifest. OpenAI's
portable format now prefers a root `plugin.json` and treats `.codex-plugin/plugin.json` as a
compatibility overlay, so blank overlays would add drift without capability. Moving this
marketplace to portable root manifests is a separate packaging migration, not a parity fix.
Existing overlays must match the Claude manifest and catalog version. Omitting the native
version was tested: Codex caches it as `local`, so an overlay must carry the same release
version. There is no generated source tree or separate release ledger.

```sh
codex plugin marketplace add hsb3/dotfiles-agents
codex plugin add atelier@dotfiles-agents
```

Codex setup requires Python 3.11 or newer. Use the installed activation skill’s `create --harness codex`, `codex-setup`, then
`check --harness codex`. Policy placement follows configured agents: the sole native
directory, or `.agents` for multiple agents. Setup reconciles placement after creating
`.codex`; roles and native config remain there. Existing policies migrate without byte
changes; divergent copies are rejected before mutation. Repeated creation is a no-op.
`ATELIER_ACTIVATION_FILE` wins, including missing or malformed selected content.
See [activation selection](override-convention.md#atelier-activation-selection) for worktrees.
Setup renders five project role TOMLs from canonical agent Markdown and the OpenAI tier
map, plus the narrow writable roots needed for worker Git operations. It refuses conflicting
or edited user configuration. Restart the session and review/trust the package in `/hooks`.
Configuration checks deliberately do not certify trust from parsed settings.
For V1, the manager layer requires `agents.max_depth >= 2`; the default is one.
Setup checks this without replacing an existing user-owned agents table.
Before upgrading, finish or checkpoint affected parent and worker sessions in every process
sharing the same `CODEX_HOME`, then exit those sessions. Marketplace upgrades and plugin
reinstallation can remove the versioned files their loaded hooks still reference. Run the
update from an ordinary terminal after those sessions exit:

```sh
codex plugin marketplace upgrade dotfiles-agents
codex plugin add atelier@dotfiles-agents
```

Rerun setup against the installed package, then start a fresh session and inspect `/hooks`.
Rendered role instructions also contain versioned package paths. Defer updates while a live
session or worker still needs its installed version; an update in one process does not
refresh other running processes.

### Recovering a missing installed hook

If shell commands report a missing versioned `hook.py`, preserve the session IDs, worker
checkouts and pending command results before restarting. A command may have finished even
when its result could not be read. Restart the affected Codex process against the installed
version, then inspect the original result before deciding whether to rerun it.

For a temporary project-only disable, merge this table into the trusted project's
`.codex/config.toml` (edit an existing table instead of duplicating it):

```toml
[plugins."atelier@dotfiles-agents"]
enabled = false
```

This disables the whole Atelier plugin, including its guards and worker routing. Finish or
checkpoint isolated workers before the transition; retain their worktrees and resume work
from their actual checkout paths. Keep the temporary override out of commits. Start a fresh
Codex process in that project and verify `/hooks` contains no Atelier hooks. Editing the
project file alone does not prove an already-running session reloaded it. Leave the installed
cache intact so other projects can continue using it.

After repair, remove only the temporary override (restoring any prior value), rerun setup if
the installed package changed, and restart/review `/hooks` before relying on Atelier again.
Do not link an old version directory to a new release: that substitutes different code at a
previously loaded path. Recovery requiring the old path must restore the exact old bundle
and its dependencies from verified release material.

In Codex 0.153.4, this is an upstream cache-lifetime limitation. The
[plugin store](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/core-plugins/src/store.rs#L699)
removes older version directories during installation; already-loaded hook handlers retain
their versioned root. Python exits 2 when its script is missing, and the
[PreToolUse handler](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/hooks/src/events/pre_tool_use.rs#L261)
interprets that exit as a tool block. An Atelier handler cannot repair this before its own
entrypoint is found. The safe update order above is a mitigation, not a runtime fix.

Code-desk and PocketBase use the same role renderer with `--plugin-root` naming their
installed package. Their hooks inject canonical instructions and enforce declared dispatch
and patch-tool exclusions without requiring Atelier activation. They do not themselves
provide worktree isolation. Claude commands are convenience entry points: invoke `activation`
or `pull-request` directly in Codex instead of claiming native slash-command registration.

## Worker isolation

Native spawn `cwd` and `isolation` fields do not relocate a worker in this runtime. Native
SubagentStart instead registers its real worker ID and creates an owned Git worktree when
`isolate` selects that writer. PreToolUse routes supported shell commands and all patch
Add/Update/Delete/Move destinations into that checkout. `updatedInput` requires an explicit
`permissionDecision: allow`; any denying hook overrides all rewrites.

Two actual workers wrote different bytes to the same relative filename, staged different
indexes, and answered follow-ups on their original native IDs while the parent stayed clean.
Actual installed custody hooks refused both workers’ protected patch attempts. Registry
validation checks the worktree, common Git directory, administrative directory and index:
missing/replaced state cannot silently route a write to the parent. Enabling isolation during
an existing unisolated writer session requires redispatch. Existing mapped workers keep their
routing if activation is later removed.

Workers start from their immediate dispatcher’s committed HEAD. Native thread cwd metadata
remains inherited; the registry records the effective checkout. This provides collision
isolation between cooperating workers, **not a separate OS sandbox per worker**. The project
sandbox and role instructions still govern shell access. Required writable roots cover owned
checkouts, Git worktrees/objects, and only Atelier branch refs/reflogs for commits. Retain
worker branches until integration; no automatic cleanup discards unfinished work.

Tool names differ within the same CLI version: Luna uses `spawn_agent` with a plain brief;
Terra uses `collaborationspawn_agent` with an encrypted brief. The adapter preserves both
native paths without decrypting or rewriting those briefs. Because role developer text was
not delivered on one measured Terra path, SubagentStart injects the canonical role text too.

## Atelier member verdicts

Membership is derived from the assembly: eight skills, five agents, fourteen hooks and one
Claude command. `codex` roster targets describe supported runtime surfaces; commands retain
their original target. A mechanism test is evidence for that boundary, not proof of every
possible project workflow.

| Member | Codex implementation and evidence scope |
|---|---|
| `activation` | Project setup, collision refusal and currency checks; trust remains an explicit native step. |
| `delegation` | Native role selection, bounded waits and follow-ups; five roles generated from canonical source. |
| `waves` | Tracker-driven coordination with native worker identities and isolated writing. |
| `comment-hygiene` | Shared procedure, with native tool guidance and package-local references. |
| `deletion-pass` | Shared contract-preserving simplification procedure. |
| `layer-cycle` | Shared create/evaluate/refine procedure using native role dispatch. |
| `rubric-panel` | Shared independent-judge procedure using native role dispatch. |
| `handoff` | File/external target procedure; board body first, freshness stamp last. |
| `builder` | Native role, owned checkout, patch routing and native replies exercised. |
| `manager` | Actual native manager → builder commit → manager integration → reviewer chain, with distinct nested ownership and proof upward. |
| `scout` | Native role with canonical read/dispatch restrictions; no writer worktree. |
| `reviewer` | Native review role with canonical read/dispatch restrictions; no writer worktree. |
| `code-reviewer` | Native review role with canonical read/dispatch restrictions; no writer worktree. |
| `activate` | Invoke the activation skill; no native command registration claimed. |
| `worktree-isolation` | Actual installed collision isolation, distinct indexes, native follow-ups and clean parent. |
| `config-custody` | Actual installed protected patch denial; parser regressions cover every patch destination. |
| `worker-git-scope-guard` | Effective worker cwd and native command normalization; shared/protected Git refusal regressions. |
| `live-worker-git-guard` | Native registry replaces Claude sidecars; live-worker mutation refusal regressions. |
| `comment-hygiene-gate` | Reads the effective routed diff; existing advisory behavior preserved. |
| `worker-context` | Canonical role and owned-checkout context observed in actual installed worker input. |
| `subagent-telemetry` | Actual installed completion rows retain native worker identity and model usage. |
| `manager-package-gate` | Actual native malformed final → gate rejection → corrected proof package; permits one correction, never an endless loop. |
| `context-watermark` | Actual trusted nudge using rollout effective context limit and latest usage, not cumulative/cache double-counting. |
| `delegation-watermark` | Actual trusted nudge from authoritative PostToolUse events, including wrapped shell calls; native spawn resets the counter. |
| `branch-activity-surfacer` | Actual peer detection distinguishes sessions sharing one app-server PID. |
| `lane-snapshot` | Actual daemon snapshot captured worker bytes while preserving its index and parent checkout. |
| `session-handoff-surfacer` | Actual cold-session file and external handoff context. |
| `handoff-freshness-guard` | Actual trusted manual compaction denied missing/stale handoff and accepted fresh handoff. Native output uses `continue: false`; automatic-compaction behavior was not live-probed. |

The runtime contract’s synthetic collision probe passed all eight assertions for Luna and
Terra. Installed package tests additionally exercise production hook composition. The installed isolation probe passed 11 checks and the installed manager workflow passed
nine, including real child model/usage accounting. Unit tests
cover routing failure, hostile paths, modified Git identity, activation transitions, setup
ownership and native event contracts. Shared neutral doctrine landed in the sibling opencode
repository in the same wave; harness-specific execution details stay outside its transform.

## Other bundles and prerequisites

| Bundle | Verified behavior and limits |
|---|---|
| Bun | Installed skill and actual Bun test. |
| Carbon | Installed wrapper plus all five authenticated MCP read/audit tools; new-account OAuth onboarding not exercised. |
| Diagrams | Graphviz SVG/PNG, Excalidraw helper/render and persistent consumer-local memory. Python provider-icon library, draw.io export and Mermaid CLI rendering remain separate prerequisites/unverified paths. |
| mise-en-place | Installed audit, scaffold plan/apply/replan, synthetic tracker reconcile. No live tracker mutation needed for the proof. |
| Obsidian toolkit | Portable API/MCP/vault guidance; executable found, disposable-vault integration not exercised. |
| solo-skills | Portable subject/procedure documents; installed signoff builder plus actual local HTTP save. opencode-sandbox executable absent. Product-specific skills still configure their named product, including Claude Code memory/configuration. |
| code-desk | Installed rig-builder created a gate and proved green/red cases; independent artifact checks passed. Presentation rendering still needs its documented application dependencies. |
| PocketBase | Installed builder, reviewer and auditor each used a disposable PocketBase 0.40.3 backend to verify allowed reads, refused writes, unchanged source and cleanup. This is fixture coverage, not full backend assurance. |
| plugin-feedback | Actual installed parent and non-forked worker received distinct reminders; fixed-template local draft chose the installed-source repository. No external issue or message filed. |

Missing services are pending proof, not successful integrations. Skill discovery does not
certify backend behavior. Detailed per-member evidence and remaining prerequisites are on
kata `7d7v` and `kzw6`.

## Repeatable local checks

`make ci` remains offline and stdlib-only. Catalog validation rejects native version drift,
missing hook files and missing referenced handlers. Dereferenced-package tests render actual
assembled roles, including their shipped helper dependencies. Removing a required handler
makes the catalog check fail. Claude manifest validation runs against the same dereferenced
publish shape.

Authenticated checks are opt-in and use disposable consumer repositories and private auth
copies, never the user’s mutable auth file. They scope state to scratch storage and stop only
verified scratch-owned snapshot daemons. Evidence is sanitized before temporary credentials
and homes are removed.

```sh
python3 harness/codex_runtime_probe.py --auth-source ~/.codex/auth.json --output /tmp/codex-installed-proof --plugin-root plugins/atelier
python3 harness/codex_runtime_probe.py --auth-source ~/.codex/auth.json --output /tmp/codex-manager-proof --plugin-root plugins/atelier --production-workflow
python3 harness/codex_lifecycle_probe.py --auth-source ~/.codex/auth.json --output /tmp/codex-handoff-proof --package-root primitives-core
```

The runtime probe reviews only the package explicitly selected for the disposable run through
`--dangerously-bypass-hook-trust`. This automation flag neither changes persistent consumer
trust nor removes the requested sandbox. A passed check certifies its named observed effect. The manager stop diagnostic explicitly
injects one test-only malformed-final stimulus; it leaves the production gate unchanged
and requires an observed rejection followed by a corrected proof package. Add
`--marketplace hsb3/dotfiles-agents` to a runtime probe to install the published GitHub
package into a fresh consumer cache instead of copying the local assembly. Private GitHub
marketplaces require authenticated `gh`; the probe scopes its credential helper to GitHub
and does not import arbitrary global Git configuration.

Official references checked against the installed runtime: [plugin packaging](https://developers.openai.com/plugins/build/plugins),
[hooks](https://learn.chatgpt.com/docs/hooks), and [custom agents](https://learn.chatgpt.com/docs/agent-configuration/subagents).
The runtime observations above take precedence over an assumed translation of those interfaces.

The source review used official Codex commit `3d2ee51ca2d5db578f328aa75e20aa22c0197c9a`
(0.153.4). Native spawn [reapplies parent cwd and permissions after role configuration](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/core/src/tools/handlers/multi_agents_common.rs#L235).
The supported relocation seams are [shell command rewriting](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/core/src/tools/handlers/unified_exec/exec_command.rs#L508)
and [patch command rewriting](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/core/src/tools/handlers/apply_patch.rs#L468),
which the two-worker probe exercises. These are operation-level adapters; they do
not mutate the native thread's cwd metadata.
The [plugin manifest fields](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/plugin/src/manifest.rs#L19)
cover skills, MCP, apps and hooks; the [role loader](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/agent-roles/src/loader.rs#L23)
uses [TOML agent discovery](https://github.com/openai/codex/blob/3d2ee51ca2d5db578f328aa75e20aa22c0197c9a/codex-rs/agent-roles/src/discovery.rs#L27).
The existing plugin Markdown agents therefore require native role adaptation.
