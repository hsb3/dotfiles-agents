# Waves on GitHub

Inventory reads from issues; the triage view lives in a pinned issue's body; a wave lands as a
PR that closes issues via keywords.

## Inventory

```sh
gh issue list --state open --limit 300 \
  --json number,title,labels,milestone \
  --jq '.[] | "\(.number)\t\(.title)\t[\([.labels[].name]|join(","))]\t\(.milestone.title // "-")"' | sort -rn
```

Ranking signals, in priority order: `gate:*` labels → milestone → epic/sub-issue links → owner
rulings in the handoff. Exclude the triage issue itself and dependabot PRs from the inventory —
neither is a backlog item.

## Triage view

The pinned issue's **body** is the durable ranked plan plus delivery plan — read and rewritten
whole each refresh, never touched by commits. **The issue list / labels / milestones are the
source of truth; this body is a view** — if they disagree, fix the body, not the truth.

Read the current body, edit it, write it back whole:

```sh
gh issue view <N> --json body -q .body > /tmp/triage-body.md
# edit /tmp/triage-body.md
gh issue edit <N> --body-file /tmp/triage-body.md
```

Position rule: **open work leads; executed plans sit last, collapsed.** Never let an EXECUTED
delivery plan sit above the open backlog sections — position is the reader's only
done/outstanding cue. Collapse prior executed plans into `<details>` one-line pointers.

## Landing a wave

One wave = one branch = one PR. Open the PR, then:

1. **Disposition every review-bot finding** — address blocking concerns *and* nits, or record
   why not, on the PR thread. Commit, push, re-review; repeat until no concerns remain and CI
   passes. A green check can still hide unaddressed comments — check the thread, not just CI.
2. Merge in the declared order, closing issues via PR keywords (`Closes #N`, `Fixes #N`) in the
   PR body or commit message so the merge closes them automatically.
3. **All merges are reserved to the session** — crews open PRs, never merge them.

## Init — seeding the triage view

Create an issue titled `meta: triaged open-issue backlog (living list)`, pin it
(`gh issue pin <N>`), and seed the body:

```markdown
_A curated, ranked view of the open backlog — pinned so it's the first thing a session sees.
**The issue list / milestones / labels are the source of truth; this body is a view.** Maintained
by editing this issue (no repo commits). Excludes itself and dependabot PRs._

**Last refreshed: YYYY-MM-DD** · N open issues at refresh time

## Now — actionable, unblocked
| # | Title | State | Blocked by |

## Milestone — what actually remains
## Backlog — no milestone
## On hold — parked by owner ruling, don't pick up
## Decision gaps — the owner queue

# Delivery history — shipped, provenance only

## Delivery plan vN — PLANNED | EXECUTED YYYY-MM-DD
| Wave | Branch | PR | Resolves | Gate |

## Maintenance protocol
- **Open work leads; executed plans sit last, collapsed.** Never let an EXECUTED plan sit above
  the open backlog — position is the only done/outstanding cue a reader gets.
- **Every issue from the inventory appears exactly once** in the open-work sections above, with
  its state explicit — outstanding-or-not must be answerable at a glance, never inferred.
- Refresh at session boundaries alongside the handoff pass, or whenever issues change in bulk —
  a stale ranked view is worse than none.
- Regenerate the inventory (gh issue list …), re-rank, edit this body, bump the refresh date.
- Ranking inputs: gate:* labels → milestone → epic/sub-issue links → owner rulings in the handoff.
- Keep pinned; it lives here (not a tracked file) so refreshes never touch commit history.
```

Write `gh issue edit <N> --body-file <seed-file>` once created, then pin it.

## Gotchas

- **A green CI check can hide unaddressed review comments** — disposition the thread itself
  before merging, not just the status check.
- **Dependabot PRs and the triage issue itself are excluded from the inventory** — `gh issue
  list` already skips PRs, but don't accidentally fold the triage issue into ranking when
  eyeballing results.
- `gh issue edit --body-file` replaces the whole body — always read-then-edit-then-write-whole,
  never a partial patch, or a concurrent triage edit gets clobbered.
- Merging via PR keywords only closes issues if the keyword lands in the default branch's merge
  commit/PR body — a squash merge with a hand-edited subject can silently drop the keyword.
