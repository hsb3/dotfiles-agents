# <project> — build contract and quality gate

<!--
  Copy to RULES.md at the repo root. Replace every <angle-bracket> placeholder and
  delete every HTML comment. Sections 1-3 answer the three questions in order: what,
  in what language, checked how. Do not reorder them — the language choice is
  downstream of the artifact, and the gate is downstream of both.
-->

This repo produces <one artifact, named>. This file is the contract it is built
against: what we are building, what language we are writing it in, and exactly which
quality checks are machine-enforced before it ships.

The rig (<list the config files>) is provided by the contract, not by the author:
**configuration files are read-only.** If a gate looks impossible to satisfy, report it
rather than loosening it.

---

## 1. What we are building

<One paragraph. What comes out of this repo, and what its job is.>

<A table of the artifact's parts and each one's role, if it has parts.>

<What is explicitly NOT the artifact: research notes, scratch dirs, vendored clones,
logs. State that these are out of scope for every rule below, or the gate will spend
its life flagging provenance.>

The success condition is not "<the obvious but uncheckable one>". It is:
**<the condition someone could actually verify>.**

## 2. Languages and runtimes

<One paragraph per language. For each: why it, what version, what is pinned, and what
the dependency policy is. Name the second language — scripts, examples, config, docs —
if there is one; most repos have one hiding.>

Tooling is pinned: **<tool version>**, **<tool version>**.

## 3. The gate

One command, run from the repo root:

```
make check
```

which enforces, in order:

1. **<structural / contract check>** — <what it enforces, by rule number>. Exit 0
   clean; exit 1 prints every violation, not the first.
2. **<typecheck>** — <mode, and what escape hatches are banned>.
3. **<lint>** — <rule selection>. <Every ignore, with the spec clause that forces it.>
4. **<format --check>** — formatting is the formatter's domain and is not a judged
   style dimension; run `make fmt` freely.
5. **<tests>** — <what must pass, and the coverage floor and how it is measured>.

<State whether the rig's own code is inside the lint scope. It should be: a gate that
cannot pass itself is advice, not law.>

`make check` is the whole gate. <Say where else it runs: pre-commit hook, CI, merge
requirement.>

**Proven both ways on <date>:** green on the tree as recorded in §7, and red when
sabotaged — <one broken rule per gate step, and which step caught it>.

---

## 4. Rules

<!--
  Number them R1..RN and keep the numbers stable across revisions; the gate's output
  cites them. Sort machine-enforced rules first. EVERY prose rule needs a budget or a
  stop condition — an unbounded rule gets maximized, not satisfied.
-->

**R1 — <name>.** <The rule. If it is prose-enforced, its budget or stop condition, in
the same paragraph.>

**R2 — <name>.** <...>

## 5. Behavioral spec

<What the artifact must do. For a program: inputs, outputs down to column order and
exact terminal messages, flags, exit codes. For a documentation or config artifact: the
behavior it must produce in whoever reads it.>

**Error paths — first-class, not edge cases.**

| Situation | Required behavior |
|---|---|
| Malformed input | <degrades at what granularity — the element, or the batch?> |
| Missing dependency | <removes exactly what?> |
| Zero results | <exact message; are requested output files still written?> |
| Usage error | <diagnostic, and exit code> |
| Ties in ordering | <the tie-break, and the precision at which things count as equal> |

**Environment inputs.** <Anything read from PATH, HOME, env vars, or the clock. Two
correct runs will disagree otherwise, and nobody will know why.>

**Out of scope / read-only guarantees.** <What this must never do.>

## 6. Judging criteria (for the human evaluator)

<3-6 questions a reviewer asks that no gate can answer. These are what the prose rules
in §4 exist to serve.>

## 7. Baseline against this gate

Measured <date>, before any remediation. This is the starting state, not a passing
grade:

| Rule | Status |
|---|---|
| R1 <name> | pass / **fail** — <the specific finding, with a count> |

<If everything passes on the first run, the gate is probably too weak. Say so here
rather than declaring victory.>

Remediation is the next piece of work and is deliberately not done here: writing the
contract and satisfying it are separate jobs, and a baseline measured after fixing is
worthless.

## 8. Revision history

**Revision 1 (<date>)** — first contract. <What was decided and why.>

<!--
  Each later revision names the ambiguity it closes. A contract that never gets revised
  is not being used. The places contracts go silent are ties, emptiness, absence, and
  precision — expect revisions there.
-->
