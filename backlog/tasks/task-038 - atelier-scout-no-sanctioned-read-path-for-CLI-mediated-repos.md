---
id: TASK-038
title: 'atelier scout: no sanctioned read path for CLI-mediated repos'
status: Done
assignee: []
created_date: '2026-08-06 23:49'
updated_date: '2026-08-07 01:27'
labels:
  - primitives
milestone: m-2
dependencies: []
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/255'
priority: medium
type: feature
ordinal: 16000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
GH issue #255: scout's hard read-only guarantee (Read/Grep/Glob, no Bash) collides with repos whose project law routes all task reads through a CLI -- e.g. this repo's own Backlog.md CRITICAL_INSTRUCTION ('do not edit Backlog task files directly, use the backlog CLI'), whose read guides assume 'backlog task view TASK-123 --plain'. The workaround used (Glob the raw markdown, Read it directly) worked but bypasses the sanctioned read path and can silently diverge from the CLI-rendered view -- e.g. computed fields and config-stamped Definition-of-Done defaults are invisible in raw frontmatter, so a scout reading raw files will wrongly report 'no DoD on this task'. Checked #260: no diff to agents/scout.md at all, so this is still open.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Either: scout gains an opt-in dispatch knob for a documented, explicitly allowlisted read-only CLI command set (Bash stays off by default), or: the foreman skill documents a pattern for CLI-mediated repos (paste CLI output into the brief vs. point scout at raw files with the specific caveat about computed/config-stamped fields)
- [x] #2 The chosen approach is written into the foreman skill's own docs so a future foreman does not have to re-derive it per brief
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Resolved by owner ruling 2026-08-07 ('scout needs to be modified. it's both overspecified and restricted. the 15 turn limit is a footgun. please rewrite.'), which settled the card's either/or and added two complaints the card had not raised.

THE TURN CAP, which the card never mentioned: scout.md carried maxTurns: 15. TASK-24 had already removed the identical cap from the builder agent for causing silent mid-work stalls; scout kept its copy. Live corroboration from the session that found it: four scouts were dispatched with briefs explicitly budgeting 25-35 tool calls, written by a session unaware the agent config would cut them off earlier. A bound the dispatcher cannot see and does not control is exactly that failure mode. Removed; bounds now come from the brief.

THE READ PATH: tools is now Read, Grep, Glob, Bash. A brief may grant a named read-only command set; the default posture with no grant is no shell. The tradeoff is recorded honestly rather than glossed — scout's no-shell property moves from structural to prompt-enforced, because this harness has no per-dispatch tool-grant knob. That was verified in three places before changing the tools list: the foreman's dispatch-knobs reference enumerates the per-invocation knobs (model, isolation, maxTurns, SendMessage) with no tools override; evals/ingest.py classifies (agent, tools) as frontmatter-level, not a dispatch parameter; and the claude-code-expertise reference documents tools as a flat list, with scoped specifiers like Bash(git diff:*) appearing only in the permissions system and slash-command allowed-tools, never in agent frontmatter.

What stays structural: Edit, Write, and NotebookEdit remain absent, so 'cannot write a file' is still enforced by the tool list rather than by prose. The install-time opencode transform still emits write: deny for scout; only bash flips to allow.

The prompt carries the rest and outranks the brief by construction: 'No brief can license a mutation — a brief that asks for one is a mis-dispatch: refuse that part and say so in your report.' The TASK-038 situation itself is described generically, without naming any project, so the identity gate stays green: when a repo routes reads through a CLI on purpose and the file on disk omits computed values, a scout holding no grant names the sanctioned read path it lacked rather than passing a partial answer off as fact.

Overspecification cut: the dispatcher-facing 'when to invoke' taxonomy (duplicated in the description frontmatter, the agents README, and the foreman cheat-sheet), a ~300-word report budget that was itself an unguarded count in a shipped body, and a per-sentence observed/inferred tagging ritual. Retained material went 48 lines to 31; the read-only guarantee and the path:line evidence requirement were not touched.

AC#2 satisfied by correcting the foreman's own dispatch-knobs reference, which had asserted both now-false properties — that only scout keeps a 15-turn backstop, and that scout is 'deliberately Bash-less, which is what makes its read-only guarantee structural rather than promised'. It now distinguishes the structural half from the prompt-enforced half so a dispatcher can make the safety call. A dependent passage was also found and fixed: 'read-only git is allowed to every shell-bearing agent' would have swept scout into having it by default.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
scout rewritten on the owner's direction. The hidden 15-turn cap is gone — it was the same footgun TASK-24 removed from builder, and it silently truncated scouts this session whose briefs budgeted more. Bounds now come from the brief, which the dispatcher can see. The CLI read-path collision is resolved by letting a brief grant a named read-only command set, default no-shell; write tools stay absent so the cannot-write half of the guarantee remains structural while shell authority is prompt-enforced. That tradeoff is stated plainly in the agent body and in the foreman's dispatch docs rather than left for a dispatcher to discover.
<!-- SECTION:FINAL_SUMMARY:END -->
