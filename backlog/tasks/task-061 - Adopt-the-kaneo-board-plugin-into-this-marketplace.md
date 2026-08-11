---
id: TASK-061
title: Adopt the kaneo board plugin into this marketplace
status: In Progress
assignee: []
created_date: '2026-08-11 08:20'
updated_date: '2026-08-11 08:36'
labels:
  - assembly
milestone: m-1
dependencies: []
priority: high
type: task
ordinal: 40000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The kaneo plugin (Kaneo board workflow: skill + L2 manager agent + level-policy hooks + MCP config) currently lives in hsb3/kaneo-ops at plugins/kaneo and ships from that repo's directory marketplace. This repo takes over its care and maintenance: the source moves into primitives-core/ and it ships as a seventh plugin assembly from .claude-plugin/marketplace.json.

Why it matters: kaneo-ops is an instance ops repo, not a plugin marketplace, so the plugin gets none of this repo's gates - no identity-neutrality lint, no roster provenance, no symlink assembly check, no README diagram standard, no version-bump gate. Moving it puts it under the same floor as every other shipped plugin.

It also closes a live packaging defect. The plugin README claims 'a plugin-shipped MCP server config' and references/api.md says the plugin's .mcp.json wires that up, but .mcp.json sits at the kaneo-ops REPO ROOT, not inside plugins/kaneo/. Any consuming repo other than kaneo-ops itself installs the plugin and gets no MCP server at all, silently. Shipping it as the roster's first mcp-type primitive is the fix.

Known collisions with this repo's rules, all cheap:
- Hooks are two bash scripts under hooks/scripts/ with a shared hooks/hooks.json; the ratified layout is one dir per hook with a stdlib-Python hook.py. Port both.
- hooks/scripts/test-policy.sh is a bash assert script; tests here are stdlib python3 -m unittest under tests/. Port it.
- The plugin README's install line names the owner handle and the ops repo slug, which trips scripts/check_identity.py (.claude-plugin/ metadata is the sanctioned identity surface, bundle README prose is not).
- examples/kaneo.local.md carries a live Railway host and a real project id; those must become placeholders before shipping to consumers.
- plugins/<id>/docs/ is not a shape this repo has - docs/access-model.md folds into the skill's references/.
- The roster's mcp type has zero instances today; kaneo is the first, so check_roster.py / gen_opencode.py / check_symlinks.py handling of it is unexercised.

