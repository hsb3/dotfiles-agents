---
title: "Build plan — Gate-2 pilot close-out: re-audit proof, gap justification, findings routing, vault sign-off (#33)"
type: spec
status: draft
created: 2026-07-03
purpose: Source-grounded plan for the RESIDUAL of #33 — what remains after the 2026-07-02 pilot execution (PR rgpt#541 merged) and the 2026-07-03 mechanical fix pass, through Gate-2 sign-off; plus the brownfield follow-on scope, clearly separated.
notes: Issue #33's body is partly stale (nested checkout path, "likely dev" guess) — this plan works from the verified 2026-07-03 state. The vault is the hsb-2026 Obsidian vault (located; see Tracking). rgpt# = mhi-raptorxai/raptorgpt-agents.
---

# Gate-2 pilot: audit → manifest → scaffold → re-audit on raptorgpt-agents

_Most of this pilot already happened. The full sequence ran 2026-07-02 (baseline 36 pass / 22 gap,
scaffold apply, re-audit 56 pass / 3 gap, additive-only + idempotence proven live) and landed as
merged PR rgpt#541; both pilot-found defects were filed and fixed (da#38, da#44); the manifest exists
and is verified. The standard then moved under the pilot: plugin 0.2.1 added the DOCS-02..05,
PLANS-01..06, IGNORE-13..16 rows and blessed `_meta/_archive/` (#35, PR #64), so today's re-baseline
reads 51 pass / 17 gap, and a foreman session is applying the mechanical fixes right now. **This plan
covers only the residual:** the post-fix re-audit proof, a justification for every remaining GAP,
routing of any new pilot findings, recording TC-013/TC-010 observations in the vault and getting
Henry's sign-off ticks (the stated Gate-2 proof), and — as separated FOLLOW-ON scope — enumerating
the brownfield backfill the pilot exposed (89 open issues, no planning desk, no decision records)._

Status: draft
Date: 2026-07-03

## Tracking

- Issue: #33 (milestone "P2 — Pilot proven"). Closing condition per its 2026-07-02 comment thread:
  merge rgpt#541 (done, merged 2026-07-02T19:54Z), then tick TC-013/TC-010 in the vault test plans.
- Origin: Gate-2 pilot GO decision, 2026-07-02 — vault
  `hsb-2026/02_Projects/02_DEVTOOLS/1_Project_Management/DECISIONS.md` ("ln on raptorgpt-agents: GO
  (audit → init-manifest → scaffold plan/apply → re-audit)"). The vault lives at
  `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/hsb-2026/` (Obsidian iCloud vault —
  located this session; confirm, open question 4).
- Relations: rgpt#541 (pilot output PR, MERGED); da#38 + da#44 (pilot findings round 1, both CLOSED —
  the routing precedent); #35 / PR #64 (`_meta/_archive/` naming, source of today's META-01 gap);
  #40 (DOCS-xx rows, source of today's DOCS gaps); #45 (issue-body.md frontmatter exemption, CLOSED);
  rgpt#542–554 (pilot's brownfield sweep, already filed); rgpt#544 (openspec-vs-planning-desk
  decision, OPEN — gates the CLAUDE-07 and planning-desk follow-on items).
- Contract impact: none in this repo from the pilot itself — no `primitives-core/` edits, no
  checklist rows, no `targets/` regeneration. Pilot FINDINGS that become fixes here land as their
  own issues/PRs under the normal gates (Deliverable C), exactly as #38/#44 did.

## The problem (grounded in source)

**What exists (verified 2026-07-03):**

- The pilot repo is a FLAT checkout at `~/Developer/raptorgpt-agents`, branch `dev`, active work in
  flight (`_meta/plans/fix-sprint/` has one modified + two untracked staged docs). The issue body's
  nested `~/Developer/RAPTOR/WEB_APPS/raptor_gpt/` path no longer exists — and the "correction"
  notes inside TC-013/TC-010 still point at that nested path, so they are stale too.
- `_meta/mise-en-place.yml` exists and is filled: `owner: "mhi-raptorxai"`, `default_branch: dev`
  (verified 2026-07-02 via origin/HEAD), empty variance lists.
