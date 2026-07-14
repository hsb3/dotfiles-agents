# Decisions (ADRs)

_One Architecture Decision Record per decision that shapes the build — what was decided,
why, and what it affects — so a choice made once isn't silently re-litigated._

Status: active

## Convention

- One file per decision: **`NNNN-kebab-title.md`** (zero-padded, sequential). Start from
  [`0000-template.md`](0000-template.md).
- Every ADR opens with the common doc-frontmatter core (`title` · `type: decision` · `status` ·
  `created`; see [`docs/governance-map.md`](../governance-map.md)) — the `status:` field holds the
  ADR lifecycle value below.
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
- The doc or code where the decision binds carries a short `Decision: ADR-NNNN` reference;
  the ADR links back. Link, don't copy.

## Log

| ADR | Decision | Status | Raised by |
|---|---|---|---|
| [0001](0001-skills-over-commands.md) | Skills over commands: command intent folds into skills or retires | Accepted | CANON 3; backfill #40 |
| [0002](0002-hooks-as-script-plus-config.md) | Hooks as script + config, never inline in settings.json | Accepted | dotfiles convention + gate H4; backfill #40 |
| [0003](0003-externals-tracked-not-vendored.md) | Externals tracked-and-cloned (upstream + pinned ref), never vendored | Accepted | CANON 11/16; backfill #40 |
| [0004](0004-rules-and-memory-translation-policy.md) | Rules CC-only; auto-memory translates lossily to opencode | Accepted | Q-03; vault migration 2026-07-05 |
| [0005](0005-frontend-stack.md) | Frontend stack (Vite+React+shadcn) for agent-built UI | Proposed | Q-07 gate; vault migration 2026-07-05 |
| [0006](0006-meta-tracked-by-default.md) | `_meta/` tracked by default; targeted ignores only (operations/, caches, litter) | Accepted | #99 owner ruling 2026-07-13 |
| [0007](0007-distribution-restructure-dev-main.md) | Distribution restructure: `dev` integrates, `main` publishes — build on `dev`, never `main` | Accepted | DEV-31/#115; mirrors old-desk ADR 0014 |
