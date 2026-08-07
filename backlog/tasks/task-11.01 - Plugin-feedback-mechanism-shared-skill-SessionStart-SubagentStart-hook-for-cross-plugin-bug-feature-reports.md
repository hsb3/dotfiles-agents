---
id: TASK-11.01
title: 'Plugin-feedback hooks: standalone plugin for cross-plugin bug/feature reports'
status: Done
assignee: []
created_date: '2026-08-07 00:19'
updated_date: '2026-08-07 01:29'
labels:
  - distribution
dependencies: []
references:
  - primitives-core/hooks/worker-context/hook.py
  - primitives-core/hooks/session-handoff-surfacer/hook.py
  - 'https://github.com/hsb3/dotfiles-agents/issues/254'
  - 'https://github.com/hsb3/dotfiles-agents/issues/255'
  - 'https://github.com/hsb3/dotfiles-agents/issues/256'
parent_task_id: TASK-11
priority: medium
type: feature
ordinal: 19000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Elaborates TASK-11 AC#3 ('feedback pointer ships in all distributed skills') from a static doc pointer into an active mechanism. Motivating prior art: issues #254/#255/#256 are already exactly this pattern -- a worker mid-task noticing a defect and filing a 'Field observation (plugin, version, project, date): symptom -> workaround -> suggestion' issue -- done ad hoc, once each. The goal is to make that shape explicit and reusable across every plugin instead of relying on each session reinventing it, and to surface it via a hook's injected context instead of a CLAUDE.md reminder (which a session can forget to read, and which a plugin cannot ship into a consumer's CLAUDE.md at all).

No separate skill -- the hook injects the instructions directly, the same way worker-context's covenant text works today (inline, not a pointer to something else to go read). Design:
- Two hooks: SessionStart reminds the primary/foreman-level session it may file a bug or feature request; SubagentStart reminds dispatched workers they may file a bug directly but should draft (not file) a feature request for their dispatcher to review. Both inject via {"hookSpecificOutput": {"hookEventName": "<event>", "additionalContext": "..."}} -- confirmed against this repo's own working precedent, primitives-core/hooks/worker-context/hook.py and primitives-core/hooks/session-handoff-surfacer/hook.py.
- A companion stdlib script does the actual filing: wraps 'gh issue create --repo hsb3/dotfiles-agents' with the template (plugin name+version, consuming project, date, symptom+repro, severity/contract-violation check, workaround, optional suggested fix) and the right type: label pre-filled, so an agent doesn't free-hand the gh invocation and risk a malformed title/body/label. The injected hook text is a short pointer to this script, not the full instructions inline. Filing is low-friction because the owner's standing GH-issues grant already covers agent-created issues.
- Bug vs. feature gating: any dispatched worker can file a bug directly -- the bar is 'observed behavior contradicts the plugin's own stated contract,' checkable without judgment. A feature request needs a why tied to an actual limitation, not 'wouldn't it be nice' -- so a dispatched worker drafts a feature-request body for its dispatcher to review and file, rather than filing one directly; the primary/foreman-level session can file either.

PLACEMENT DECIDED: standalone plugin (plugin-feedback@dotfiles-agents, or similar name), NOT dual-homed into every other plugin. Verified against official docs (code.claude.com/docs/en/hooks, 'Hook handler fields'): 'If you define the same handler in more than one settings file, it runs once. A plugin's or skill's copy of the same handler stays separate.' Dedup is scoped to settings-file layers only, never across plugins -- dual-homing this hook into every plugin would mean it fires once PER dotfiles-agents plugin a consumer has installed (e.g. 3 times per session start with 3 plugins installed), turning a cheap nudge into noise. A standalone plugin means one clean install, fires exactly once regardless of how many other dotfiles-agents plugins are also installed. Tradeoff accepted: a consumer has to actively install this plugin alongside whatever else they use; it does not come bundled for free. Consider naming/describing it so it reads as a natural companion install alongside atelier and friends, to raise the odds someone actually adds it.

Sequencing note: this is a new plugin, not an addition to every existing plugin, so it does NOT trigger TASK-032's version-bump gap the way dual-homing would have -- no cross-plugin sequencing dependency after all.

Caveat: the bug-vs-feature tier split above is this session's interpretation of the owner's 'level 1 or 2 agent' framing, not confirmed doctrine -- check with the owner if the exact tier mapping matters before hardening it into shipped hook text.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 A new standalone plugin exists (own plugin.json, own catalog row) containing only the two reminder hooks and the reporting script -- not dual-homed into any existing plugin
- [x] #2 A companion script produces a consistently-shaped GH issue (plugin+version, project, symptom/repro, severity, workaround, optional fix) via one command rather than agents free-handing gh issue create
- [x] #3 A SessionStart hook reminds the primary session it may file bugs or feature requests via the script; a SubagentStart hook reminds dispatched workers they may file bugs directly but should draft (not file) feature requests for their dispatcher
- [x] #4 Both hooks fail open and add zero third-party dependencies, matching this repo's existing hook conventions
- [x] #5 TASK-11 AC#3 is satisfied by this mechanism once shipped
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Shipped as plugins/plugin-feedback (v0.1.0): two hooks symlinked from primitives-core, plugin.json and hooks.json as regular files per ADR 0017, a marketplace row, a README catalog row, and two roster entries. 51 tests. Captured red in two stages — ModuleNotFoundError with no reporter, then 25 failures with the reporter present and both hooks absent.

