# The interview

Eight questions, in order. The first two decide the rest, so do not let the
conversation jump to tooling — an owner who starts with "let's use ruff and mypy" has
skipped deciding what the thing *is*, and the gate ends up enforcing a shape nobody
chose.

Ask one question at a time. Play back what you heard before moving on. When an answer
is vague, say so and ask the sharpening follow-up; a vague answer here becomes an
argument three weeks from now.

---

## 1. What is the artifact?

> "In one sentence, what does this repo produce? Not what it's about — what comes out
> of it."

Then: **"What does success look like that isn't 'it's finished'?"**

This second question is the one that pays. It forces a success condition you can
actually check. "The docs are complete" is not one. "An agent that read only `SKILL.md`
routes to the right reference and never asserts an unverified claim" is.

| Vague answer | Follow-up |
|---|---|
| "A CLI tool" | "What does it print, and where does it write?" |
| "A library" | "Who imports it, and what's the smallest useful call?" |
| "Documentation" | "Read by a human or loaded by an agent? They have different failure modes." |
| "It'll be obvious once we start" | "Then name one thing that would make you say we built the wrong thing." |

Also settle **what is not the artifact**. Research notes, scratch dirs, vendored clones,
and logs live in the repo but must be out of scope for every rule, or the gate spends
its life flagging provenance.

## 2. What language, and what is pinned?

> "What language and runtime? And is that a decision or a default?"

Ask for versions, and write them down: runtime, package manager, and every tool the gate
will invoke. An unpinned toolchain means the gate's verdict changes under you.

Two follow-ups that matter:

- **"Is there more than one language here?"** Most repos have a second one hiding —
  scripts, examples, config, a docs site. Each gets judged separately, and the gate
  needs a path list per language.
- **"Are dependencies allowed, and who decides?"** "Standard library only" is a real
  and often correct answer for examples and tooling. If additions are allowed, require
  one line of justification per dependency.

## 3. What can a machine check?

Walk the layer list out loud and get a yes/no plus a threshold on each. Do not accept
"the usual" — the usual is different in every ecosystem.

| Layer | The question | A sharp answer |
|---|---|---|
| Types | Is there a checker, and in what mode? | `ty check`, no suppressions |
| Lint | Which rule set, and which ignores? | wide select, 3 ignores, each justified |
| Format | Who owns formatting? | the formatter; it exits the review entirely |
| Tests | What must be covered, by name? | the enumerated behavior list |
| Coverage | What number, measured how? | ≥85% lines, in-process only |
| Structure | What shape must files have? | frontmatter keys, layout order, budgets |
| Portability | What must never ship? | absolute paths, names, credentials |

For each ignore or exemption, ask **"what spec clause forces that?"** An ignore with a
reason is a decision; an ignore without one is drift that will grow.

**When the artifact has no compiler** — prose, config, data, a docs site — this is the
question that saves the project. The answer is not "nothing." Write a small checker
instead: does the frontmatter parse, do the links resolve, is anything orphaned, does
anything machine-tied ship. See `rig-cookbook.md`.

## 4. What can't a machine check — and what is each one's budget?

> "What do you care about that no tool can see?"

Typical answers: readability, comment discipline, naming, layout order, whether the
tests read as documentation, whether an explanation is honest about uncertainty.

Then, for **every single one**: **"What stops someone from over-applying this?"**

This is the rule that gets skipped and it is the one that bites. An unbounded prose
rule gets maximized rather than satisfied. Real case: "all fixed values in one named
constants block" produced a 90-line wall in which 43 of 57 constants were used exactly
once — the rule was followed perfectly and cost the solution its readability score.

Bound each rule by count, by scope, or by a stop condition:

- "at most one doc comment per function, plus one inline comment for the genuinely
  non-obvious"
- "name a literal only when it is shared across two or more sites, or genuinely cryptic"
- "`SKILL.md` body ≤ 80 lines; anything that is not routing goes in a reference"

If the owner cannot state a bound, the rule is not ready. Drop it or reshape it.

## 5. What are the error paths, the empty case, and the ties?

> "What happens when the input is malformed? When a dependency is missing? When the
> answer is zero results?"

Unspecified edges are where implementations diverge and where the real bugs live. Pin,
explicitly:

- **Malformed input** — and at what granularity it degrades. Does one bad element drop
  itself, or its whole batch? Say which.
- **Missing dependency** — removes what, exactly? Usually less than people assume.
- **Zero results** — the exact message, and whether requested output files are still
  written. This case is skipped more than any other.
- **Exit codes** — usage error vs. partial failure vs. success.
- **Ordering and ties** — and *at what precision* things count as equal. "Sorted newest
  first" is silent about ties; "equal at whole-second output precision, then by name
  ascending" is a total order recoverable from the output alone.
- **Environment inputs** — anything read from `PATH`, `HOME`, env vars, or the clock is
  an input. Name it, or two correct runs will disagree and nobody will know why.

## 6. What is out of scope, and what is guaranteed read-only?

> "What must this never do?"

Read-only guarantees ("only reads the filesystem, never installs or modifies") belong in
the contract because they are the promise a reviewer checks first. Non-goals belong there
because scope creep is easiest to refuse in writing.

## 7. Who enforces it, and when?

> "When does the gate run — on demand, on commit, in CI, or all three?"

Collapse to **one command**. If the answer has two commands in it, the second one will
be the one nobody runs. Then decide:

- Pre-commit hook, and on which paths.
- CI, and on which branches.
- Whether the gate is a merge requirement or advisory. Advisory gates decay.

## 8. What does the gate say today?

Run it. Record the result verbatim in the contract as the baseline, before any fixing.

> "This is what the contract says about the repo as it stands. Nothing is fixed yet —
> that's the next job, and it's deliberately separate."

A baseline measured after remediation tells you nothing. And a baseline that turns out
to be clean on the first run usually means the gate is too weak — go back to question 3.

---

## Closing the interview

Play the whole thing back in the owner's own words before writing anything: artifact,
languages, gate steps in order, prose rules with their budgets, error paths, scope.
Ask for one correction. There is almost always one, and it is almost always in question
1 or question 5.
