---
id: TASK-10
title: 'Externals: build the pinned-vendored-copy mechanism (decision-6)'
status: Done
assignee: []
created_date: '2026-08-04 00:43'
updated_date: '2026-08-06 21:31'
labels:
  - distribution
milestone: m-0
dependencies:
  - TASK-2
  - TASK-26
references:
  - 'https://github.com/hsb3/dotfiles-agents/issues/36'
priority: high
type: feature
ordinal: 700
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Build the externals mechanism ruled by decision-6 (pinned-vendored-copy, superseding the original clone-at-build design from GH #36). Vendoring is gated by docs/vendoring-rule.md (task-26, merged 2026-08-06 in PR #238) — this task builds the enforcement: the ADR 0015 amendment, the `origin: vendored` roster class + check_provenance arm, dropping the 4 re-hostable plugin externals, reclassifying pptx-themes/base, and optionally `make externals-drift`. Also the compliant path for the parked visual-planning skills (draft-3) and the mechanism home for vendored-skill provenance (task-11). Design memo: _meta/plans/externals-clone-vs-vendor/memo.md. Unblocked: task-26 is Done.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 Decisions 1-7 ruled and recorded
- [x] #2 ADR 0015 amended to permit `origin: vendored` under docs/vendoring-rule.md, citing it
- [x] #3 Roster schema + check_provenance gain the vendored arm (upstream + immutable SHA + LICENSE + attribution enforced)
- [x] #4 The 4 install-from-upstream plugin externals dropped from the roster/externals.yaml
- [x] #5 pptx-themes/base reclassified `origin: vendored` and passes the new arm
- [x] #6 make ci green (drift guards clean under the amended rules)
<!-- AC:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Decisions ruled 2026-08-03 (decision-6, AC#1 satisfied): materialization = pinned-vendored-copy, superseding clone-at-build (#36 / ADR 0003). D1-D7 resolved per memo `_meta/plans/externals-clone-vs-vendor/memo.md`. Also: drop the 4 plugin externals (install-from-upstream, not re-hosted) — only pptx stays vendored; vendoring gains a minimum-bar rule (task-26, blocks this build). Now depends on TASK-26.

**Built 2026-08-06** (owner verified via `_meta/signoff/2026-08-06-m0-rulings/`, item A):
ADR 0015 amended to permit `origin: vendored` gated on `docs/vendoring-rule.md`; `origin`
enum in `check_roster.py` gained `vendored` and `disposition` gained `orphaned` (D5's
require-or-reclassify); `check_provenance.py` gained invariant (3) — every vendored entry
must carry LICENSE + non-null upstream + ref. `pptx-themes` reclassified `authored` →
`vendored` with `upstream: anthropics/skills` @ `fa0fa64`; its `base/LICENSE.txt` copied to
the skill root so the check finds it at the entry's `source`. `externals.yaml` trimmed 5 → 1
(pptx only). `make ci` green.

**Not built, deliberately:** the optional `make externals-drift` checker (D4's
`up_to_date|behind|diverged|not_found` model) — it was optional in the memo and needs
network, which no current lane has. Filed as a follow-up consideration under task-11, which
owns the vendored-skill quality layer.
<!-- SECTION:NOTES:END -->
