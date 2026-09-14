---
name: deep-research
description: >-
  Run a deep, multi-source, fact-checked research investigation that ends in a cited report,
  not a single web lookup. Use when the user asks to "research X", "do a deep dive on",
  "find out everything about", "investigate", "compare the options for", "what's the state of
  the art on", or "give me a report with sources" — or poses a broad, open-ended question that
  one search cannot settle and that needs several sources cross-checked against each other.
  Runs the pipeline scope -> decompose into angles -> fan out searches -> dedupe and fetch
  sources -> extract falsifiable claims -> adversarially verify each load-bearing claim ->
  synthesize a confidence-ranked, per-claim-cited report that keeps negative findings. Prefer
  it over an ad-hoc search whenever being wrong is costly or the answer must be defensible.
---

# Deep Research

Turn a fuzzy question into a **defensible, cited answer**. The value of this skill is not
finding pages — a single search does that — it is *disproving* what you find. Most of the
effort goes into scoping the question tightly, pulling from several independent angles, and
then actively trying to refute every load-bearing claim before it earns a place in the report.
A claim that no one tried to refute is a rumor with a footnote.

This skill is self-contained. Run it top to bottom; reach for the two references only where
noted for depth.

## The pipeline at a glance

| Phase | Do | Output |
| --- | --- | --- |
| 0. Scope | Confirm the question is answerable; narrow it if not | A single, specific research question |
| 1. Decompose | Split the refined question into ~5 distinct search angles | An angle list, each with a purpose |
| 2. Fan out | Search each angle (parallel subagents if available, else serial) | Raw hits per angle |
| 3. Sources | Dedupe URLs, triage, fetch the top sources, extract falsifiable claims | A claim ledger, each claim source-attributed |
| 4. Verify | Try to refute each load-bearing claim independently; label the survivors | Verdict + confidence per claim |
| 5. Synthesize | Merge duplicates, rank by confidence, write the cited report | A report with per-claim provenance |

The phases are ordered but not one-way: a verification failure in phase 4 or a thin source in
phase 3 can send you back to add an angle (phase 1) or re-search (phase 2). Budget for one such
loop; deep research that never revisits its angles usually missed the real question.

## Phase 0 — Scope before you search

Default scope is the single refined question the user actually asked, never the widest
reading of it — never infer a sprawling multi-subject investigation from a general request;
widen only when the user explicitly asks for broader coverage.

**Do not research an underspecified question.** A vague prompt fans out into vague searches and
a report that answers a question no one asked. Before anything else, judge whether the question
is specific enough to have a *checkable* answer.

A question is ready when you can name: the **subject**, the **decision or output** it feeds, the
**time frame** (current state vs history vs forecast), and the **boundary** (what is explicitly
out of scope). If any of those is missing or ambiguous, **stop and ask 2–3 clarifying
questions** — no more. Pick the questions whose answers would most change how you search:

- Scope boundary — "Should this cover only [X], or also [adjacent Y]?"
- Intent — "Are you deciding between options, or building a background briefing?"
- Freshness — "Do you need the current state as of today, or the historical arc?"
- Depth/format — "A quick scan of the top sources, or an exhaustive, heavily-cited report?"

Offer a **recommended default** with each question so the user can answer by approving, not
composing. If the user says "just go", or the question is already specific, skip straight to
phase 1 — over-interrogating a clear request is its own failure. Record the refined question in
one sentence and treat it as the contract for everything downstream.

## Phase 1 — Decompose into ~5 angles

Break the refined question into **about five distinct search angles** — enough to triangulate,
few enough to stay deep on each. Angles are *different directions of attack*, not paraphrases of
the same query. Good angle sets mix these lenses:

- **Definitional / foundational** — what the thing is, canonical sources, primary documents.
- **Current state** — the latest developments, releases, or data, deliberately biased to recency.
- **Comparative** — alternatives, competitors, the field around the subject.
- **Critical / adversarial** — failures, criticisms, limitations, "problems with [X]", "[X]
  debunked". This angle is not optional: it is where refuting evidence lives.
- **Quantitative / evidential** — benchmarks, studies, primary data, numbers you can cite.

Write each angle as a one-line purpose plus 1–2 concrete queries. Five sharp angles beat ten
overlapping ones. If the question is narrow, three angles may be enough; if it is sprawling,
prefer adding an angle over cramming two questions into one. `references/search.md` has angle
patterns and query-crafting detail.

## Phase 2 — Fan out the searches

Search every angle. **Parallelize when the harness lets you, degrade gracefully when it does
not** — the workflow is identical either way, only the concurrency changes:

- **Parallel path (preferred).** If the harness offers subagents (a Task/Agent-style tool),
  dispatch **one read-only search agent per angle in a single batch** so they run concurrently.
  Brief each with: the one refined question (for context), *its* angle and queries, and the
  return format — a list of `title | url | one-line relevance | publication date if known`. Tell
  each agent to return raw hits and short quotes, **not** conclusions; judging is your job, and a
  sub-agent's summary is a hypothesis, not a finding.
- **Serial path (fallback).** If there are no subagents, run the angles yourself one at a time
  with the web-search tool, keeping the same per-angle notes. Slower, same result. Do not skip
  angles to save time — the critical/adversarial angle is the one most often dropped and the one
  that most changes the answer.

Collect all hits into one working list, tagged by the angle that found them. Keep going until
angles start returning the same URLs — **saturation** (repeated sources across independent
angles) is the signal you have enough breadth to move on.

## Phase 3 — Sources: dedupe, fetch, extract claims

Now convert pages into a **claim ledger**.

