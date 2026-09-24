# Briefs — the handoff packet a worker actually gets

A brief is written for an agent with **zero chat context**. Ambiguity in a brief is the session
silently delegating a decision it was supposed to make.

This file covers the **execution layer** — `scout`, `builder`, `reviewer`. The brief is that
layer's entire context, and rule 3 below is the boundary on what may not enter it. For the
**management layer**, use `manager-brief.md` instead: a manager gets the DoD verbatim and the stop
conditions, and it writes its own workers' briefs to this file's rules.

## Required fields

- **Repo path** (absolute) and the environment or working commands.
- **Exact objective** — what must exist when done, and why, in enough detail to make good local
  calls.
- **In and out of scope, WITH file ownership** — which files this agent owns, which are
  report-only, and **which are read-only config** (gate, lint, typecheck, coverage thresholds,
  CI). One file has one owner per wave — including against whoever dispatched the worker; a
  manager does not edit inside its own builder's owned list (`waiting.md`).
- **Evidence format** to return.
- **Verification commands** to run, each with its expected output, and the instruction to paste
  actual output. A criterion with no command attached is not a criterion — rewrite it until a
  machine can check it.
- **Stop conditions** — "if the code does not match this brief, or a command fails after a
  reasonable retry, stop and report; do not improvise."

## The three rules

### 1. Every constraint gets a budget, a stop condition, or a machine check

An instruction an agent cannot tell it has satisfied gets **maximized, not satisfied**. Measured:
an unbounded "all fixed values live in one named-constant block" rule produced a ~90-line
constants wall in the lab's TypeScript solution; a usage census found 43 of its 57 constants were
single-use, and a deletion probe (9 representative constants inlined; gate green, golden output
identical) confirmed the class was behavior-inert. The rule, not the code, was the defect, and it
cost that solution its worst dimension score, unanimously, on its round's panel.

Write constraints that carry their own limit:

| Unbounded (gets maximized) | Bounded (gets satisfied) |
|---|---|
| "Comment the code well" | "At most one doc comment per function plus one inline comment for the genuinely non-obvious" |
| "Define constants at the top" | "Name a literal only when it is shared across ≥2 sites or genuinely cryptic" |
| "Be thorough in the audit" | "Report every violation of §3; stop when the file list is exhausted" |
| "Handle errors properly" | "Every external boundary passes through the schema; malformed input degrades per spec §4, never throws" |
| "Add tests" | "One test per behavior enumerated in the required-coverage list; coverage gate ≥85% is the check" |

Best of all: if a tool can check it, make the tool check it and delete the prose. Prompt rules are
for what tools cannot see.

**The same rule binds a constraint an agent adopts for itself**, and that half is where the
damage has actually landed: every deadlock reported so far was an agent waiting on a condition it
invented and never bounded. A stop condition adopted mid-flight names what would satisfy it, who
produces that, and what the agent does when it does not arrive — or it is not a stop condition,
it is a deadlock. `waiting.md` carries the rule and the one-way message channel behind it.

<!-- harness:claude-code -->
Four such deadlocks have been reported, all of that shape; `waiting.md` also carries the liveness
check for the one where a manager could not tell a dead worker from a slow one.
<!-- /harness -->

### 2. Test-first is the default, and RED is the evidence

Adding strict test-first discipline was the single largest measured quality lever in the lab:
+0.21 to +0.42 weighted score per language, essentially all of it in test quality (one language
moved 2.67 → 4.50 on that dimension) with a type-story spillover; the only declines anywhere were
−0.50 and −0.16 on single dimensions, and every weighted total rose. One language's implementation
got shorter. The mechanism is design rather than ceremony: writing the
test first forces an injection seam, so effectful collectors take their dependencies (command
runner, filesystem, clock) as parameters. The best type story in the lab's whole corpus exists
because a test demanded a seam.

In any brief that produces or changes behavior:

> Strict test-first: write the test, **observe it fail**, write the minimum code to pass, refactor
> on green. In the handoff note, name each behavior and quote the failure you observed before
> fixing it.

- **Exemption**: entry-point wiring and pure rendering, covered by an end-to-end test.
- **Hermeticity**: tests must be green on a bare machine, never dependent on the host's real
  state. This is what makes the suite a fixative that later passes can lean on.
- **Coverage counts only in-process execution**, so the entry point must be callable in-process,
  not only via subprocess.

### 3. The negative list — what a worker must never be told

