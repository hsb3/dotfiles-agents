---
id: DRAFT-007
title: 'atelier: provider-agnostic model tiers with a validated, refreshable mapping'
status: Draft
assignee: []
created_date: '2026-08-08 15:59'
labels:
  - primitives
  - decision
dependencies: []
type: feature
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
The agent roster hardcodes `anthropic/claude-*` model ids across 7 agent files. Two problems.

**It assumes one provider.** Tier is the real concept — recon, execution, judgment, management, strategy — and it should resolve to a concrete model per configured provider. Switching provider (or trying a non-Anthropic model in one tier) currently means editing 7 files, and the tier intent is implicit in scattered model strings rather than stated once.

**Nothing validates a model id.** `Provider.parseModel` just splits on `/`, so a wrong id silently degrades an agent instead of failing. This has already bitten: the namespace gate shipped asserting `anthropic/claude-haiku-5`, a model that does not exist (the real one is `claude-haiku-4-5`). Because nothing validated it, that check was green while pinning a value that would have broken every scout. The lesson recorded at the time — never assert an invented literal, always resolve against real semantics — applies directly here.

There is already a refresh mechanism in the ecosystem to build on: the `models/` generated model tables written by `models-dev` and read on demand via the claude-api skill. This task should consume that rather than inventing a second catalog.

Also produces an input the watermark task needs: per-model context-window size. Sequence this one first.

Owner rulings needed: the tier vocabulary and its names; which provider is the default; and the fallback when a tier has no mapping for the active provider (fail loudly, or degrade to a named default).
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A provider-independent tier vocabulary is defined, one tier per roster agent role
- [ ] #2 A single map resolves tier + provider to a concrete model id; no agent file names a model directly
- [ ] #3 Every model id is validated against a real catalog at gate time — an invented id fails the gate
- [ ] #4 Refresh path defined and documented, consuming the existing models.dev generated tables
- [ ] #5 Switching the active provider requires editing one map, not 7 agent files
- [ ] #6 Per-model context-window size is exposed for the watermark task to consume
- [ ] #7 Documented fallback behavior when a tier has no mapping for the active provider
<!-- AC:END -->
