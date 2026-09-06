---
name: feedback-tracker-workflow
description: Owner rulings on working the kata board — the owner's queue, reproduce before building, close by hand on the dev merge
metadata:
  type: feedback
---

Three standing owner rulings on tracker work. The claim ritual itself is the kata block in AGENTS.md.

**Work the owner's queue; never self-select from the pile** (2026-08-18). On kata the queue is `kata list --label up-next` (the label replaced `kaneo-status:up-next` in the 2026-09-06 board cleanup, r2m0; it started as what sat in Kaneo's Up Next at the 2026-09-02 cutover) plus whatever the owner schedules or prioritizes (`kata next`, `kata ready`). Empty means ask the owner to stock it. **Why:** pulling from the pile substitutes an agent's ranking for the owner's, and a session spends itself on something nobody prioritized.

**Reproduce before building from a card, and before closing one** (2026-08-17). A card records what the filer inferred from a symptom. In one session one card's defect had been fixed weeks earlier and another's four API claims all failed to reproduce; a card closed on a half fix was refiled twice from other projects. **How to apply:** run the card's repro against the current tree and the live system first; if it does not reproduce, say so on the card and work out what part is genuinely outstanding. When a card asserts an API contract, measure it on a throwaway project and put the measurement in the docs. See [[testing-means-real-proof]], [[feedback-verify-state-before-staging-decisions]].

**Close a fixed issue as soon as its PR merges to `dev`** (2026-08-24, the permanent answer). Nothing auto-closes here and nothing will: GitHub closes only on the default branch, `main` is written solely by the publish workflow (`publish: dev@<sha>`, names no issue), so `Closes #N` is inert. **How to apply:** `kata close <ref> --done --commit <sha> --evidence pr:<url> --message "..."` and `gh issue close <n> --comment "..."` for the mirror, naming the PR, the `dev` SHA, and what actually changed. This is the standing confirmation for that edit to a pre-existing issue; it does not extend to other people's threads or repos the owner does not own.