Adversarially reviewed before merge, which was worth it: the review REFUTED one claim and found a consumer-facing defect.

DEFECT FOUND AND FIXED: both hooks offered to report a defect in 'any installed plugin', but resolve_repo reads the REPORTING plugin's manifest, not the reported one's. Executed proof: a bug about an unrelated third-party plugin resolved to this repo. So a consumer installing this and reporting someone else's plugin would file into this tracker silently. It was a missing specification, not a coding slip — nothing had ever decided whether the target is 'the marketplace this reporter shipped from' or 'the repo of the plugin being reported'. Decided as the former, hook text narrowed to say so, and the resolved target plus its provenance (env var vs manifest) is now printed BEFORE the runner is called, so a watcher can stop a misdirected report.

TWO TESTS THAT COULD NOT FAIL, both proved by mutation and then by sabotage-fix-revert runs. First: _assert_wrote_nothing walked the tempdir while the hook subprocess inherited the test runner's cwd, so it collected an empty list unconditionally — the sabotage run shows the old test passing WHILE the stray file existed on disk, which is the vacuity itself rather than its absence. Fixed by passing cwd=. Second: the no-repo-literal guard asserted only the substring 'github.com/', so a hardcoded git@github.com:owner/repo.git passed it. Now three nets: the tokens from check_identity.IDENTITY (imported, so it drifts with the lint rather than beside it), forge shapes the lint does not model, and this plugin's own slug read from its manifest. The strengthened guard flagged an existing comment whose placeholder was shape-indistinguishable from a live remote; the placeholder was rewritten rather than the guard weakened.

Fail-open verified by execution, not by reading: 13 adversarial cases x 2 hooks, all exit 0 — malformed JSON, empty stdin, closed stdin, /dev/null, JSON list, JSON null, empty object, wrong-typed field, 1MB input, invalid UTF-8, closed pipe, empty environment, bogus plugin root, and stdout fd closed. The genuine broken-pipe case needed a purpose-built harness since /dev/full is unavailable on macOS.

Identity: the shipped script carries no repo string. Resolution is PLUGIN_FEEDBACK_REPO, then the plugin's own manifest, then an explicit refusal naming the variable — verified by execution, including that a garbage override refuses rather than guessing.

--severity defaults to the least severe rather than 'major': an under-marked report costs a maintainer one upgrade at read time, while a queue where everything arrives major destroys the priority signal entirely.

ONE THING NOT VERIFIED, recorded rather than assumed: nobody has observed SubagentStart firing in a live session with this plugin installed. If the event were not honored the worker tier would be silently inert and every test would still pass, since the tests assert only on the hook's stdout. Corroborating but not proof: the pre-existing worker-context hook already ships on SubagentStart via atelier. Closing this needs one live dispatch.
<!-- SECTION:NOTES:END -->

## Comments

<!-- COMMENTS:BEGIN -->
author: @claude
created: 2026-08-07 00:44
---
Owner ruling 2026-08-07: the bug-vs-feature tier split is CONFIRMED as designed. A dispatched worker may file a bug directly (the bar is 'observed behavior contradicts the plugin's own stated contract' — checkable without judgment); a dispatched worker must DRAFT a feature request for its dispatcher to review and file, not file it itself; the primary/foreman-level session may file either. The description's caveat that this was an unratified interpretation of the 'level 1 or 2 agent' framing is now resolved — this is doctrine, safe to harden into shipped hook text.
---
<!-- COMMENTS:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
plugin-feedback ships as its own plugin — never dual-homed, because hook dedup is scoped to settings-file layers only, so dual-homing would fire the reminder once per installed dotfiles-agents plugin instead of once per session. Two hooks inject a short pointer (capped at 700 chars by an asserted test) and a companion script wraps gh issue create with a fixed template and label. The owner-ratified tier rule is implemented as stated: a worker may file a bug directly against an objective bar, must draft rather than file a feature request, and the primary session may file either. Adversarial review before merge caught a real consumer-facing defect (reports about third-party plugins would have landed in this repo silently) and two tests that could not fail; all three fixed and each fix proved by sabotage. Satisfies TASK-11's AC#3.
<!-- SECTION:FINAL_SUMMARY:END -->
