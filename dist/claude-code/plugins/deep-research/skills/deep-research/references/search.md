# Search — angles, queries, fan-out, and source triage

Depth for phases 1–3 of the main flow. The spine tells you *what* to do; this tells you *how*.

## Decomposing into angles

An angle is a **direction of attack**, distinguished by the kind of source it is meant to
surface. Paraphrasing one query five ways is not five angles — it returns the same pages five
times. Aim for ~5 angles that a *different* class of source would answer:

| Lens | What it surfaces | Query shapes |
| --- | --- | --- |
| Definitional / foundational | Primary docs, canonical explainers, specs | "what is [X]", "[X] official documentation", "[X] specification" |
| Current state | The latest releases, data, developments | "[X] 2026", "[X] latest", "[X] release notes", date-filtered search |
| Comparative | Alternatives and the surrounding field | "[X] vs [Y]", "alternatives to [X]", "[category] landscape" |
| Critical / adversarial | Failures, limits, criticism, retractions | "problems with [X]", "[X] criticism", "[X] debunked", "[X] limitations" |
| Quantitative / evidential | Benchmarks, studies, primary numbers | "[X] benchmark", "[X] study results", "[X] statistics", "[X] dataset" |

**Rules of thumb.** Narrow question → 3 angles is fine; sprawling question → add an angle rather
than overloading one. The critical/adversarial angle is mandatory — it is where refuting evidence
lives, and dropping it is the most common way research turns into an echo chamber. Bias the
current-state angle toward recency explicitly (date filters, "latest", the current year) because
default search ranking favors popular-but-stale pages.

Write each angle down before searching:

```
Angle 2 — Current state
  purpose: find developments in the last ~12 months that supersede older summaries
  queries:
    - "[subject] 2026 update"
    - "[subject] latest release notes"
```

## Query crafting

- **One idea per query.** Compound queries ("X performance and pricing and alternatives") dilute
  ranking; split them.
- **Vary specificity.** Run a broad query for landscape, then narrow queries for the specifics it
  surfaces. Follow named entities (a product, a paper, a person) into their own queries.
- **Use the source's language.** Search the terms practitioners use, not the layperson gloss — a
  field's jargon is the fastest path to primary sources.
- **Chase primaries.** When a secondary source cites a study, paper, or dataset, search for *that*
  original and cite it instead of the retelling.

## Fan-out: parallel vs serial

The workflow is identical; only concurrency differs.

**Parallel (preferred, if the harness has subagents).** Dispatch one read-only search agent per
angle in a single batch so they run concurrently. Brief each agent with:

```
CONTEXT: The overall research question is: "<one-sentence refined question>".
YOUR ANGLE: <angle name + purpose>.
QUERIES: <the 1-2 concrete queries for this angle>.
RETURN: a list of hits, one per line:
  title | url | one-line why-relevant | publication date if visible
Return RAW hits and short verbatim quotes only. Do NOT synthesize conclusions,
do NOT rank across angles, do NOT decide what is true — that is the caller's job.
Note any query that returned nothing (a null result is useful).
```

**Serial (fallback, no subagents).** Run each angle yourself with the web-search tool, one at a
time, keeping the same per-angle notes. Same output, more wall-clock time. Never drop an angle to
save time — especially not the adversarial one.

**Stop condition — saturation.** Keep searching an angle until new queries return URLs you have
already seen. When independent angles start converging on the same handful of sources, you have
enough breadth; more searching past saturation is wasted. Conversely, if an angle returns only
thin or SEO-farm results, that thinness is itself a finding — note it for the limitations section
and consider whether the question needs re-scoping.

## Source triage and URL dedupe

Turn raw hits into a fetch queue.

**Dedupe first.** Normalize each URL before comparing:

- lowercase the host; drop a leading `www.`
- strip tracking query params (`utm_*`, `ref`, `fbclid`, `gclid`, session ids) and the `#`
  fragment
- collapse a trailing slash; treat `http` and `https` of the same path as one
- treat AMP / mobile (`m.`) / print variants of the same article as the same page

Then dedupe a second time by **title + publisher**: the same wire story syndicated across many
domains is *one* source. This second pass is what protects the confidence math downstream —
counting ten reprints as ten sources manufactures false certainty.

**Rank what survives.** Fetch budget is finite; spend it on the highest-value sources:

| Tier | Examples | Trust default |
| --- | --- | --- |
| Primary | Official docs, the actual paper/dataset, filings, source code, first-party statements | Highest — cite these directly |
| Established secondary | Reputable outlets, standards bodies, recognized domain experts | High, but check date and corrections |
| General secondary | Mainstream reporting, well-run community wikis | Medium — corroborate before load-bearing use |
| Aggregator / SEO | Content farms, listicles, auto-summaries, most "best X" pages | Low — mine for links to primaries, rarely cite |

**Prefer independent origins.** When ranking, favor sources that do not derive from each other —
three outlets reprinting one press release are one origin. Independence, not count, is what makes
corroboration meaningful (see `verification.md`).

**Fetch the top of the queue.** Pull full text for the highest-tier sources per angle with the
harness fetch tool; skim the rest by search snippet. Record, for every source you actually use,
the fields the claim ledger needs: URL, publisher, date, and the verbatim quote backing each
claim you extract.

## Extracting falsifiable claims

The output of phase 3 is a **claim ledger**, one row per checkable assertion:

```
claim | source_url | publisher | date | verbatim_quote | weight(load-bearing|supporting)
```

- **Falsifiable only.** Keep assertions that could be shown false — numbers, dated events,
  specific behaviors, named causal relationships. Drop the unfalsifiable — adjectives, sentiment,
  "widely regarded as", anything with no test that could fail.
- **One claim per row.** Split a sentence that bundles three assertions into three rows so each
  can be verified and cited independently.
- **Attribute exactly.** The quote must be verbatim and the URL must point to where it actually
  appears — not a homepage, not a search result. Attribution you cannot re-open is not
  attribution.
- **Mark weight now.** Tag each claim load-bearing (a conclusion rests on it) or supporting
  (context). The verification phase spends its budget on the load-bearing rows.
