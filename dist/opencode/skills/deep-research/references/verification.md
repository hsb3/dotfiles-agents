# Verification — the adversarial refutation protocol

Depth for phase 4. Search finds claims; verification tries to **break** them. The premise: a
claim that survived a genuine attempt to disprove it is worth far more than a claim that was
merely re-confirmed, because confirmation bias makes re-confirmation nearly free and nearly
worthless. You are the claim's adversary, not its advocate.

## What gets verified, and how hard

Every **load-bearing** claim (the report's conclusions depend on it) gets the full refutation
treatment below. **Supporting** claims get a lighter touch — a single sanity check against one
independent source — unless a load-bearing claim turns out to rest on one, at which point it is
promoted and re-verified. Do not spend the budget verifying claims that change nothing.

## The refutation attempt

For each load-bearing claim, run **independent refutation attempts** — parallel subagents if the
harness offers them, otherwise serial passes you run yourself. Each attempt is briefed to *falsify*,
not confirm:

```
CLAIM UNDER TEST: "<the exact claim>"
ORIGINAL SOURCE: <url> (<publisher>, <date>) — quote: "<verbatim>"
YOUR JOB: try to prove this claim FALSE or OVERSTATED. Specifically hunt for:
  - primary sources that directly contradict it
  - newer data that supersedes or revises it
  - the original context the quote was lifted from (was it qualified, hedged, or hypothetical?)
  - corrections, retractions, or errata on the original source
  - methodology flaws if it is a study/benchmark (sample, date, conflict of interest)
RETURN: verdict for THIS attempt — refuted | not-refuted | inconclusive —
  with the contradicting source url + verbatim quote if you found one.
Do not defend the claim. If you cannot break it after a real attempt, say not-refuted.
```

Run **at least two independent attempts** per load-bearing claim (three when the stakes are
high). Independence matters: attempts that all lean on the same source, or the same search query,
are one attempt wearing three hats. Vary the query framing and steer each attempt toward a
different class of source (primary, adversarial-angle, quantitative).

## The verdict rule

Aggregate the attempts into one verdict:

| Aggregate of independent attempts | Verdict | What happens |
| --- | --- | --- |
| Majority **refute** it | **refuted** | Claim is killed. It does **not** appear as fact — it becomes a negative finding: "claim X was investigated and contradicted by [sources]". Never a silent deletion. |
| Attempts split / sources genuinely disagree | **contested** | Reported with both sides, the disagreement made explicit, and the strongest source on each side named. |
| None refute AND ≥2 **independent** sources support | **verified** | Enters the report as a supported finding with its label. |
| None refute but only one source, or it cannot be checked either way | **unverified** | Kept, but labeled `unverified` in the report. Never laundered into an asserted fact. |

"Majority" is over the **independent** attempts, not raw agent count — three attempts that shared
a source count as one. When in doubt between two verdicts, choose the more cautious one
(contested over verified, unverified over verified).

## Confidence labels

Every load-bearing claim wears exactly one label in the report:

- **`verified`** — survived refutation; corroborated by ≥2 independent origins. Safe to state as
  a finding.
- **`contested`** — credible sources disagree. State the disagreement, not a false resolution.
- **`unverified`** — could not be independently checked, or rests on a single source. Reported,
  but flagged so the reader weights it accordingly.
- **`refuted`** — refutation succeeded. Reported as a negative finding, with the contradicting
  evidence, so the reader knows a plausible-sounding claim was tested and failed.

The invariant: **nothing enters the report unlabeled.** An unlabeled claim reads as fact, and
half of them are not.

## Source independence — the currency of confidence

Confidence comes from *independent* corroboration, never from repetition. Before counting two
sources as corroboration, check they do not collapse into one:

- **Syndication.** Many outlets reprinting one wire story, press release, or upstream report are
  **one** origin. Trace the byline/dateline to the source.
- **Citation chains.** Source B whose only evidence is "according to source A" is not independent
  of A. Follow the chain to its root and count the root once.
- **Shared funding / authorship.** Two "studies" from the same lab, sponsor, or author with a
  stake are correlated, not independent — note the conflict.
- **Circular references.** A and B each cite the other with no external grounding is a closed loop
  with zero independent support; treat the claim as unverified until an outside source appears.

Weight primary sources above secondary, recent above stale (for time-sensitive claims), and
disinterested above conflicted. Two genuinely independent primary sources outweigh ten reprints
of a single blog post.

## Common failure modes to guard against

- **Confirming instead of refuting** — searching "[claim] is true" finds agreement every time.
  Always frame the attempt as falsification.
- **Quote out of context** — the source said it, but hedged, dated, or hypothetically. Reading the
  surrounding paragraph is a refutation attempt in itself.
- **Stale-as-current** — a once-true claim superseded by newer data. The current-state angle and a
  date check catch these.
- **Manufactured consensus** — ten pages agreeing because they copied one source. Independence
  weighting is the antidote.
- **Precision theater** — an oddly specific number ("73.4%") with no traceable methodology behind
  it. Demand the primary; if there is none, it is unverified at best.
