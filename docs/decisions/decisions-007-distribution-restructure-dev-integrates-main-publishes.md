---
title: "Distribution restructure: dev integrates, main publishes"
id: decision-007
type: decision
status: Accepted
created: 2026-07-14
summary: dotfiles-agents uses a dev integration branch — humans and agents branch off dev and PR into dev; main is the CI-published marketplace surface and is off-limits to direct commits.
---

# Decision 007 · Distribution restructure: `dev` integrates, `main` publishes

_The in-repo mirror of the branch-governance rule: build on `dev`, never `main` — so the
rule is visible where the crew works, not only on the strategy desk._

- **Provenance:** mirrors old-desk ADR **0014**
  (`dotfiles-agents-cowork/_structure/decisions/0014-distribution-restructure-dev-main.md`,
  also recorded desk-side as executive-desk `decisions/0010`). Owner ruling relayed on
  DEV-31 (2026-07-14): `dev` was cut from `main` at
  `452969a3b92af01089c9b0de6a0cb3493a005713` (cutover-plan step 1 pulled forward, verified
  on the remote); build proceeds on `dev`.
- **Raised by:** DEV-31 / [#115](https://github.com/hsb3/dotfiles-agents/issues/115) build
  scope (this ADR authored as the first `skill-bundle` PR) · the distribution-restructure
  epic (#111–#113).

## Context

Consumers add this repo as a Claude Code marketplace by the `owner/repo` shorthand
(`claude plugin marketplace add hsb3/dotfiles-agents`), which reads the **default branch**'s
generated `.claude-plugin/marketplace.json`. That makes the default branch a *published
surface*: any commit to it is immediately live for every installer. Building directly on the
published branch means half-finished work, an un-regenerated manifest, or a failed drift
guard reaches consumers before review.

The distribution restructure (#111–#113) separates the two roles the branch was conflating —
*integration* (where work lands and is reviewed) and *publication* (what consumers install).
The authority for the split is old-desk ADR 0014, but that decision lived only on the strategy
desk: `docs/decisions/` in this repo stopped at 0006, so a crew member working here had no
in-repo record of which branch to target. DEV-31's planner and reviewer both flagged the
absence as a hard blocker before any build could pick a valid target branch.

## Decision

**`dev` is the integration branch; `main` is publish-only.**

- All work — human or agent — **branches off `dev` and opens PRs targeting `dev`**. Branch
  naming and squash-merge conventions are unchanged.
- **`main` is off-limits to direct commits** from humans and agents. It is the CI-published
  marketplace surface; it advances only by the sanctioned promotion path (`dev` → `main`),
  not by ad-hoc pushes.
- The marketplace-manifest regeneration that republishes `main` is sequenced **last**, after
  the manifest-serialization work (#112/#113) releases — no PR regenerates or commits the
  root manifest until then.

This ADR is the in-repo mirror; **old-desk ADR 0014 remains the authority of record.** If the
two ever disagree, 0014 wins and this mirror is corrected to match.

## Consequences

- A valid, documented target branch exists for `skill-bundle` and every subsequent build:
  branch from `dev`, PR into `dev`.
- CI keeps running `make ci` on every PR (any base) and on push to `main`; the drift guards
  stay authoritative on both branches.
- The `dev` → `main` promotion becomes a deliberate, reviewed step — the point at which the
  regenerated marketplace manifest is published — rather than a side effect of merging a
  feature.
- If the epic's cutover model changes (e.g. `main` is retired or renamed), this ADR is
  superseded by a new one and 0014 is updated first.

## Affects

Branch/PR governance for all `dotfiles-agents` work · `CLAUDE.md` / `AGENTS.md` task
interface · CI target-branch assumptions (`.github/workflows/ci.yml`) · the
marketplace-manifest publish step gated on #112/#113 · the `skill-bundle` (DEV-31) build.
