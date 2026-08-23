---
name: task-authoring
description: Write tracked work items a cold agent can actually execute — titles, acceptance criteria, thresholds, approval gates, scope ownership. Use whenever creating or rewriting a Kaneo task, a GitHub issue, an OpenSpec change, or any tracker item, and when reviewing an existing task for executability.
---

# Task authoring

The executor is an agent with none of your context. Everything you leave implicit becomes a
coin flip you delegated.

## Titles: for scanning, not describing

- **Shape `area: outcome`** — first token is the component touched (`auth-proxy`, `docs`,
  `evals`, `ops`). Scanning the lane then groups related items for free.
- **Outcome, not symptom or activity** — "runs fail loudly on infra errors", not
  "investigate why errors surface as normal replies". A finding-shaped title goes stale the
  moment work starts; an outcome-shaped one *is* the acceptance criterion.
- **One clause, <=70 chars.** Evidence, issue/PR numbers, and "follow-up to X" belong in
  the body; past the limit the board UI truncates anyway.
- **No `feat:`/`fix:`/`chore:` prefixes** — labels carry type; the prefix burns the
  highest-value characters in the title.
- **Prefix non-work items by kind** (`DECISION:`, `REF:`, `HANDOFF —`) so they never
  masquerade as buildable work.
- Before renaming anything, grep for what points at the old title by exact string (hooks,
  docs, automation) and exempt those.

## Acceptance criteria must be able to fail

- **Run every criterion against today's baseline before writing it.** A criterion that
  already passes detects nothing — "no broken links in these two files" passed while 64
  broken links sat in the files it didn't cover.
- **Record the baseline number** ("64 broken links -> 0"; "28 referenced paths, 0 missing").
  Done becomes measurable instead of arguable.
- **Check that the check detects the failure it names.** `mise tasks` exits 0 even after
  every script it references is deleted; a path-prefix gate goes silently blind when files
  move out of the matched prefixes. Prefer "extract the paths and assert each exists" over
  "the tool ran green".
- **Verification must be safe and runnable cold**: name the credentials and prerequisites,
  give the exact command, and never use a mutating action (a deploy script, a key-vault
  bootstrap) as a test. State the fallback when creds may be absent — validate-only, marked
  owner-run.

## Words that need a number or a command

Replace judgment words with thresholds: "stale" -> last commit >120 days; "dead" -> zero
references in a named file list; "load-bearing / complexity warrants" -> >50 lines or real
control flow; "matches contents" -> diff a generated listing against the doc. Two agents
given a judgment word produce two results; given a threshold, one.

## Gates and approvals need a mechanism

- "Apply after owner review" is not executable. Reference the ritual explicitly: post the
  artifact as a board comment -> set status blocked -> stop -> owner approves by comment ->
  resume. Otherwise a cold agent blocks forever or self-approves.
- Say what the task may **not** touch — CI workflows, pre-commit gate scripts, anything
  whose pass/fail meaning other tasks depend on. "Path strings yes, job logic no" is a
  one-line authority statement that prevents a stall.

## Scope, sequencing, ownership

- **"Coordinate with task X" is not sequencing.** If two tasks can edit the same files, name
  one owner per file set and make the ordering a blocking edge on the board.
- **State the delta, not the ideal end state.** If the goal is already mostly true, a cold
  agent can't tell what to change — say what is wrong today.
- **Classify artifacts by function, not location.** A deploy script living in `scripts/dev/`
  went unclaimed by both the deploy task and the scripts task.
- **Deliverables need a location and a lifecycle**: where the output goes (board comment vs
  in-repo file), who consumes it, what happens after approval.

## Facts and tools named in the task

- Verify every factual claim (file lists, counts, "X exists") against reality before writing
  it in, and date-stamp it ("verified 2026-08-19"). One task named a move target that a
  blocking task was about to delete.
- If the task names a skill or tool, read that tool's own scope statement first. Invoke it
  only when the scopes match; otherwise write "in the spirit of X, don't invoke it". Name
  the tool's source (marketplace/repo) so a cold agent on another machine installs it
  instead of improvising.
- **Reread the finished task for internal contradictions** — "every folder" in one section
  against "larger folders" in another; "add these fields" beside a gate that forbids them.
