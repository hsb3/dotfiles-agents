---
id: decision-024
title: Board-desk owns board maintenance and references kata
date: '2026-09-08'
status: accepted
---
## Context

Owner ruling on r6h7, 2026-09-08, approved A-narrow: collect the board maintenance
surface in a board-desk plugin, keeping canonical primitives under `primitives-core/`.
The implementation follows the membership cleanup in PRs #509 and #515. At that
baseline board-triage ships in code-desk and task-authoring in mise-en-place, not
solo-skills. The older instruction to remove task-authoring from solo-skills is stale.

## Decision

- Board-desk starts at 0.1.0 with board-triage and task-authoring. Its assembly links to
  canonical primitives; plugin membership stays out of the provenance roster.
- Board-triage leaves code-desk. Its health check and both Kata and GitHub Projects
  adapters travel together. The repo-local reconciler moves to
  `primitives-core/skills/board-triage/scripts/reconcile_github.py`, accepts `--project`,
  and remains dry-run unless `--apply` is explicit. Existing callers use that path.
- Planning-desk stays in mise-en-place; waves stays in atelier.
- Kata remains a cross-marketplace dependency from `hsb3/kata-oversight`, declared
  as `kind: plugin` with an immutable ref in `externals.yaml`. No upstream bytes are
  copied. The vendoring rule defines third-party by **different repository**, even
  when both repositories share an author; moving kata here would need a separate ruling.
- Kata-audit owns per-card definition and dependency checks. Board-triage's
  `board_health.py` owns board-wide discrimination. There is no duplicate audit.

## Amended 2026-09-10 — retain the planning dependency

Under the owner's execution grant, the lead approved retaining task-authoring's existing
mise-en-place symlink as a required planning-desk dependency. Board-desk is its primary
topical home. An independent review reproduced six citation failures when the link was
removed and zero when only that membership was restored; the lead separately confirmed
mandatory source invocations. No gate exception, duplicate body or planning-desk move is
part of this amendment. This supersedes only the original membership-removal instruction.

Mise-en-place alone keeps its working authoring dependency. Enabling both plugins can
list task-authoring twice, as observed historically in decision-020; no fresh runtime
listing proof is claimed here. Owning and carrying bundles follow decision-017's distinction.

## Consequences

Code-desk consumers install board-desk to keep board triage. Board-desk works with
existing backend clients; the full Kata maintenance rhythm additionally requires the
separate kata plugin for wiring and per-card audits. GitHub reconciliation does not
create issues or cards and applies only stale-mirror closes; reverse drift stays
informational. GitHub reads retain the existing 500-issue limit per state.

The source plugins and marketplace move versions under the repository's version rules.
The code-desk board-triage removal must be declared in the squash commit with its new
home. Solo-skills has no membership change in this move and gets no bump for one.
Decision-020 and decision-021 retain their historical text with dated amendments that
distinguish the earlier mise-en-place move from this new board-desk home.
