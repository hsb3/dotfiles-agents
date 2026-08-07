---
id: TASK-043
title: One plugin distributing every standalone-capable skill
status: Done
assignee:
  - '@claude'
created_date: '2026-08-07 01:10'
updated_date: '2026-08-07 03:37'
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
- [x] #1 The owner has ruled between the additive and replacing readings, and the ruling is recorded before any file changes
- [x] #2 'Standalone-capable' is defined as a checkable property of the skill (no sibling-skill references by path or wikilink), not as a description of its current packaging
- [x] #3 A gate enforces that every skill in the new plugin meets that property, so membership cannot silently drift
- [ ] #4 If the additive reading wins, dual-homing is verified: installing both the aggregate and an individual plugin loads the skill once
- [x] #5 make ci is green and the catalog guard's counts and names match the new lineup
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

author: @claude
created: 2026-08-07 03:25
---
Owner ruling 2026-08-07 (session 10), recorded before any file changes per AC#1.

CORRECTION MADE AND ACCEPTED FIRST. The owner's framing was 'get rid of any single skill plugin and package a new plug-in that allows each skill to be individually installed', with an explicit invitation to correct it. It was corrected: a plugin is the unit of installation, so no single plugin can offer per-skill installs, and a marketplace does not change that because a marketplace's granularity is also the plugin. The seventeen one-skill plugins ARE the per-skill install mechanism; retiring them is precisely what removes it. The mitigating fact that made the trade acceptable: skills are progressively disclosed, so installing all 27 costs 27 one-line descriptions in context, not 27 skill bodies.

RULED, with that understood: ONE aggregate plugin, the seventeen one-skill plugins retire, per-skill installation is knowingly given up.

- Plugin id: solo-skills. Permanent in effect — install records key on it and there is no alias mechanism.
- Bundles stay exactly as they are. Owner's reason, verbatim: 'they are packs of things that work together.' So diagrams, obsidian-toolkit, atelier, code-desk, and plugin-feedback are untouched, and the 11 eligible skills living inside them are dual-homed into solo-skills rather than moved.
- solo-skills carries all 27 eligible skills, not just the 16 backed by a retiring standalone.
- check_symlinks' standalone branch: KEEP, with a stated reason in the module docstring (a forward guard for a shape no plugin currently has).

Resulting lineup: 6 marketplace entries (solo-skills + the five bundles), down from 22.

FINDING that changes one detail of the plan — mise-en-place-scaffold is the seventeenth standalone and is NOT eligible, so it has nowhere to go in solo-skills. It survives inside code-desk, which carries its two required siblings. Retiring its standalone entry is therefore not a loss: that plugin is ALREADY BROKEN in the published marketplace. Proven by running its own script against its own plugin root — 'scaffold error: checklist file missing: .../plugins/mise-en-place-scaffold/skills/repo-meta-structure/references/checklist.md — broken plugin install; refusing to scaffold against a partial checklist'. It fails loudly and can never have worked as a standalone install. This restructure removes the broken entry as a side effect.

CORRECTION to the card's Hazard B as previously written: check_symlinks' standalone branch is exercised entirely by synthetic fixtures in tests/test_check_symlinks.py, which build their own alpha/beta plugin dirs in tempdirs. It therefore stays green with zero real subjects, and the test suite will not force the retire-or-keep decision either way. That is why the decision had to be made deliberately rather than discovered by a red gate.
---

author: @claude
created: 2026-08-07 03:36
---
BUILT 2026-08-07 (session 10). PR #276 into dev. make ci exit 0, 391 tests (16 new), version-bump gate clean by hand.

AC#4 is left UNCHECKED deliberately, not overlooked. Its condition — 'if the additive reading wins' — did not occur; the replacing reading won. Dual-homing is nonetheless in play, since 11 of the 30 members also ship inside a bundle, and it rests on the standing mechanism (one primitives-core source symlinked into two assemblies, ADR 0017) rather than on anything verified fresh here. What WAS verified is structural: check_symlinks confirms all 67 links resolve in-repo and that assemblies and marketplace entries match 1:1. The runtime claim that installing both homes loads the skill once was NOT re-tested live in this session. Flagging rather than checking, because the difference between 'the mechanism is established' and 'I proved it again today' is exactly what an unchecked box should preserve.

