# Decisions (ADRs)

_One Architecture Decision Record per decision that shapes the build — what was decided,
why, and what it affects — so a choice made once isn't silently re-litigated._

Status: active

## Convention

- One file per decision: **`NNNN-kebab-title.md`** (zero-padded, sequential). Start from
  [`0000-template.md`](0000-template.md).
- **Append-only.** Never renumber or delete an ADR. Two distinct mechanisms, by what changed:
  - **Supersession** — the *decision* changed: write a new ADR, set the old one's status to
    `Superseded-by-NNNN`, leave its text for provenance.
  - **Correction (erratum)** — a *factual premise* was wrong (the decision may still stand):
    add a dated `> **Correction (YYYY-MM-DD):** …` callout at the top citing the evidence,
    strike the false sentence inline (`~~…~~`) with a pointer to the callout. Status reads
    `Accepted (corrected YYYY-MM-DD)`. A falsified claim is never left readable as current
    truth.
- **Status lifecycle:** `Proposed` → `Accepted` / `Rejected` / `Superseded-by-NNNN`.
  A `Proposed` ADR is a ballot — it states the recommendation and the open question.

## Log

These are mirrors carried into the clean-room rebuild from the pre-rebuild tree (now
preserved at `dev-legacy`) — kept **verbatim**, numbers and titles unchanged, per D7. The
numbering has intentional gaps: **0004** and **0005** existed pre-rebuild but are not carried
(below).

| ADR | Decision | Status | Raised by |
|---|---|---|---|
| [0001](0001-skills-over-commands.md) | Skills over commands: command intent folds into skills or retires | Accepted | CANON 3; backfill #40 |
| [0002](0002-hooks-as-script-plus-config.md) | Hooks as script + config, never inline in settings.json | Accepted | dotfiles convention + gate H4; backfill #40 |
| [0003](0003-externals-tracked-not-vendored.md) | Externals tracked-and-cloned (upstream + pinned ref), never vendored | Accepted | CANON 11/16; backfill #40 |
| [0006](0006-meta-tracked-by-default.md) | `_meta/` tracked by default; targeted ignores only (operations/, caches, litter) | Accepted | #99 owner ruling 2026-07-13 |
| [0007](0007-distribution-restructure-dev-main.md) | Distribution restructure: `dev` integrates, `main` publishes — build on `dev`, never `main` | Accepted | DEV-31/#115; mirrors old-desk ADR 0014 |
| [0008](0008-vendor-dist-lanes-and-filtered-publish.md) | Vendor dist lanes under `dist/`, filtered append-only publish, flow.yaml as standing structural guard | Proposed | opencode lane planning, 2026-07-22 |

### Deliberately not carried

- **0004** (`rules-and-memory-translation-policy`) — governed rules/auto-memory behavior
  *when translating to opencode*. The clean-room rebuild dropped the multi-vendor translation
  surface entirely (Claude-Code-only, charter G1); the decision has no target to bind.
- **0005** (`frontend-stack`) — `Proposed` status, conditional on a UI surface entering scope
  ("binds only when a deliverable actually has a UI"). No deliverable in the 0007 lineup has
  a UI surface, so it never bound and isn't carried. Revisit if that changes.

Both remain readable at their original path on `dev-legacy` if a future UI or cross-vendor
surface needs to re-open them.
