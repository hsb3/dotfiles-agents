---
id: TASK-043
title: One plugin distributing every standalone-capable skill
status: To Do
assignee:
  - '@claude'
created_date: '2026-08-07 01:10'
updated_date: '2026-08-07 02:07'
labels:
  - assembly
milestone: m-1
dependencies: []
priority: medium
type: feature
ordinal: 22000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Owner instruction 2026-08-07, verbatim: 'create a plugin that distributes all skills that can stand on their own.'

Today the marketplace ships most standalone-eligible skills as their own one-skill plugin — the large majority of current entries are that shape. This asks for a single plugin that carries all of them instead of, or in addition to, that pattern.

BLOCKED ON A CLARIFICATION BEFORE ANY BUILD. The instruction arrived alongside a ruling that the lab-setup skill (TASK-29) should ship standalone, and the two readings imply very different work:

Reading A, additive — the existing one-skill plugins stay exactly as they are, and this new plugin is an aggregate convenience install for someone who wants everything without picking. Cost: every standalone skill is then dual-homed, so a consumer installing both the aggregate and an individual plugin needs the dual-homing behavior to hold (one primitives-core source symlinked into two assemblies loads the skill once).

Reading B, replacing — the aggregate becomes the distribution shape and the per-skill plugins are retired. Cost: a breaking marketplace change removing many entries, dangling every existing install record, with no alias or redirect mechanism in this marketplace's shape.

A is cheap and reversible. B is a marketplace restructure and, under AGENTS.md, a major information-architecture change needing the owner's approval before it is built. Settle the reading first.

Also to determine once the reading is fixed: what 'can stand on their own' means mechanically. check_symlinks now encodes a standalone rule (exactly one skill, no agents, no hooks), but that describes an ASSEMBLY, not a skill's self-sufficiency. A skill that references a sibling by path is not standalone-capable regardless of how it is packaged — claude-code-expertise's own authoring rules state exactly this. The membership test needs to be that property, not the current packaging.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 The owner has ruled between the additive and replacing readings, and the ruling is recorded before any file changes
- [ ] #2 'Standalone-capable' is defined as a checkable property of the skill (no sibling-skill references by path or wikilink), not as a description of its current packaging
- [ ] #3 A gate enforces that every skill in the new plugin meets that property, so membership cannot silently drift
- [ ] #4 If the additive reading wins, dual-homing is verified: installing both the aggregate and an individual plugin loads the skill once
- [ ] #5 make ci is green and the catalog guard's counts and names match the new lineup
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
ELIGIBILITY INVENTORY, first pass 2026-08-07 (a second pass is closing the gaps below).

CONFIRMED ELIGIBLE (15) — no hook/agent dependency, no sibling reference by path or wikilink:
handoff, github-project-board, opencode-expertise, pptx-themes, diagrams, drawio, excalidraw, obsidian-api-basics, obsidian-chat-ui, obsidian-cli, obsidian-mcp-server, owner-signoff, deep-research, tech-eval-research, dataviz.

Notes on those: diagrams needs cli:graphviz, drawio needs cli:drawio, obsidian-cli needs the Obsidian binary — external CLI dependencies, which the owner's test does not disqualify. deep-research and tech-eval-research do dispatch subagents, but generically through the harness's own Task tool rather than naming this repo's agents, so they pass. Several carry bundled scripts/, references/, assets/, base/ or examples/ directories that travel with them.

CONFIRMED NOT ELIGIBLE (1): board-triage, disqualified twice over — it references a sibling skill BY PATH at SKILL.md:31 ('S="${CLAUDE_PLUGIN_ROOT}/skills/github-project-board/scripts"'), and it names a 'board-analyst' agent at SKILL.md:68 that does not appear in the roster at all. The second is a defect in its own right, filed separately.

STRUCTURAL FINDING — the aggregate plugin will be a BUNDLE, so it hand-authors its README as a regular file. Every existing multi-skill bundle follows one shape: '# <id>' plus a one-paragraph pitch, a '## What you get' table of skill and what-it-does, an '## Install' block, and a '## Honest scope' section naming cross-skill boundaries and external dependencies. Follow it rather than inventing a shape.

HAZARD A — marketplace.json:4's metadata.description hardcodes '22 plugins: five bundles ... and seventeen standalone one-skill plugins' and then ENUMERATES all seventeen by name. Every count and every name in that sentence is falsified by this restructure, and check_catalog.py verifies those counts and names against reality, so it goes red until rewritten. The root README catalog was not checked in this pass — that half is still open.

HAZARD B, CONFIRMED — the check_symlinks standalone branch would go permanently dead. scripts/check_symlinks.py:90-97 defines standalone as exactly one skill with no agents and no hooks, and the README-symlink rule at :100-131 hangs off it. Of the plugins that would remain (atelier: 6 skills + 4 agents + 7 hooks; plugin-feedback: 0 skills + 2 hooks; code-desk: 10 skills), none satisfies that definition. If every current standalone retires, that lint can never fire again. It shipped 2026-08-07 under TASK-28, so this is a same-day interaction between two of the owner's decisions. Decide deliberately: retire the branch, or keep it with a stated reason (e.g. it guards against a future standalone being added wrongly).

