# Decisions (ADRs)

_One Architecture Decision Record per decision that shapes the build — what was decided,
why, and what it affects — so a choice made once isn't silently re-litigated._

Status: active

## Convention

- One file per decision: **`decisions-NNN-kebab-title.md`** (zero-padded, sequential). Start from
  [`0000-template.md`](0000-template.md).
- **Append-only.** Never renumber or delete an ADR. Two distinct mechanisms, by what changed:
  - **Supersession** — the *decision* changed: write a new ADR, set the old one's status to
    `Superseded-by-decision-NNN`, leave its text for provenance.
  - **Correction (erratum)** — a *factual premise* was wrong (the decision may still stand):
    add a dated `> **Correction (YYYY-MM-DD):** …` callout at the top citing the evidence,
    strike the false sentence inline (`~~…~~`) with a pointer to the callout. Status reads
    `Accepted (corrected YYYY-MM-DD)`. A falsified claim is never left readable as current
    truth.
- **Status lifecycle:** `Proposed` → `Accepted` / `Rejected` / `Superseded-by-decision-NNN`.
  A `Proposed` ADR is a ballot — it states the recommendation and the open question.
- The doc or code where the decision binds carries a short `Decision: decision-NNN` reference;
  the ADR links back. Link, don't copy.

## Log

| ADR | Decision | Status | Raised by |
|---|---|---|---|
<!-- | [001](decisions-001-…md) | … | Accepted | … | -->
