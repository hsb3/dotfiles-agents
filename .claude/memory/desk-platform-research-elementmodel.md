---
name: desk-platform-research-elementmodel
description: "Verification pattern for reviewing the dev-tooling desk-platform element-model spec, esp. its net-new RESEARCH support"
metadata: 
  node_type: memory
  type: reference
  originSessionId: fdbbdcbf-b5ec-488b-9d8d-aa7c232fc398
  modified: 2026-07-22T19:20:32.614Z
---

> **Correction (2026-07-22):** paths below predate the EXECUTIVE_DESK reorganization;
> dev-tooling-desk is archived at
> `~/Documents/EXECUTIVE_DESK/Projects/ARCHIVE/dev-tooling-desk-old`, the desk estate now
> lives under `~/Documents/EXECUTIVE_DESK/Projects/` (desk-standard-desk,
> dotfiles-agents-desk, desk-standard-practice, desk-standard-tutorial).

Reviewing `~/Documents/EXECUTIVE_DESK/Projects/ARCHIVE/dev-tooling-desk-old/_meta/plans/desk-platform/spec-element-model.md` (element model
for a PM/KM platform, three planes input/activity/output, project types software+research).
Synthesized from `functionform-headcase/packages/obsidian/data/_headcase` (schema.yaml + shared/sops/).

**What checked out (don't re-litigate on future revisions):** the proposal's factual claims about
`_headcase` are accurate — no `goal`/`objective`/`okr` type (one-pager carries a `## Success Metrics`
table instead); no `source` entity (only a `## Sources` section in the research-synthesis template);
`analysis` cleanly precedes `decision` in _headcase's own SOPs ("weigh here, bind there"). Its
self-diagnosed §5 gaps are correct as far as they go.

**Where research support keeps refuting (scrutinize these on any R4+ revision):**
- No claim/finding + citation/excerpt entities — the evidence-to-claim link (the core of *cited*
  research) collapses into prose inside a `research-synthesis` doc. Inconsistent with the proposal's
  own "registries -> entities" thesis (it promotes DECISIONS/TASKS/OPEN_QUESTIONS but leaves
  SOURCES/FINDINGS as prose).
- `source` is one flat entity for doc/url/dataset/paper — needs subkinds + access-date/version/
  credibility; `dataset` is wrong-shaped as a citation (it feeds experiments).
- No experiment/protocol/result element — empirical research (benchmarks, A/B, reproductions) has
  nowhere to record method+results; research left weaker than the software side (which has test-plan).
- Linear brief->plan->gather->synthesis->findings forces a waterfall; research is a loop
  (open-question re-enters the brief).
- research-report vs research-synthesis vs analysis vs decision boundaries undefined in the walkthrough
  (analysis->decision is the only clean pair, inherited from _headcase).
- v1 spine defers `research-synthesis` (the one research doc _headcase ships free) — so the first
  research slice produces only sources+notes+decision, no synthesizing artifact.

Minor: `postmortem` SOP exists in _headcase but is unmentioned in the proposal; schema has 32 type
entries, proposal says "31".
