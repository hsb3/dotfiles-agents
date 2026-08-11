---
id: TASK-065
title: 'kaneo: ship the MCP-token mint script inside the skill'
status: Done
assignee:
  - '@claude'
created_date: '2026-08-11 15:22'
updated_date: '2026-08-11 15:29'
labels:
  - primitives
milestone: m-1
dependencies: []
priority: high
type: bug
ordinal: 44000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The kaneo plugin's hooks hard-require five KANEO_* env vars and block every board write until they are set, but the plugin ships nothing that produces them. SKILL.md tells the agent to run `scripts/mint-mcp-token.sh` — a relative path that resolves to nothing in any repo that installed the plugin — and references/configuration.md attributes both credentials to an unnamed 'instance ops repo'. A session that installs kaneo from the marketplace therefore cannot complete first-run setup: preflight blocks, the skill forbids guessing, and no runnable path exists.

Observed 2026-08-11 in this repo while attempting to adopt a Kaneo board. Filed as issue #308.

mint-mcp-token.sh (in the private ops checkout) is already fully portable: its only inputs are the base-URL argument and $MINT_KEY, with no .env, config.json, or railway dependency. mint-agent.sh is genuinely instance-ops (owner API key from .env, workspaceId from config.json, Railway roster push) and must not ship — but the docs must say so and state what the consuming repo needs the owner to hand over, instead of naming a script it cannot run.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 primitives-core/skills/kaneo/scripts/mint-mcp-token.sh exists, is executable, and depends on nothing outside its arguments and $MINT_KEY
- [x] #2 SKILL.md's config section points at the skill-local script path rather than an unnamed ops repo
- [x] #3 references/configuration.md states which credential the owner must mint out of band (the agent key) and why that step cannot ship
- [x] #4 make ci passes, including the symlink and roster guards
<!-- AC:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. Copy mint-mcp-token.sh from the ops checkout into primitives-core/skills/kaneo/scripts/, unchanged in behavior; retarget its own docstring at the skill-local path and drop the ops-repo-relative invocation.
2. Rewrite SKILL.md's Config section: point at the skill-local script, name the agent key as the one thing the owner supplies out of band.
3. Rewrite references/configuration.md's provenance table + add a section on what the owner mints and why agent creation cannot ship.
4. Note the script in the skill README's 'what to read next'.
5. Bump plugins/kaneo/.claude-plugin/plugin.json to 0.4.2; make ci.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Shipped primitives-core/skills/kaneo/scripts/mint-mcp-token.sh (executable lines byte-identical to the ops-repo original; shebang zsh -> bash to match the repo's other skill script, header retargeted at the skill-local path). SKILL.md, references/configuration.md, and README.md rewritten to split owner-supplied credentials from self-minted ones and to state why agent-account creation cannot ship. Version 0.4.1 -> 0.4.2.

Verification: make ci exits 0 (519 tests; roster/symlink/catalog/identity guards clean). PR #310 green on both CI checks. End-to-end live mint run from the new location under bash against the production instance: all 4 steps succeeded, exit 0, returned a 36-char token. Token proven valid by contrast against the MCP endpoint — minted token returns 400 'Server not initialized' (authenticated, awaiting handshake) while a bogus token returns 401. Minted credential deleted from scratchpad after testing.

Note: that run created one additional 30-day better-auth session row for agent-kaneo-a on the live instance. Harmless and self-expiring; it does not affect the existing KANEO_MCP_TOKEN.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Shipped the MCP-token mint script inside the kaneo skill and rewrote the config docs to name the owner's one hand-off (the agent key) instead of pointing at an unshipped script in an unnamed repo. Verified with make ci (exit 0) and a live end-to-end mint against the production instance, with the minted token proven to authenticate (400 vs 401 against a bogus control).
<!-- SECTION:FINAL_SUMMARY:END -->
