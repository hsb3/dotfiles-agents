---
name: pull-request
description: >-
  Work a pull request's review findings after the checks go green — collect the inline
  review comments, the review and summary-level comments, and the gate statuses; classify
  each finding as actionable (it sits on a line this PR changed, or it is a failing hard
  gate) or as pre-existing rot; then report the deferred set by name instead of dropping
  it. Use when asked to "check the PR comments", "address the review feedback", "what did
  the review bots say", "is this PR ready to merge", or right after opening a PR and
  watching its checks go green.
---

# Pull request — read every finding before calling it done

A green check is not a finished PR. The status check reports what the gates ran; the
repository's automated reviewers post their findings on a **separate surface** that no
check status reflects. A PR can be all-green and carry unread review comments, and the
usual failure is closing the loop on `gh pr checks` alone.

This is the read-and-triage pass. It ends with every finding either answered or **named as
deferred** — never with a silent drop.

## 1. Resolve the PR

With a number, use it. Without one, resolve the current branch's PR:

```bash
gh pr list --head "$(git branch --show-current)" --state open --json number,url --jq '.[0]'
```

**Filter on state, and do not use bare `gh pr view` to resolve.** `gh pr view` returns the
branch's PR whatever its state, so on a branch whose PR already merged it hands you a
merged PR and you triage its stale threads believing they are live. Selecting `state` and
checking it is `OPEN` works equally well; what does not work is trusting the lookup.

No PR for this branch is an answer, not an error: say the branch has no open PR, show
`gh pr status` so the person can see whether one exists elsewhere, and stop. Do not open
one, and do not fall back to the most recent PR in the repo — that reads someone else's
review as your own.

## 2. Collect all three surfaces

Read all three every time. Each carries findings the others do not.

```bash
gh api repos/{owner}/{repo}/pulls/<n>/comments --paginate    # inline, line-anchored
gh pr view <n> --json comments,reviews                       # summary + review bodies
gh pr checks <n>                                             # gate status
```

`{owner}` and `{repo}` are literal — `gh api` substitutes them from the current
repository. `--paginate` is not optional: on a busy PR the first page looks complete and
is not.

The inline stream is where line-level findings live. The `reviews` array is where a
reviewer's overall verdict and its summary body live, and a body there frequently holds
findings that never became inline comments.

## 3. Classify every finding

One rule, applied to each finding:

**ACTIONABLE** if either holds:

- it is a **failing hard gate** — a required check that is red, whatever it points at; or
- it sits on a line **this PR's own diff touched**.

Derive the touched set rather than guessing at it. `gh pr diff <n>` prints the patch; each
hunk header `@@ -a,b +c,d @@` gives the new-side range `c`..`c+d-1` for the file named in
the preceding `+++ b/<path>` line. A finding is on a touched line when its `path` matches
and its `line` falls in one of that file's ranges.

Two parsing details that silently misfile a finding as pre-existing if you skip them:

- **An omitted count means 1.** Git really emits `@@ -1 +1 @@` for a single-line hunk, so
  a formula that requires `+c,d` drops that hunk and the file looks untouched.
- **A path containing a space gets a trailing TAB** on its `+++ b/<path>` line. Split on
  the tab before using the name, or every finding in that file reads as pre-existing.

**PRE-EXISTING** otherwise — a finding on code this PR did not change. Real, and not this
PR's job.

Three cases that trip people up:

- **An inline comment with `line: null` is outdated**, not gone: it was anchored to a line
  a later push rewrote, and `original_line` says where it was. Its file is in the diff, so
  it fired on your change — treat it as actionable and check whether the rewrite already
  answered it.
- **A summary or review-body finding has no `path`.** Classify it by what it names: a file
  and line get the same test as above; a remark about the change this PR makes is
  actionable; a remark about the repository at large is pre-existing.
- **Unsure? Actionable.** Answering a finding that was not yours costs a sentence; missing
  one costs a merge.

## 4. Report

Report in exactly this shape, both sets always present, each with its count:

- **One-line verdict** — is this PR ready to merge, and if not, what is holding it.
- **ACTIONABLE (n)** — per finding: where it came from (inline / review body / gate),
  `path:line`, what it asks for in a few words, and either the fix you are making or why
  the finding is wrong.
- **DEFERRED — pre-existing (n)** — per finding: `path:line` and one line on why it is out
  of this PR's scope. An empty set is stated as "none", never omitted.

Never collapse this to "CI is green" or "no blockers". A missing **DEFERRED** section is
indistinguishable from a triage that never looked, which is the failure this exists to
stop. If a finding was ambiguous and you called it actionable by default, say so rather
than presenting the call as clean.

**Then stop.** Reporting is the deliverable. Fix the actionable set in the same turn only
if the person asked for that — "address the review feedback" is such an ask, "check the PR
comments" is not. If you do fix: reply on each thread you addressed or rejected, push, then
re-read every surface, because the reviewers run again on the new commit.

## Traps

- **A green gate proves nothing about the comment stream.** They are different surfaces
  and neither reflects the other's state.
- **The reviewers post asynchronously.** Findings land minutes after the checks turn
  green, so a read taken the instant CI passes is an early read — re-read after the last
  push has settled.
- **Deferred is not ignored.** Every pre-existing finding is either filed on the tracker
  or answered in the thread as out of scope. "I did not mention it" is how rot becomes
  permanent.
- **Do not grow the diff to satisfy a pre-existing finding.** The larger the diff, the
  less of it gets reviewed; fixing untouched code inside a feature PR trades a real review
  for a cosmetic one.
- **Resolving a thread is not answering it.** Say what you did, in the thread, before
  resolving.
