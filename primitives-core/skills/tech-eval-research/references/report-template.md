# Report template

Save as markdown in the user's folder, named `{topic-slug}-{YYYY-MM-DD}.md`. Open with the title, the one-line framing of the decision, the research date, and a note that all claims are point-in-time from primary sources with adversarial verification of decision-critical claims (include the tally).

## 1. Executive summary (≤200 words)

Which candidates clear both the hard filters and the maturity bar, the single best fit for the user's specific context, and the one-line reason. Name the confirmed failure of any baseline/incumbent the user was escaping.

## 2. Comparison matrix

Candidates as rows, evaluation axes as columns. Required columns: candidate + layer tag, license type (+ OSI or equivalent filter status), hard-filter verdict (Pass / Fail — reason), one column per checklist capability, secondary axes (observability, ecosystem fit, integration effort), maturity verdict, and an overall "required features paywalled?" column.

Legend (state it above the table):
✅ Yes, free/OSS · ◐ Partial (see note) · 💰 Paywalled · ❌ No (confirmed) · ❓ Not documented

Use numbered footnotes below the table for every ◐ and for any cell whose one-word verdict hides a decision-relevant nuance. The footnotes are where the evaluation earns its keep — a matrix without them is a listicle.

Order rows: passing candidates by rank, then near-misses, then fails (including the baseline). Keep failed candidates in the matrix with their failure reason — the reader needs to see *why* the field narrowed.

## 3. Per-candidate profiles (shortlist + notable near-misses)

One paragraph each: what it is and what layer it operates at → the maturity evidence (actual numbers: stars, contributors, release cadence, downloads, adopters) → the standout strength → the honest caveat(s) → integration effort with the user's stack. Never a strength without its caveat.

## 4. Rejected candidates

Everything considered and cut, one sentence each with the failure category: fails hard filter (say which) / SOURCE-AVAILABLE (name the license) / SaaS-only / wrong layer / abandoned-deprecated / immature. Every candidate from the seed set must appear somewhere in §2–§4.

## 5. Recommendation & caveats

- The recommended option(s) for this specific context, and what to prototype first (concretely — the fastest path to a validating proof).
- If no single candidate covers everything, say so and recommend the composition.
- Top 2–3 risks to validate before committing (bus factor, integration drift, backlog trend, pin-version risk...), each with a mitigation.
- **State the bias**: which axes this research deliberately weighted (e.g., license purity over vendor support) so the reader can discount for their own priorities.

## 6. Sources

Primary sources grouped by candidate, each with what it supports; state the date checked once at the top if uniform. Close with a method note: where the maturity numbers came from, and the "No vs Not documented" discipline used.

---

# Deck spec (only when requested)

Follow the pptx skill for construction. Structure (~10–13 slides):

1. Title — topic, date, the one-line framing.
2. **First content slide: the recommendation.** Single option, named, with 4–6 rationale points drawn from the report and a small honest-caveats strip. If there's a fallback option, one line at the bottom. This slide leads because executives read one slide.
3. Why this research exists — the failure mode or decision pressure that triggered it.
4. Method — hard filters, capability checklist, maturity bar, verification tally.
5. Results overview — who passed.
6. Condensed comparison matrix (shortlist rows only; symbols + legend; this is the densest slide — table, minimal footnotes).
7–n. One profile slide per shortlisted runner-up (stats strip + wins + honest caveats).
n+1. Notable fails, grouped by which bar they missed.
n+2. Recommended path forward (sequence: prototype → scale choice → conditional options).
n+3. Risks to validate + stated bias.

Always QA before delivery: render every slide to an image, view each one, fix overflow/overlap/broken glyphs, re-render to confirm. An independent reviewer pass (subagent) that also fact-checks the recommendation and matrix slides against the report catches what the builder can't see.