Source of truth for what moves: the kaneo-ops checkout at plugins/kaneo (11 files) plus that repo's root .mcp.json.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 primitives-core/ holds the kaneo skill, the kaneo-manager agent, both policy hooks, and the MCP server config, each with a roster entry in primitives-core.yaml (origin: authored)
- [ ] #2 The MCP server config ships INSIDE the plugin - installing kaneo into a repo that is not kaneo-ops registers the kaneo MCP server with no hand-authored .mcp.json in that repo
- [ ] #3 Both hooks are stdlib-Python hook dirs matching the ratified hooks/<name>/hook.py layout, and their behaviour is covered by a stdlib unittest file under tests/ that fails if the floor-deny or the stamping regresses
- [ ] #4 plugins/kaneo/ is a hand-authored symlink assembly with a bundle README carrying a Mermaid diagram under How it fits together; make symlinks and make check pass
- [ ] #5 make ci exits 0, and scripts/check_identity.py reports no violation from any kaneo file
- [ ] #6 No live instance host, project id, or agent identifier appears in any shipped kaneo artifact - all instance values are placeholders or KANEO_* env references
- [ ] #7 The seventh marketplace entry exists in .claude-plugin/marketplace.json and flow.yaml homes every new top-level path
- [ ] #8 kaneo-ops no longer ships the plugin from its own marketplace, or its README states plainly that the plugin is now maintained here
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Branch feat/kaneo-plugin off dev.
2. primitives-core/skills/kaneo/ — SKILL.md, references/api.md, references/access-model.md (from the plugin's docs/), references/configuration.md (from examples/kaneo.local.md, instance values de-identified), plus the required per-primitive README.md.
3. primitives-core/agents/kaneo-manager.md — moved as-is.
4. primitives-core/hooks/kaneo-mcp-policy/ and primitives-core/hooks/kaneo-bash-tripwire/ — each hook.py + config.json + README.md. The port is mechanical: both bash wrappers only exec a python heredoc over fd 3, so the Python body lifts out unchanged and the shell disappears.
5. primitives-core/mcp/kaneo.json — the connection spec lifted from the kaneo-ops repo root .mcp.json. First mcp-type primitive; check_roster already discovers primitives-core/mcp/*.json.
6. plugins/kaneo/ assembly — hand-authored .claude-plugin/plugin.json, hooks/hooks.json, README.md with the Mermaid diagram; symlinks for skills/kaneo, agents/kaneo-manager.md, both hook dirs, and .mcp.json.
7. Five roster rows in primitives-core.yaml, origin: authored, with requires: declaring hosted-mcp + the KANEO_* env words.
8. Root .claude-plugin/marketplace.json — seventh entry plus the metadata description and version.
9. tests/test_kaneo_policy.py — stdlib unittest port of hooks/scripts/test-policy.sh (13 assertions: floor-deny, L2 pass-through, stamping, stamp idempotence, root attribution, tripwire host/env-name/unrelated/main-session/env-unset).
10. make ci, then check_version_bump.py by hand (CI-only, needs network).
11. Drop the plugin from kaneo-ops: leave that repo uncommitted per the never-mutate-a-second-repo rule, and report what it needs.

Deliberately NOT in scope: publishing to main, and the two follow-on skills (TASK-062, TASK-063).
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Migrated on branch feat/kaneo-plugin; PR #304 into dev, both required checks green. Merge blocked by the session's permission classifier, so the PR is open and waiting.

What landed: 5 primitives (skill, agent, 2 hooks, 1 mcp - the roster's first), the plugins/kaneo/ symlink assembly, the seventh marketplace entry, a root README catalog row, and tests/test_kaneo_policy.py (17 tests; suite 484 -> 501).

Verified rather than assumed:
- Probed the harness binary before writing plugin.json: a plugin's own root .mcp.json IS merged at load, and a STRING mcpServers in the manifest means a path to an MCPB file, not a config. The manifest key is deliberately absent; the symlinked .mcp.json is the whole mechanism.
- Mutation-tested the policy hook, because 17 green tests prove nothing on their own. Disabling the subagent floor deny -> 4 failures; removing stamp idempotence -> 1; dropping the mcp__plugin_kaneo_kaneo__ prefix -> 4. All three regressions are silent in production.
- Dereferenced the assembly with cp -RL and ran claude plugin validate --strict: 16 files, all resolve, validation passed. Note this only confirms the manifest and that no symlink is broken - per the known gotcha it does not descend into agent or skill bodies.
- Read the generated opencode lane directly instead of trusting the gate: all five kaneo primitives appear as explicit reasoned exclusions, not silent skips.

Two things caught by inspection that no gate would have caught:
- The kaneo skill initially targeted opencode. Its contract is the MCP tools plus the two hooks, none of which reach that lane, so an opencode session would have loaded a skill telling it to call tools that do not exist and to trust stamping that never happens. Now claude-code only, with the reason in the roster.
- gen_opencode.py's fragment comment claimed no mcp entry was rostered. Corrected; the underlying render-branch hole is TASK-064.

NOT verified: no live install probe. Installing into a throwaway project would mutate the machine's marketplace registration and other projects' enabledPlugins, which the handoff documents as having wiped seven entries in one go elsewhere. The load mechanism is confirmed from the binary and the dereferenced tree, but nobody has watched this plugin register its MCP server in a real session.

Follow-ups filed: TASK-062 (brownfield adoption skill), TASK-063 (provisioning skill), TASK-064 (three gate gaps the first mcp primitive exposed).
<!-- SECTION:NOTES:END -->
