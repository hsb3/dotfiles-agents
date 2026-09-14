# Worked examples

Two real contracts. One governs a program, one governs a documentation artifact. They
are here for their mistakes as much as their shape — both were wrong in instructive ways
on the first pass, and both were corrected by the gate rather than by review.

---

## A — A program: three implementations, one spec

**Artifact.** A read-only package-inventory CLI, built independently in TypeScript, Go,
and Python from a single prose spec, each inside a frozen toolchain.

**Gate.** One command per language (`bun run check`, `make check`), each running
typecheck → lint → format → tests with a ≥85% line-coverage floor.

**What the contract got right.** It treated error paths as first-class: missing binary,
malformed JSON, unreadable path, and the zero-result case each had named behavior. It
declared `PATH` and `HOME` as inputs, so two "correct" runs producing different rows was
understood rather than debugged.

**What it got wrong first, and how that surfaced.** Three implementations of one spec are
a three-way fuzzer of the spec. Wherever they disagreed, the contract had been silent.
Revision 2 pinned six such holes:

| Hole | The silence |
|---|---|
| Cellar path | spec said "name"; the data has both `name` and `full_name`, and a tapped formula's directory uses the short one |
| Invalid flags | no exit code specified, so each language picked its own |
| Manager binary absent | unclear whether that removed the whole collector or only the data it contributed |
| Sort ties | "newest first" is silent about equal timestamps |
| Empty results | unclear whether requested output files were still written |
| Line endings | CSV unspecified, so platforms differed |

The tie-break needed a second sharpening even after being written down: "equal
timestamps" had to become "equal **at output precision** (whole seconds)", because raw
sub-second `stat` precision was leaking into row order and making the output
irreproducible from the output alone.

**The lesson.** The places a contract goes silent are not exotic. They are ties,
emptiness, absence, and precision. Ask about those four directly (interview question 5)
rather than waiting for implementations to disagree.

**The other lesson.** One prose rule in that contract said all fixed values live in a
named-constants block, with no bound. It was followed exactly: 57 constants, 43 of them
used once, a 90-line wall that cost the solution the readability score the rule existed
to protect. An unbounded rule gets maximized, not satisfied.

---

## B — A documentation artifact: no compiler at all

**Artifact.** An agent skill — a `SKILL.md` router, ten deep references, five runnable
Python examples — destined for a governed marketplace repo.

**The hard question.** Markdown has no compiler, so every guarantee a compiler would give
was simply absent: nothing checked that the frontmatter parsed, that routing targets
existed, that nothing was orphaned, that nothing machine-tied shipped. The answer was to
write those checks, about 250 lines of stdlib Python, rather than accept "you can't gate
prose."

**Gate.** `make check` → structural checker → `ty check` → `ruff check` →
`ruff format --check`.

**What the gate caught that reading had not.** Five portability violations, including a
home-directory absolute path inside a config example and a "…'s setup does this" aside
naming a person — both of which would have failed the destination repo's own identity
lint on the day of promotion. It also caught an ordinary prose phrase, a word followed by
a hash and a single digit, which the destination's issue-reference pattern reads as a
ticket number. That one looks like a false positive and is not: the destination would
reject it, so the local gate must too.

That rule bites the author of this very file, which is the point. Describing a banned
string still ships the banned string, so a reference that documents portability rules has
to *describe* the shape rather than reproduce it.

Then `ty` found what no amount of reading had: `subprocess.Popen.stdin` is
`IO[str] | None`, so every `p.stdin.write(...)` in the shipped examples was an unchecked
`None` dereference. Eight of them, in code that had been read carefully several times.

**Three mistakes in building it, all worth stealing.**

1. **The first gate had a rule that would have made the artifact worse.** It required
   one-line module docstrings; three examples had multi-line docstrings that explained
   the protocol and were the best thing about them. The rule was wrong, not the files.
   It became "a summary line ≤ 100 chars, then a blank line, then as much body as you
   like." When a gate and a good artifact disagree, one of them is wrong — decide which,
   out loud, rather than defaulting to either.

2. **The checker failed its own gate.** Thirty lint violations, all in the enforcement
   script. It was rewritten in the style it demanded. A checker exempt from its own
   standard teaches everyone that the standard is optional.

3. **The first baseline reported a defect that the measuring had created.** An earlier
   byte-compile check had written `__pycache__/` into the artifact, which the clean-tree
   rule then dutifully flagged. Reporting it would have been a fabricated finding.
   Check whether a defect predates you before you write it into a baseline.

**One more.** The project's own handoff notes said "seven Mermaid diagrams" in two
places. There are nine. Nobody had counted since the day they were written. A gate that
counts is worth more than a note that asserts.

---

## What both have in common

- The contract was written **before** the work was judged, and revised when the work
  proved it incomplete. Revision history is part of the document.
- The gate is **one command**, and it is the same command in CI, in the hook, and in the
  builder's head.
- The baseline was **measured before remediation** and recorded verbatim, failures and
  all. Both contracts open their status section with some variant of "this is the
  starting state, not a passing grade."
- Configuration is **read-only** to whoever builds against it, with the standing
  instruction: if a gate looks impossible, report it rather than loosening it.
