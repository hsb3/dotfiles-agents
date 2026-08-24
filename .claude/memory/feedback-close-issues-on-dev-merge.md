---
name: feedback-close-issues-on-dev-merge
description: Standing owner rule — close a fixed GitHub issue when its PR merges to dev, not when it reaches main
metadata:
  type: feedback
---

**Close a fixed issue as soon as its PR merges to `dev`.** Do not wait for the publish to
`main`. Standing owner ruling, 2026-08-24, given as the permanent answer so this stops being
asked per release.

**Why:** nothing closes these automatically and nothing ever will. GitHub only auto-closes on
merge to the **default** branch, which is `main` here, and `main` is written solely by the
publish workflow whose commit message is `publish: dev@<sha>` — it names no issue, so
`Closes #N` in a PR body or commit is inert in this repo. Waiting for publish therefore means
waiting for an event that never fires, leaving fixed work indefinitely open.

**How to apply:** after merging a fixing PR into `dev`, `gh issue close <n> --comment "..."`
with the PR number and the `dev` SHA. Say what actually changed and why, not just "fixed" —
the comment is the only place a reader learns the reasoning, since the issue is where people
land. This is an exception to the general rule that edits to pre-existing issues need
per-instance confirmation; the ruling IS the standing confirmation. It does not extend to
comments on other people's threads or to issues in repos the owner does not own.

Related: [[identity-gate-blocks-personal-repo-installs]], [[harness-lane]].