Information asymmetry is deliberate, and it held up across every round of the lab: workers who
could not see sibling solutions, prior rounds, or the cycle budget produced honest, scoped work.
Field-level problems were caught by the layers above (gates, output diffs, judge panels) — never
by a worker self-report, which was structurally unable to see them.

This is the execution layer's context boundary, and it is load-bearing twice over: it keeps
workers honest, and it is why the differential and the panel mean anything at all.

Never put these in a worker brief:

- **Cycle budgets, remaining passes, or the fact that a later pass exists.** A worker told its
  work will be reviewed again gold-plates the current pass.
- **Rubric scores, rankings, or how a sibling scored.**
- **Sibling implementations, prior rounds, or git history of the same work** — "work only from the
  contract" is the instruction. Cross-contamination destroys the independence that makes a
  differential meaningful.
- **The session's own plan beyond this slice.** In-scope, out-of-scope, and what other owners need
  to know: that is the whole map a worker needs.

<!-- harness:claude-code -->
Also keep the tree free of stray `CLAUDE.md` files during a fan-out. The harness injects them into
every worker session, which makes them an uncontrolled side channel into agents that are supposed
to be reading only the brief.
<!-- /harness -->

## Worker brief template

```
Repo: <absolute path>.  Read <contract path> first — it is the complete spec. Follow it exactly.

Objective: <what must exist when done, and why>.

You own: <file list>.  Report-only (never edit): <file list>.
READ-ONLY config (gate, lint, typecheck, coverage, CI): <file list>. If a gate looks
unsatisfiable, stop and report — never loosen it.

Constraints:
- Strict test-first: test, observed RED, minimal GREEN, refactor. Quote each RED in your note.
- <constraint>, bounded by <budget / stop condition / the check that enforces it>.
- All external input crosses <schema>; malformed input degrades per <spec §>, never throws.

Do NOT read git history, sibling implementations, or any other solution. Work from the contract.

Definition of done: `<gate command>` fully green, plus `<smoke command>` produces <expected>.

Report: files changed, each acceptance criterion with the command run and its ACTUAL output,
the RED you observed per behavior, what you deliberately deferred, and anything another owner
must know. Leave no scratch files. Stop and report rather than improvising.
```

For the mechanical-transform variant (one codemod across many sites), use the worker template in
`migrate-at-scale.md` instead — it adds the site list, the exact transform, and the odd-site
escalation rule.

A report-only brief (`reviewer`, `scout`) owns no files and replaces the "You own" line with its
scratch location. Read-only roles run in the parent checkout, so a probe that defaults its
project directory to the cwd writes into the very tree under review:

```
Report-only: write nothing under <repo> or any directory above it. Scratch lives in
/tmp/rev<PR>-<slug>/ only: cd there in every command (a shell may reset its cwd between
calls), and pass every tool that takes a project directory (--project-dir, -C, a positional
repo path) an explicit path. A probe never defaults to the repo. Any mutate-then-restore proof
runs in a copy under that scratch dir.
```

Brief wording is not enforcement. After a report-only worker returns, compare the checkout's
status, untracked and ignored files included, against a snapshot taken before dispatch; any new
or vanished entry is a protocol breach to report and clean up by hand.

<!-- harness:claude-code -->
Bracket every report-only dispatch with `scripts/trace_check.py` from this skill (from an
installed plugin,
`~/.claude/plugins/cache/dotfiles-agents/atelier/<version>/skills/delegation/scripts/trace_check.py`):
`python3 trace_check.py snapshot <repo> /tmp/trace-rev<PR>-<slug>.json` before dispatch, then
`python3 trace_check.py check <repo> /tmp/trace-rev<PR>-<slug>.json` after it returns. The
snapshot sits outside the worker's `/tmp/rev<PR>-*` scratch so its cleanup cannot delete it.
Exit 1 names each new or vanished status entry and each new or vanished ref, HEAD's target
included; Python bytecode under `__pycache__/` is ignored, since re-running a test suite writes
it. It is blind to a rewrite of a path that was already dirty, to other writes under `.git/`
(config, hooks), to an empty new directory, and to writes inside a nested repo or worktree
(including `.claude/worktrees/`). A concurrent writer in the same checkout, or a commit in a
sibling worktree (refs are shared), shows up as noise, so snapshot with no other writer live.
<!-- /harness -->

## Reading a returned brief

A handoff note is a **hypothesis**, not proof. Before accepting it: re-run the gate, check that
pasted output matches the commands claimed, and confirm the worker stayed inside its file
ownership (`git diff --stat` against the owned list). A worker that touched read-only config, or
pushed, merged, or committed outside its own worktree, has breached protocol regardless of how
green the result looks.