MEMBERSHIP IS 30, NOT THE 27 ON THIS CARD. The gate derives it, and derivation disagreed with the recorded inventory in three places. Recording them because the inventory note above is now partly wrong and a later reader will otherwise trust it:
- deletion-pass, layer-cycle, rubric-panel: the card excluded all five atelier skills as a group, 'by inspection', for dispatching this repo's named agents. True of delegation and waves; FALSE of the other three, which dispatch generic briefs and judges — the same basis on which the card itself ruled deep-research eligible. An unverified group generalization, and the reason the gate had to derive rather than consume the list.
- opencode-expertise: eligible, but it trips the agent rule on 'scout', which is opencode's OWN built-in subagent listed beside build/plan/general/explore. Handled as a documented exemption keyed (skill, agent) with its reason, not by weakening the rule for all 35 skills. The exemption list is itself checked: one that stops suppressing anything is reported stale.
- repo-meta-structure: had a genuine sibling path (references/layout.md pointing into skills/mise-en-place-scaffold/). It was a doc pointer rather than a runtime need, and it DANGLED in the standalone plugin shipping today. Fixed at the source by naming the skill without the path, which makes the content true in both of its homes.

SECOND LIVE DEFECT REMOVED. mise-en-place-scaffold's standalone plugin has never worked. Proven, not inferred: running its own scaffold.py against its own plugin root gives 'scaffold error: checklist file missing ... broken plugin install; refusing to scaffold against a partial checklist'. Its plugin root carries only its own skill, never the two siblings whose checklists it resolves. It is not eligible for solo-skills and keeps working inside code-desk, so retiring the entry is a straight repair.

GATE DESIGN, since AC#3 turns on it. Three rules, each applied where that class of dependency actually appears: sibling path or wikilink in prose (SKILL.md + references/); sibling id anywhere in bundled code (scripts/); roster-agent id in backticks, bare or namespaced. The split matters — a prose mention of another skill is a cross-reference, but an id inside a script is a dependency, and scaffold.py proves the point by composing its path with os.path.join so that no substring search for 'skills/<id>' would ever find it. The gate runs BOTH directions: an ineligible member is red, and so is an eligible non-member, so the plugin's claim to carry every standalone-capable skill cannot quietly rot. Rides the existing symlinks target so no new CI check name is pinned.

The two load-bearing tests were mutation-tested rather than assumed: disabling the bundled-code rule, and disabling the absent-from-solo-skills direction, each turned exactly one test red.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Shipped as PR #276 (squash-merged into dev as d54c5fd). The seventeen single-skill plugins are retired into one aggregate, solo-skills, carrying the 30 skills that stand on their own; the marketplace goes from 22 entries to 6, with the five bundles untouched.

The owner's framing was corrected before anything was built. 'A plug-in that allows each skill to be individually installed' is not buildable: a plugin is the unit of installation and a marketplace's granularity is also the plugin, so the seventeen one-skill plugins WERE the per-skill install mechanism and retiring them is what removes it. The owner confirmed the trade with that understood. Progressive disclosure is what makes it cheap — carrying the set costs a set of one-line descriptions, not a set of skill bodies — and both READMEs say so rather than implying a granularity that no longer exists.

Membership is derived by scripts/check_solo_skills.py rather than curated, because eligibility cannot be read from metadata: no ineligible skill is caught by the roster's requires: field, and two compose their sibling paths with os.path.join so no substring search finds them. The gate runs both directions, so neither an ineligible member nor an eligible non-member can pass. Deriving it disagreed with this card's own recorded inventory in three places, all corrected on the card.

Two live defects removed as a side effect: mise-en-place-scaffold's standalone plugin, which never worked and was proven broken by running its own script against its own plugin root, and a repo-meta-structure doc path that dangled in the standalone shipping today.

AC#4 is intentionally unchecked — its 'if the additive reading wins' condition never occurred, and while dual-homing is in play for 11 members, the runtime claim was not re-verified live this session.

NOT YET PUBLISHED. This is breaking for consumers: seventeen install records dangle with no alias or redirect, and the failure is silent on the next refresh. Publishing to main is a separate, owner-gated step.
<!-- SECTION:FINAL_SUMMARY:END -->
