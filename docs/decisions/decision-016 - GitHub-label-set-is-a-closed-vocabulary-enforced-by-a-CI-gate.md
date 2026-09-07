---
id: decision-016
title: GitHub label set is a closed vocabulary enforced by a CI gate
date: '2026-09-07'
status: accepted
---
## Context

The repo's GitHub labels had accumulated a stale sprawl — `status:*`, `priority:*`, `area:*`,
`phase:*`, `bug`, `feature`, `chore`, `docs` and more, the issue-event history holds the full
list — sitting alongside the taxonomy actually in use. Much of it
arrived because kata's GitHub sync writes labels onto the repo, and nothing constrained what
could appear there: a label minted by a sync was indistinguishable from one somebody chose.
No gate read the label set at all, so the taxonomy drifted by accident rather than by
decision. Ruled on kata card `z1xy`.

## Decision

Owner ruling, 2026-09-07 (on `z1xy`):

1. The repo's GitHub label set is a CLOSED vocabulary: exactly `type:feat`, `type:fix`,
   `type:chore`, `decision`, `epic`. A label present that is not on that list is drift; a
   label on that list that is absent is drift too.
2. Enforcement is `scripts/check_labels.py`, which reads the live set and fails naming the
   `gh label delete '<name>'` / `gh label create '<name>'` command that fixes each
   difference — the failure is the fix instruction, not a diff to interpret.
3. It runs CI-only — a step in the `drift guards` job, plus `make labels` by hand — because
   it needs `gh` and network, and `make ci` is offline-and-zero-install by design. It rides
   an existing job rather than getting its own because `dev`'s branch protection pins
   required checks by job NAME. Same placement, same two reasons, as `check_version_bump.py`
   and `check_vendored_drift.py`.
4. **A gate that cannot measure is red, never green.** Every failure to read the live set
   exits 1 — `gh` missing from PATH, `gh` failing against a host that answered, and an
   unreachable `api.github.com` alike. This diverges from `check_version_bump.py` and
   `check_vendored_drift.py`, which skip an unreachable remote with a notice and exit 0.
   The reason is what a CI summary shows: a step that exits 0 having measured nothing is
   indistinguishable there from one that measured and found the set clean, and a green
   check nobody can distinguish from a real one is worse than no check. The failure
   message still names which of the three it hit, and the unreachable one says outright
   that it is not evidence of drift. The cost is a re-run on a network blip; that is the
   cheaper mistake.
5. The vocabulary is declared as a constant in the checker. No new tracked config file:
   nothing generated is tracked (ADR 0017), and a one-line YAML would be a file that exists
   only to be read by one script.
6. kata's GitHub-sync `title_prefix` is OFF. Titles on GitHub read as themselves; the kata
   short id is not prefixed onto them.
7. **Standing rule:** never re-enable a kata GitHub binding on a live board without taking a
   `kata list --status all --json` snapshot first.

This succeeds decision-014 on the kata/GitHub-sync axis. Decision-014 made the kata board the
sole tracker and carried forward decision-1's rule that GitHub issues are bug intake only;
both still stand. What this adds is a constraint on what that sync is allowed to leave behind
on the repo.

## Consequences

**The incident that produced point 7.** Turning `title_prefix` off meant disabling and
re-enabling the board's GitHub binding. Re-enabling RESET the binding's sync cursor, so kata
treated the repo as never-synced and re-applied every GitHub field onto the board as if from
scratch. Measured blast radius: 96 titles rewritten, 30 bodies rewritten, 3 issues reopened,
8 label changes, 27 priorities blanked. It was restored by hand and verified back to a
0-of-200 diff against the pre-incident snapshot. That snapshot is the only reason the restore
was possible — without it there is no record of what the board said before the overwrite, and
the damage is silent and permanent. That is why point 7 is a standing rule and not advice.

- Adding a label to the repo now requires amending the vocabulary in the checker in the same
  change. That is the point: the gate makes the taxonomy a decision somebody makes on
  purpose, rather than an accident somebody notices months later.
- kata's sync minting an unexpected repo label is precisely the drift this catches — the
  failure mode that produced the stale mixture above now turns the `drift guards` job red on
  the next PR instead of accumulating unseen.
- The stale labels were deleted before this record was written, so the live set already
  matches the vocabulary and the gate lands green rather than as a backlog of cleanup.
