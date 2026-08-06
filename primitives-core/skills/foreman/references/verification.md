# Verification — proof of completion, not reports of completion

## The evidence ranking

Strongest first. Accepting a lower rank when a higher one was available is the recurring way a
foreman ships something wrong.

1. **A loud gate.** A command that fails when the work is wrong, run by the session itself. Only
   counts if the gate has been proved red at least once.
2. **An output differential across independent producers.** Two or more agents produced artifacts
   that should agree observably, and their outputs are identical. This catches what no
   single-producer gate can.
3. **An independently re-derived check.** A `reviewer` that re-read the source or re-ran the
   command, without the producer's rationale.
4. **A lead's proof package.** Evidence assembled by a same-tier agent that also did the work. It
   catches worker errors; it cannot catch its own blind spots.
5. **A worker's self-report.** A hypothesis. Honest workers still report confidently about things
   they were structurally unable to see.

**Silent caps read as full coverage.** Any wave that bounded its scope — top-N, sampling, "the
first twenty files", a skipped case — gets that cap surfaced to the user and added to the backlog.

## The differential

**When two or more agents produce artifacts that should agree observably, the reconciliation is a
diff of their outputs, not a reading of their diffs.**

This is the highest-yield verification technique in the lab's record. Three independent
implementations of one spec, each with its own green gate, still disagreed in two ways no
single-solution check could have surfaced: the result set depended on the process environment, and
sort order diverged because one implementation compared timestamps at nanosecond precision while
another truncated to milliseconds. Convergence came only after the contract named the precision at
which "equal" is judged.

**Procedure.**

1. Pin the environment. Run every producer under the same `PATH`, `HOME`, locale, and working
   directory. An environment difference produces a diff that is real but uninteresting.
2. Capture golden output on representative invocations: the normal case, each error path, and the
   empty case. Save stdout, stderr, exit code, and any files written.
3. Diff. Normalize only what the contract explicitly leaves free, and say so out loud. The lab's
   contract left an absolute-path column unspecified, so its diffs dropped exactly that column:
   `rev | cut -d, -f2- | rev` strips the first field from the end of each CSV row, which is easier
   than field-counting when the free column is first.
4. Read a disagreement as a **contract defect first**. Every divergence the lab's differentials
   surfaced traced to an unwritten clause, not a coding error. Fix the contract, then decide which
   implementations need to change.

**When no natural redundancy exists** and the claim is high-impact, build the oracle
deliberately: a second cheap implementation of just the disputed behavior (a 20-line script that
computes the same answer a different way) is often cheaper than an argument about whether the
first one is right.

**Where this applies outside code:** two scouts given the same question with different search
strategies, two reviewers given the same claim without each other's reports, a rewritten config
compared against the original by dumping both resolved states. Anywhere the answer should be
identical, make the comparison mechanical.

## The panel escalation

`reviewer` returns confirmed / refuted / unverifiable per claim, which is exactly right for a
factual claim. It is not right for a claim with a judgment in it ("is this design maintainable",
"is this the cleanest of the three", "is this ready to ship"). A single judgment verdict has no
calibration and no disagreement signal.

For judgment-shaped claims, escalate to a panel — the `rubric-panel` skill implements the
protocol. Three properties make it work, and all three are cheap:

- **Persona diversity.** Distinct lenses (long-term maintainer, language purist, QA skeptic, or
  domain equivalents) surface different failure modes. Three identical reviewers mostly agree with
  each other.
- **Whole-field scoring.** Each judge scores **every** target rather than one each. Calibration
  drifts between judges but stays consistent within a judge, so within-panel ranking is strong
  signal and cross-panel score levels are weak signal. Never compare scores across panels and call
  the delta a result.
- **Contested flags.** A spread greater than 1.5 points on a dimension is surfaced as contested,
  never silently averaged. Disagreement is a finding that needs a decision, not noise.

Judges are read-only, score against written anchors rather than on a curve, cite concrete code for
every score, and earn no credit for process artifacts (a TDD log is not a score).

**The delegation analogue for architecture C:** when N workers each produced a slice, dispatch
**one reviewer across all N slices** rather than N reviewers each seeing one. Cross-slice
inconsistency — two owners solving the same sub-problem differently, a convention that drifted
between slices — is invisible to a single-slice reviewer, and it is precisely what the
reconciliation pass exists to find.

## Aiming verification where the stack is weak

Defect shape is predictable from the language and stack, so a targeted reviewer brief beats a
generic one. Recurring signatures from the lab's three-language corpus — tendencies, not laws
(Python's idiom lead disappeared under the frozen rig; TypeScript's type ceiling emerged only
after round 1):

- **Python**: usually the best cold read, weakest unforced error paths in every round. Aim reviews at
  malformed input, missing tools, and the empty case. Its test seams tend toward monkeypatching
  module internals, which reads as weaker design than injected dependencies.
- **Go**: compiler-forced robustness, so error paths are the strong side; the tax is
  extensibility. Aim reviews at how many places a new case must be registered.
- **TypeScript**: highest type ceiling (misuse will not compile) and the highest variance
  everywhere else. Aim reviews at whether the strictness is real — types that no checker runs over
  are decoration, since the runtime strips them without checking.

The generalization: ask what the toolchain **cannot** see, and point the reviewer there. Gates
move exactly what they measure and nothing else.
