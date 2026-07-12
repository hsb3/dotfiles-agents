Require every issue folder under the desk (`_meta/plans/`, or `_meta/issues/` after the rename) to carry **both** `issue_body.md` (the contract) **and** `plan.md` (the build detail) — today a folder can have only `plan.md`, so the issue-body contract goes unstaged and un-diffed against the live GitHub body.

Complements #68 (governance toolkit blind to issue-body-only folders): #68 makes the toolkit SEE body-only folders; this issue makes both artifacts REQUIRED so neither is skipped.

## Deliverable
- `coverage.py` (or a new check) flags any issue folder missing `issue_body.md` OR `plan.md`, with a non-zero exit so it can gate.
- planning-desk authoring guidance (`SKILL.md`, `references/issue-body.md`, `references/plan.md`) states both files are required, and issue mode stages `issue_body.md` even when `plan.md` is deferred (and vice versa).
- Backfill the current desk: any existing folder missing one of the two gets it (or a documented exemption for trivial issues).

## Acceptance criteria
- The check reports 0 folders missing either file after backfill; it exits non-zero on a folder with only one.
- Skill guidance names the two-file requirement explicitly.
- `make ci` green; planning-desk `targets/` rebuilt.

## Dependencies & gates
- **Blocks on:** best sequenced with #68 (same toolkit) and after the `_meta/issues` rename (sibling issue) to avoid double-touching the scripts.
- **Gates:** `make ci` + `make build-check` (planning-desk edit); `project-workflow` version bump.
