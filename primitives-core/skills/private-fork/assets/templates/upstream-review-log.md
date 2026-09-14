# Upstream Review Log

_Append-only ledger of upstream (`{{UPSTREAM_ORG}}/{{NAME}}`) review sessions: which
commits/PRs were looked at and the verdict on each. This is the answer to "have we seen
this upstream change, and what did we decide?"_

Status: active
Last-reviewed-upstream-commit: {{SHA — the upstream commit the fork was created from}}

## How this works

- Cadence and procedure live in the merge SOP (Step 0).
- `scripts/upstream-digest.sh` (or `make upstream-review`) generates a pre-triaged
  digest of everything between the `Last-reviewed-upstream-commit:` watermark above and
  `refs/remotes/upstream/{{BRANCH}}` — the full refname the digest script resolves.
- A review session fills the digest's Verdict column, pastes the finished block below
  (newest first), and advances the watermark line. **The watermark only advances when
  every commit in the range has a verdict.**
- Verdicts: **adopt** (take via merge/cherry-pick) · **adapt** (take, but modified to
  fit the fork — note how) · **pass** (not applicable — note why) · **defer**
  (undecided; carried in *Open deferrals* until resolved).
- Reviewing is not merging: a session may verdict everything and merge nothing.

## Open deferrals

_(none)_

## Sessions

_(newest first)_