- `_meta/` is fully scaffolded (`briefings/ operations/ plans/ research/ HANDOFF.md README.md`) but
  with the OLD `_meta/archive/` name; the standard now requires `_meta/_archive/` (checklist META-01,
  `repo-meta-structure/references/checklist.md:29`, blessed by #35 / PR #64).
- The `.gitignore` `_meta/*` negation stanza is in place (rgpt `.gitignore:171-175`, the IGNORE-01
  fix carried by rgpt#541).
- Round-1 findings are closed: da#38 (scaffold creates files the target's gitignore swallows) and
  da#44 (hardcoded template labels + duplicate-reviewer blind spot). Zero standards over-strictness
  findings in round 1.
- TC-010 already carries a "pilot run observations (2026-07-02, da#33)" section
  (`test-plans/build-repo-compliance-audit-skill.md:90`); TC-013 likewise. Both sign-off checkboxes
  are still UNTICKED (`build-mise-en-place-scaffold-skill.md:94`,
  `build-repo-compliance-audit-skill.md:87`).
- Baseline re-audit today with plugin 0.2.1 (foreman session; not independently re-run here):
  **51 pass / 17 gap**. The 17 enumerate exactly against the checklist: META-01 (1) + CLAUDE-07 (1,
  `.claude/commands/opsx/` present — checklist:47) + ROOT-03 (1, no `AGENTS.md` — checklist:72) +
  DOCS-02..05 (4, no `docs/CHARTER.md`, no `docs/decisions/` — checklist:92-95) + IGNORE-13..16
  (4, gitkeep negation triplets — checklist:116-119) + PLANS-01..06 (6 — checklist:142-147; 11 md
  files under rgpt `_meta/plans/`, all lacking frontmatter; 9 in scope after the #45 issue-body.md
  exemption).
- A foreman session is applying the mechanical subset NOW: archive rename (META-01), scaffold
  `--plan`/`--apply` (DOCS-03..05 triad), gitignore triplets (IGNORE-13..16), frontmatter backfill
  on non-in-flight planning docs (PLANS-01..06 partial).

**What's missing (the residual this plan delivers):**

- A post-fix re-audit table proving the mechanical pass closed what it claims — the issue's
  "re-audit gap count materially down" acceptance is currently only asserted, not evidenced against
  the 0.2.1 checklist.
- A justification for every GAP that survives the mechanical pass. Expected survivors: CLAUDE-07
  (migration debt by design — `flag-if-present`), ROOT-03 and DOCS-02 (authored-content rows the
  scaffold never creates — `AUTHORED_FILES` per the #40 plan), and PLANS-01..06 (still GAP while any
  in-scope in-flight doc — e.g. `fix-sprint/staged-563-comment-2026-07-03.md` — lacks frontmatter).
- Round-2 findings routing: anything the 0.2.1 re-run surfaces (bug → da fix issue; over-strictness
  → standards issue). One candidate already visible: staged `staged-*.md` comment/issue drafts are
  in PLANS scope but, like `issue-body.md` (#45), carry raw publishable bodies.
- Dated 2026-07-03 addenda in TC-013 and TC-010 (plugin 0.2.1 re-run, flat-checkout path
  correction), then Henry's sign-off ticks — the Gate-2 proof itself.
- Any organized statement of the brownfield backfill: rgpt has 89 open issues (verified via
  `gh issue list`), no planning-desk `_config.md`, no conformant plan folders, no decision records;
  rgpt#542–554 name pieces of it but nothing owns the whole.

## Deliverables

**A — Post-fix re-audit proof (plugin 0.2.1).**
After the foreman's mechanical pass lands on rgpt `dev`, run the repo-compliance-audit from the
installed 0.2.1 plugin at the rgpt root; capture the verbatim `ID | Area | Verdict | Detail` table
and `N pass / M gap` line; stage it in this folder as `re-audit-2026-07-03.md`. Run `--plan` once
more and capture the idempotence line (expected: 0 create).
_Acceptance:_ staged evidence file contains the full verbatim table; gap count is at or below the
expected survivor set (CLAUDE-07, ROOT-03, DOCS-02, any PLANS rows pending in-flight docs); every
mechanically-fixed row (META-01, DOCS-03..05, IGNORE-13..16) reads PASS; second `--plan` shows 0
create; `git status` in rgpt shows no modified tracked file attributable to the audit (read-only
proof).

**B — GAP justification ledger.**
For each surviving GAP, one row: checklist ID, class (content-authoring / declared variance /
migration debt), justification, and the tracked home of its eventual fix (rgpt issue, Deliverable E
epic, or `_meta/mise-en-place.yml` variance entry). Stage in `re-audit-2026-07-03.md` alongside A;
post to #33 as the results comment after owner approval (staging is free, publishing is owner-gated
per `_meta/plans/_config.md` conventions).
_Acceptance:_ ledger covers 100% of A's GAP rows; no row's class is "unexplained"; each row names a
tracked follow-up or an explicit accept-as-is ruling; the #33 comment is staged verbatim in this
folder before posting.

**C — Round-2 findings routing.**
Triage anything the 0.2.1 re-run surfaced, on the #38/#44 precedent: audit or scaffold DEFECTS →
dotfiles-agents fix issues (each with repro from the rgpt run); standards OVER-STRICTNESS →
standards issues against the checklist/skills. Known candidate to rule on: extend the #45
`issue-body.md` exemption to staged `staged-*.md` drafts (or rename convention) — file as a
standards issue if confirmed.
_Acceptance:_ every finding named in A/B either has a da issue number or an explicit "not a finding"
note; zero findings fixed silently in-repo without an issue; issue bodies conform to the desk
templates (Acceptance criteria + Dependencies & gates sections).

**D — Vault recording + Gate-2 sign-off.**
Append dated 2026-07-03 addenda to both vault test plans —
`hsb-2026/02_Projects/02_DEVTOOLS/1_Engineering/test-plans/build-mise-en-place-scaffold-skill.md`
(TC-013) and `build-repo-compliance-audit-skill.md` (TC-010) — covering: the 0.2.1 re-baseline
(51/17) and post-fix result, the mechanical-pass scope, round-2 findings, and a correction note that
the checkout is now flat at `~/Developer/raptorgpt-agents` (the existing in-file corrections cite
the dead nested path). Henry then ticks the two sign-off checkboxes; post B's approved comment on
#33 and close it.
_Acceptance:_ both test plans contain a 2026-07-03 addendum; the stale path corrections are
themselves corrected in place (dated, per the correction-erratum convention); TC-013 and TC-010
sign-off boxes are ticked BY HENRY (never by an agent); #33 closed with the results comment; the
vault `DECISIONS.md` / `CURRENT_STATE.md` reflect Gate-2 proven.

**E — FOLLOW-ON: brownfield backfill enumeration (separate scope, does NOT block A–D or #33).**
Stage (then file, owner-approved) one rgpt epic that owns the whole brownfield adoption, with
sub-items: (1) planning-desk setup in rgpt (`_meta/plans/_config.md`, conformant plan folders for
the existing `fix-sprint` / `agent-db-access-562` / `prod-agent-create-403` work) — explicitly
sequenced AFTER the rgpt#544 openspec-vs-planning-desk ruling; (2) decision-record backfill into the
newly scaffolded `docs/decisions/` (template + README from A's apply) for rgpt's load-bearing
decisions; (3) content authoring: `AGENTS.md` (ROOT-03) and `docs/CHARTER.md` (DOCS-02), closing
B's authored-content gaps; (4) `.claude/commands/opsx/` migration or retirement (CLAUDE-07, tied to
rgpt#544); (5) issue-conformance pass over the 89 open issues, absorbing rgpt#542–554 as existing
sub-items rather than duplicating them.
_Acceptance:_ epic staged in this folder with a "Close when" section; each sub-item names its
blocking dependency (esp. rgpt#544) and its checklist ID where one applies; explicitly states it is
follow-on to — not part of — the Gate-2 pilot; filed only after owner approval; #33 does not wait
on it.

## Gate & contract hygiene

dotfiles-agents gates for THIS plan's own changes (a plan doc + staged evidence under
`_meta/plans/`): none of the drift guards fire — no `primitives-core/`, roster, or `targets/`
edits. Pilot findings routed via C land as separate issues/PRs and pick up their own gates there
(a scaffold fix touches `primitives-core/` → `make ci` + targets drift guard, as #38's fix did).

| Gate | Fires | Why |
| ---- | ----- | --- |
| make ci aggregate | plan: no; C-routed fixes: yes | this plan adds _meta/plans/ docs only; any da code fix goes through CI on its own PR |
| Targets drift guard | plan: no; C-routed fixes: likely | fires only when a fix touches primitives-core/ or the manifests |
| Roster drift guard | no | no primitive added, removed, or renamed anywhere in this plan |
| Naming taxonomy | no | no new primitive or plugin names |
| yamllint / actionlint | no | no YAML or workflow edits in this repo |
| PLANS-01..06 self-conformance | yes | this plan.md and every staged doc in this folder carry the six-field frontmatter; issue-body/staged drafts follow the #45 exemption ruling |

raptorgpt-agents-side proof points (the pilot's own hard gates, run there — not asserted):

| Proof point | How proven |
| ----------- | ---------- |
| Additive-only, no overwrites | scaffold output review + git status showing untracked-or-new-only; precedent held in round 1 |
| Idempotence | second --plan reports 0 create (A) |
| Audit is read-only | no tracked-file modifications after the audit run (A) |
| Owner review before push | all rgpt-bound changes land via PR into dev, Henry reviews; round-1 precedent rgpt#541, 7 checks green |
| No in-flight collateral | fix-sprint staged/modified docs byte-identical before vs after the mechanical pass and re-audit |

## Parallelism + landing order

| Unit | Owner | Depends on | Notes |
| ---- | ----- | ---------- | ----- |
| A re-audit proof | one agent, read-only in rgpt | foreman mechanical pass landed on dev | run from rgpt root with installed 0.2.1 plugin; stage evidence in this folder |
| B justification ledger | same agent as A | A table in hand | one document with A; publishing to number 33 is owner-gated |
| C findings routing | one agent in dotfiles-agents | A/B drafted | can draft issue bodies in parallel with B; filing is owner-gated |
| D vault addenda | one agent with vault access | A + B final, C triaged | sign-off ticks and issue close are Henry-only |
| E brownfield epic | one agent | none (reads A/B when ready) | fully parallel to A-D; blocked at FILING on owner approval and sequenced after rgpt 544 ruling for its planning-desk item |

Landing order: A+B as one evidence package, C alongside, D last (it is the Gate-2 proof and
consumes all of them), E whenever — it never blocks the pilot close.

## Open questions / owner decisions

1. **Author `AGENTS.md` + `docs/CHARTER.md` now, or defer to E?** The #33 acceptance allows
   justified content-authoring gaps — authoring is not required for sign-off. **Recommend: defer to
   E(3)** and carry ROOT-03/DOCS-02 in B's ledger as content-authoring rows; authoring canonical
   pages for a brownfield repo deserves its own pass, not a pilot footnote.
2. **In-flight PLANS docs and `staged-*.md` frontmatter.** PLANS-01..06 stay GAP while any in-scope
   doc lacks frontmatter, and the fix-sprint staged drafts are raw publishable bodies (same shape
   as the #45-exempted `issue-body.md`). **Recommend:** justify as in-flight in B now; backfill the
   genuinely-in-flight docs at their session boundary; file the staged-drafts exemption question as
   a C standards issue rather than force-adding frontmatter to publishable text.
3. **CLAUDE-07 disposition.** `.claude/commands/` holds exactly one entry, `opsx` (openspec).
   **Recommend:** accept as flagged migration debt in B, resolution owned by E(4) and gated on the
   rgpt#544 openspec ruling — do not migrate or delete during the pilot.
4. **Vault identity.** This plan takes "the vault" to be the Obsidian vault at
   `~/Library/Mobile Documents/iCloud~md~obsidian/Documents/hsb-2026/` — where the GO decision row,
   CURRENT_STATE pilot log, and both TC test plans live. (`_config.md` names the cowork desk at
   `~/Documents/Claude/Projects/dotfiles-agents-cowork/` for governance docs, but TC-013/TC-010 are
   not there — searched.) **Recommend: confirm hsb-2026 is canonical for TC records** — high
   confidence, one-word answer wanted before D writes to it.
5. **When does #33 close?** **Recommend:** after A's evidence + B's 100%-justified ledger are posted
   and Henry ticks TC-013/TC-010 — exactly the closing condition already stated on the issue; E is
   filed separately and never holds #33 open.
6. **Where does the E epic live?** **Recommend: rgpt-side** (it is rgpt's backlog, per its own
   taxonomy, absorbing rgpt#542–554), with only a cross-link from the da milestone — not a da issue.
