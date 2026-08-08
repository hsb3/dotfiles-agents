---
id: DRAFT-006
title: >-
  atelier (oc): documentation that scales with the bundle, and distinguishes it
  from the CC mirror
status: Draft
assignee: []
created_date: '2026-08-08 15:59'
labels:
  - assembly
dependencies: []
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/290'
  - /Users/henry/Developer/AGENT-PLUGINS-WORKBENCH/plugin-oc-atelier/README.md
type: docs
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
`plugin-oc-atelier` has outgrown its README. It now ships 7 hooks, 7 self-registering agents, 6 skills, a tiered permission posture, a symlinked install, and (as of 2026-08-08) a log-identity scheme with a versioned record schema. Load-bearing knowledge currently lives in HANDOFF.md — a session-boundary document that is rewritten every session and is explicitly not the place for durable reference material.

Two forcing functions:

1. Complexity. Several facts are now traps rather than details: the plugin self-installs its own roster via the `config` hook, so copying `agents/*.md` into `~/.config/opencode/agents/` registers every prompt twice; `tools:` frontmatter is silently DEAD for hook-registered agents (only `permission:` works); permission rule precedence is last-match-wins, so a wildcard deny must come first but must not come last. Undocumented, each of these costs a future session a debugging round.

2. The workbench repo rule. AGENTS.md: "sometimes we have more than one way to do the same thing. when that happens, we make extra effort in our repo-level documentation to distinguish these items." The CC atelier and the opencode atelier are exactly that case, and the docs currently do not distinguish them. The port header even claims 1:1 fidelity while the two diverge on log location, timestamp format, and whether worktree-isolation logs at all.

Scope is the docs surface only — README plus whatever reference pages earn their place. No behavior change. The test of success is that HANDOFF.md gets SHORTER, because durable content moved to where it belongs.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 All 7 hooks documented: trigger event, effect, whether it can block, and which log stream it writes
- [ ] #2 The self-registration model is documented, including the 'never copy agents/*.md' trap and why
- [ ] #3 Permission posture documented per tier, with the owner's 'the level above decides for the level below' rationale
- [ ] #4 Log identity documented: root shape, all 6 envelope fields, schema version, and the 7 env overrides
- [ ] #5 The two known config traps are written down: dead 'tools:' frontmatter, and last-match-wins rule precedence
- [ ] #6 opencode-vs-Claude-Code differences called out explicitly, per the AGENTS.md distinguish rule
- [ ] #7 Every path, env var name and model id in the docs is verified against code by a gate check, not by eye
- [ ] #8 HANDOFF.md is net shorter: durable reference moved out, session state left in
<!-- AC:END -->
