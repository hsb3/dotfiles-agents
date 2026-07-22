# Synthesis — the cited-report skeleton

Depth for phase 5. The output is not a summary of what you read; it is an **auditable** answer —
a reader can follow any load-bearing sentence back to the source that supports it and see how
confident you are in it. Optimize for that: per-claim provenance, confidence labels inline, and
negative findings kept.

## Ordering principle

Rank by **confidence, then load-bearing weight** — never by how interesting a claim is. The
verified core leads; contested and unverified material follows in clearly-labeled sections; a
vivid unverified claim never outranks a dull verified one. The reader should be able to stop after
the executive summary and have the trustworthy answer.

## The skeleton

```markdown
# Research report: <one-line question>

**Question (as scoped):** <the single refined question from phase 0, verbatim>
**Scope boundary:** <what was in / out of scope>
**Date of research:** <YYYY-MM-DD>  ·  **Data recency cutoff:** <how current the sources are>
**Confidence in overall answer:** <high | medium | low> — <one line why>

## Executive summary
3-6 sentences that answer the question directly, using only `verified` findings. If the honest
answer is "it depends" or "the evidence is mixed", say so here — a hedged true answer beats a
confident false one. No claim appears here that is not defended below.

## Findings

### Verified
- **<finding stated as a claim>.** `verified`
  Sources: [<publisher>](https://<source-url>) (<date>); [<publisher>](https://<source-url>) (<date>)
  <one line of context or the specific number/quote, if useful>

### Contested
- **<the claim>.** `contested`
  One side: [<publisher>](https://<source-url>) says <...>. Other side: [<publisher>](https://<source-url>) says <...>.
  <why they disagree, and which is better-sourced, if you can tell>

### Unverified (reported, not asserted)
- **<the claim>.** `unverified` — <why it could not be confirmed: single source / not checkable>
  Source: [<publisher>](https://<source-url>) (<date>)

## Negative findings
What was investigated and did NOT hold up — the results a shallow search omits. Keep these.
- **<claim that was refuted>.** `refuted` — contradicted by [<publisher>](https://<source-url>): <what it says>.
- **<thing searched for and not found>.** No credible source located for <X> across
  <which angles> — noted so the absence is on the record, not silently dropped.

## Limitations & open questions
- Angles that came up thin: <...>
- Sources you could not access: <paywalled / offline / not found>
- Recency cutoff and what may have changed since: <...>
- Questions the research did not resolve: <...>

## Sources
Full list, grouped by tier (primary / established secondary / other), each with its URL and date.
This is the bibliography; the per-claim links above are what make it auditable.
```

## Rules that make the report defensible

- **Per-claim provenance, at the URL level.** Every load-bearing statement carries its own
  source link(s) inline — not one bibliography at the bottom the reader cannot map to sentences.
  If a sentence has no citation, it is either common knowledge or it does not belong.
- **Label inline.** The confidence label rides next to the claim (`verified` / `contested` /
  `unverified` / `refuted`), so a skimming reader sees the certainty without hunting for a
  footnote.
- **Merge duplicates, keep sources.** When two claims say the same thing, collapse to one row and
  carry *all* their independent sources — that is what earns the higher confidence. Keep
  genuinely distinct claims separate even when they sound similar.
- **Negative findings are mandatory, not optional.** A report with an empty negative-findings
  section almost always means the adversarial phase was skipped. "We looked for X and found no
  support" and "Y was widely repeated but refuted by [primary source]" are among the highest-value
  lines in the whole document.
- **State the overall confidence honestly.** If the verified core is thin, the headline
  confidence is `low` and the summary says why. Do not let a long sources list imply a certainty
  the verification did not earn.
- **No unlabeled load-bearing claim, anywhere.** This is the same invariant as verification,
  enforced one last time at write-time: read the draft and confirm every consequential sentence
  has both a citation and a label.

## Sizing

Match the report to what phase 0 scoped. A "quick scan" answer may be the executive summary plus a
short verified-findings list and sources — the *discipline* (per-claim citation, labels, negative
findings) is non-negotiable even when the length is small. An "exhaustive report" fills every
section. Do not pad a thin evidence base into a long document; length should track the evidence,
not the ambition.