1. **Dedupe URLs.** Normalize before comparing: lowercase host, drop `www.`, strip tracking
   query params (`utm_*`, `ref`, `fbclid`, session ids) and fragments, collapse trailing
   slashes. Treat AMP/mobile/mirror variants of the same article as one. Dedup by normalized URL
   first, then by title+publisher for the same story syndicated across domains.
2. **Triage, then fetch the top sources.** You cannot read everything — rank by likely value
   (primary source > established outlet/official docs > secondary reporting > aggregator > SEO
   filler) and **prefer independent origins**: three domains reprinting one wire story are one
   source, not three. Fetch the full text of the top sources per angle with the harness fetch
   tool; skim the rest by snippet.
3. **Extract falsifiable claims.** From each fetched source, pull out the **specific, checkable
   assertions** — a claim that could in principle be shown false ("Model Y scores 82% on
   benchmark Z", "the API deprecates the field in version 4"). **Discard the unfalsifiable**
   (marketing adjectives, vibes, "widely regarded as best"). Record each claim with its **source
   attribution**: the exact URL, the publisher, the date, and a short verbatim quote. One row per
   claim. This ledger — claim, source, quote — is the unit everything downstream operates on.

Flag each claim's weight as you record it: **load-bearing** (the report's conclusion depends on
it) or **supporting** (context). Phase 4 verifies the load-bearing ones hardest.

## Phase 4 — Adversarial verification

This is the phase that separates research from search. **Every load-bearing claim gets
independent attempts to refute it** — you are not confirming the claim, you are trying to break
it. Confirmation bias is the default failure mode; the refutation framing is the fix.

For each load-bearing claim, run independent refutation attempts (parallel subagents if
available, else serial passes), each briefed to *find evidence the claim is false or
overstated*: search for contradicting primary sources, newer data that supersedes it, the
original context the quote was lifted from, and known corrections/retractions. Then apply the
verdict rule:

- **Majority of independent attempts refute it → the claim is killed.** It does not go in the
  report as fact. It becomes a *negative finding* (see phase 5) — "claim X was investigated and
  contradicted by [sources]" — never a silent deletion.
- **A minority refute / sources genuinely disagree → contested.** Report it with both sides and
  the disagreement made explicit.
- **No refutation survives and ≥2 independent sources support it → verified.**
- **Cannot be independently checked either way → unverified.** Keep it, but **label it
  `unverified` in the report** — an unverifiable claim is never laundered into an asserted fact.

The confidence labels, the refutation-agent brief template, and how to weight source
independence are in `references/verification.md`. The one rule to carry without the reference:
**nothing enters the report unlabeled.** Verified, contested, unverified, or refuted — every
load-bearing claim wears its verdict.

## Phase 5 — Synthesize the cited report

Assemble the ledger of verdicts into a report the reader can trust *and audit*.

1. **Merge semantic duplicates.** Collapse claims that say the same thing in different words into
   one, carrying **all** their sources (more independent sources → higher confidence). Keep
   genuinely distinct claims separate even when they rhyme.
2. **Rank by confidence, not by how interesting the claim is.** Lead with the verified core;
   demote contested and unverified material to clearly-labeled sections. Never let a vivid
   unverified claim outrank a dull verified one.
3. **Cite at the URL level, per claim.** Every load-bearing statement in the report carries its
   own source link(s) and its confidence label inline — not one bibliography at the bottom that
   the reader cannot map back to specific sentences. Provenance is per-claim.
4. **Keep the negative findings.** Report what you looked for and did **not** find, and every
   claim the verification phase refuted. "No credible source supports [X]" and "[Y] was widely
   repeated but contradicted by [primary source]" are among the most valuable outputs of deep
   research — they are the results a shallow search silently omits. A report with no negative
   findings usually means the adversarial phase was skipped.
5. **State the limitations.** Name the angles that came up thin, the sources you could not
   access, the recency cutoff of your data, and the questions that remain open.

The full report skeleton — front matter, executive summary, confidence-labeled findings, the
per-claim provenance table, negative-findings and limitations sections — is in
`references/synthesis.md`.

## The non-negotiables

Carry these into every phase; they are why this produces a defensible answer rather than a
plausible one:

- **Scope before search.** An underspecified question gets 2–3 clarifying questions first, each
  with a recommended default — never a fan-out into fog.
- **Refute, don't confirm.** Load-bearing claims are attacked, not checked. Majority-refute kills
  a claim; the kill is reported as a negative finding, not deleted.
- **Nothing enters the report unlabeled.** Verified / contested / unverified / refuted — every
  load-bearing claim wears its verdict, and citations are per-claim at the URL level.
- **Source independence is the currency.** N domains reprinting one origin count as one source;
  confidence comes from *independent* corroboration, not from repetition.
- **Sub-agent output is a hypothesis.** Searchers return hits and quotes; refuters return
  evidence. The judgment — what is true, what is load-bearing, what makes the report — stays with
  you and is re-derived from the cited source, never inherited from an agent's summary.
- **Negative findings are findings.** What you searched for and did not find is reported, not
  dropped. Absence of evidence, stated plainly, is a result.

## References

- **`references/search.md`** — angle patterns, query crafting, the parallel-vs-serial fan-out,
  source triage and URL-dedupe rules in full.
- **`references/verification.md`** — the adversarial refutation protocol: the confidence-label
  taxonomy, the refutation-agent brief template, the majority-refute verdict rule, and source
  independence weighting.
- **`references/synthesis.md`** — the cited-report skeleton with per-claim provenance, negative
  findings, and limitations.