GAPS this pass did NOT certify, being closed by a second pass: mermaid, project-memory, private-fork, readme-value-and-proof, repo-meta-structure, comms, claude-code-config, claude-code-expertise, iterm2, editor-project-config, mise-en-place-scaffold, planning-desk (never read); repo-compliance-audit and dev-focus (suspected not-eligible via code-desk's README calling them bundle-only, reason unconfirmed). The atelier skills (waves, rubric-panel, deletion-pass, layer-cycle, and the skill now renamed to delegation) are not eligible by inspection — they dispatch this repo's named agents, which is the disqualifying criterion.

INVENTORY COMPLETE 2026-08-07 (second pass closed every gap; all 14 remaining skills read and given a verdict).

ELIGIBLE — 27 total. First pass (15): handoff, github-project-board, opencode-expertise, pptx-themes, diagrams, drawio, excalidraw, obsidian-api-basics, obsidian-chat-ui, obsidian-cli, obsidian-mcp-server, owner-signoff, deep-research, tech-eval-research, dataviz. Second pass (12): mermaid, project-memory, private-fork, readme-value-and-proof, repo-meta-structure, comms, claude-code-config, claude-code-expertise, iterm2, editor-project-config, planning-desk, dev-focus.

NOT ELIGIBLE — three, each for a concrete cited reason, plus the atelier skills by inspection.
- board-triage: references a sibling skill by path (SKILL.md:31) AND names a nonexistent agent (SKILL.md:68). Filed separately as a bug.
- mise-en-place-scaffold: hard runtime dependency on sibling skills' CONTENT, not merely a mention. SKILL.md:49 requires the plugin root to contain skills/repo-meta-structure/ and skills/project-memory/, and scripts/scaffold.py:66-71 hardcodes those relative paths for its checklists and assets. The script cannot resolve its inputs without both siblings physically present.
- repo-compliance-audit: same shape, SKILL.md:29-32 — it needs a plugin root containing those same two siblings' checklist files at fixed relative paths. Its own script's docstring notes it duplicates reader functions kept in sync with scaffold.py, so the two share one dependency pattern.
- The atelier skills (waves, rubric-panel, deletion-pass, layer-cycle, delegation) dispatch this repo's named agents, which is the disqualifying criterion.

NOTE THE PATTERN in those three: none of them was caught by a roster 'requires:' field. Two express the dependency as a hardcoded relative path inside a bundled Python script. So eligibility cannot be decided from metadata — it needs the body and the scripts read. Any gate enforcing membership must check the same way.

PRE-BUNDLING CLEANUP: stray tracked __pycache__/*.pyc files exist under comms/scripts/, mise-en-place-scaffold/, and planning-desk/. The published .gitignore drops them at publish time, but they should not travel into a new assembly.

Bundled directories that travel with each eligible skill are recorded per-skill in the second pass report — several carry scripts/, references/, assets/, or examples/ trees, and planning-desk carries a scripts/_utils/ set of governance scripts.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @claude
created: 2026-08-07 01:39
---
Owner ruling 2026-08-07, verbatim: 'instead of single-skill plugins, create a plug-in that has all skills that can stand on their own (don't require hooks, agents, ...).'

This settles the card's blocking ambiguity: it is the REPLACING reading, not the additive one. The per-skill plugins are retired and one aggregate plugin carries every standalone-capable skill. 'Instead of' is unambiguous on that point.

It also answers the second open question — what 'can stand on their own' means. The owner's test is dependency-based: a skill qualifies when it needs no hooks and no agents to function. That is a property of the skill, not of how it happens to be packaged today, which is the distinction the card asked for.

Accepted cost, stated so it is not discovered later: removing a plugin's marketplace entry dangles every existing install record for it, and this marketplace has no alias or redirect mechanism, so the failure is silent on the consumer's next refresh — the plugin simply stops resolving with no message naming its successor. Migration is manual: uninstall the old id, install the aggregate.

Second-order effect to check during the build: TASK-028 just shipped a gate requiring a STANDALONE plugin (exactly one skill, no agents, no hooks) to symlink its README into the skill's own README. If every single-skill plugin is retired, that rule may have no subjects left and would become a gate that can never fire. Confirm whether any standalone assembly survives; if none does, the gate needs either a stated reason to remain or an honest retirement.
---

author: @claude
created: 2026-08-07 02:07
---
Set back to To Do 2026-08-07: the ANALYSIS is complete (see the two inventory notes above — 27 eligible skills, 3 not, both hazards confirmed) but the BUILD was not started. The session that did the analysis handed it off rather than starting a marketplace-wide restructure on exhausted context.

A session picking this up should not redo the inventory. What remains is the build itself, and the two hazards decide its shape: marketplace.json's metadata.description enumerates all seventeen standalone plugins by name and the catalog guard verifies those names, so it goes red until rewritten; and the check_symlinks standalone branch loses every subject, so it must be retired or explicitly justified.

One thing learned during the inventory that changes how the membership gate must work: eligibility cannot be read from metadata. None of the three ineligible skills was caught by the roster's requires: field — two express the dependency as a hardcoded relative path inside a bundled Python script (mise-en-place-scaffold/scripts/scaffold.py:66-71 and repo-compliance-audit). A gate enforcing membership has to read bodies and scripts.
---
<!-- COMMENTS:END -->
