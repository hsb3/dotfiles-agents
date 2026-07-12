---
title: "fix: planning-desk plan.md guidance omits the 6-key frontmatter schema PLANS-01..06 requires"
type: spec
status: draft
created: 2026-07-12
purpose: Source-grounded build plan for #70 — make planning-desk's plan-authoring guidance prescribe the 6-key YAML frontmatter (title, type, status, created, purpose, notes) on plan.md so a plan.md produced by following the skill literally passes repo-compliance-audit PLANS-01..06.
notes: Drafted 2026-07-12 in worktree plans-wave. Corrected-scope re-pointing already landed on the live issue (#70, verified against plugin source 0.2.4) — this plan does not re-litigate scope, it builds the corrected scope's three acceptance criteria. All citations re-verified fresh 2026-07-12.
---

# fix: planning-desk plan.md guidance omits the 6-key frontmatter schema PLANS-01..06 requires

_Issue #70's own "Corrected scope" section already re-pointed this issue once (from "the desk's
generated docs fail the audit" to the precise live gap below) — this plan does not redo that
diagnosis, it builds the three acceptance criteria the corrected scope states. RESIDUAL: nothing
has shipped yet; #70 is still fully open. The fix is prose-only (one reference doc gains a
frontmatter block + a citation), not a schema change — the schema itself already exists and is
already correct in a sibling standard doc; the gap is that planning-desk's own authoring guidance
doesn't point to it._

Status: draft
Date: 2026-07-12

## Tracking

- Issue: #70 (`planning-desk artifacts lack the PLANS-xx frontmatter repo-meta-structure
  requires`, OPEN). Staged body: `_meta/plans/plan-frontmatter-schema/issue-body.md` (copied
  verbatim from the live issue — no redraft needed, the corrected scope is already sound).
- Origin: filed against planning-desk cache 0.1.0 / audit 0.2.1; re-verified and re-pointed by
  the issue author against plugin source 0.2.4 (in-issue "Corrected scope" section).
- Relations: sibling live gaps on the same skill from the same wave — #69 (issue-template
  `.yml` vs `.md` mismatch), #68 (toolkit blind to issue-body-only folders), #83 (require both
  `issue_body.md` and `plan.md` per folder), #82 (rename `_meta/plans` -> `_meta/issues`, OPEN).
  None of these four block #70 and #70 blocks none of them — see Dependencies below for the
  gate-sharing relationship that DOES couple them.
- Contract impact: edits `primitives-core/skills/planning-desk/references/plan.md` (a
  distributed primitive's source) — **fires the targets drift guard** (`make build`) because
  `primitives-core/` changed, even though the edit is prose-only. No `primitives-core.yaml`,
  `plugins.yaml`, or translation-config edit (no primitive added/removed/renamed), so the
  **roster** drift guard does NOT fire.

## The problem (grounded in source)

**EXISTS — the frontmatter schema is already fully specified, just not in planning-desk.**
`primitives-core/skills/repo-meta-structure/references/planning-docs.md:16-25` defines the exact
6-key block:

```yaml
---
title: ""
type: reference|spec|canon
status: draft
created: YYYY-MM-DD
purpose: ""
notes: ""
---
```

`planning-docs.md:27-34` documents field semantics, and `planning-docs.md:38-46` gives the
`type` vocabulary (`reference`, `spec`, `canon` for `_meta/plans/` proper; `proposed-issue` /
`reprioritization-memo` reserved for `_meta/plans/inbox/` communication packages — out of scope
for plan.md). `planning-docs.md:36` states plainly: "The machine checks are rows `PLANS-01` ...
`PLANS-06` in `checklist.md`."

**EXISTS — the machine check that enforces it.**
`primitives-core/skills/repo-meta-structure/references/checklist.md:142-149` is the PLANS-01..06
table: `frontmatter-has: title|type|status|created|purpose|notes`, one row per key, each keyed to
"Every in-scope doc's frontmatter has `<key>`." The scope line at `checklist.md:133-136`: every
`*.md` under `_meta/plans/` (recursive, including `inbox/`) EXCLUDING `README.md`, `_`-prefixed
files (e.g. `_config.md`), anything under `_utils/`, and `issue-body.md` files (staged issue
bodies are exempt by the 2026-07-02 owner ruling — kept byte-identical to the live GitHub body).
`plan.md` matches none of the exclusions, so it is squarely in scope.

**EXISTS — the desk's own strong plans already carry this frontmatter in practice, just not by
following the documented guidance.** Every current `plan.md` on this repo's own desk opens with
the 6-key block — e.g. `_meta/plans/frontend-extenders-curation/plan.md:1-8`
(`title/type/spec/status:draft/created:2026-07-03/purpose/notes`), and a repo-wide sweep of the
worktree's desk confirms it is universal: every `plan.md` under `_meta/plans/*/plan.md` opens
with exactly two `---` frontmatter delimiters (verified fresh 2026-07-12,
`rg -c '^---$' _meta/plans/*/plan.md` — 9/9 existing plans return `2`). **This is the core
finding: the PRACTICE already exists and is followed by every human/agent who has drafted a plan
here, but the SKILL GUIDANCE that's supposed to generalize the practice to other repos doesn't
prescribe it** — so a plan.md produced by literally following `references/plan.md` in a fresh
repo (or by an agent that hasn't seen this repo's existing plans and pattern-matched off them)
would fail PLANS-01..06 on day one.

**MISSING — the plan-authoring guidance names none of the 6 keys.**
`primitives-core/skills/planning-desk/references/plan.md:14-31` is the full prescribed plan
shape ("What 'proper' means"). Line 15: `**Status header:** \`Status: draft\` and
\`Date: <today>\`` — an inline two-line header, not YAML frontmatter, and it names only 2 of the
6 required keys (`status`, `created` — under different names and format: `Date:` not
`created: YYYY-MM-DD`). The bullet list (lines 13-29: Title, Status header, Tracking, The
problem, Deliverables, Gate & contract hygiene, Parallelism, Open questions) contains no mention
of `title` (as a frontmatter field distinct from the H1), `type`, `purpose`, or `notes`, and no
reference to `checklist.md` or `planning-docs.md` at all. Re-checked at the current line numbers
(no drift from the brief's citation).

**MISSING — no cross-reference anywhere in planning-desk to repo-meta-structure's frontmatter
schema.** `rg -n "PLANS-0|planning-docs|frontmatter" primitives-core/skills/planning-desk/`
(verified fresh 2026-07-12) returns zero hits across `SKILL.md`, all of `references/`, and all of
`assets/` — the two skills currently have no textual link between them despite
`repo-meta-structure` governing the exact doc type `planning-desk` produces.

**NON-DEFECT — confirmed exempt, no change needed (issue's third acceptance criterion).**
- `assets/_config.template.md` and the generated `_config.md`: `_`-prefixed, excluded by
  `checklist.md:134`.
- `assets/plans-README.md` and the generated `README.md`: the desk index, excluded by
  `checklist.md:133-134`.
- `references/issue-body.md` (the skill's issue-authoring guidance) and every generated
  `issue-body.md`: excluded by `checklist.md:135-136` (staged issue bodies are byte-identical to
  the live GitHub body by the 2026-07-02 ruling; adding frontmatter would break that identity).
  Read fresh at `primitives-core/skills/planning-desk/references/issue-body.md` — it already
  prescribes no frontmatter and should stay that way.

## Deliverables

**A — `references/plan.md` prescribes the 6-key frontmatter.** Replace the "Status header" bullet
(`references/plan.md:15`) with a frontmatter bullet that emits the full block, and update the
"Title" bullet (`references/plan.md:13`) so the H1 title and the frontmatter `title:` field are
both accounted for (H1 = human-readable title + italic scope summary, exactly as today;
frontmatter `title:` = the same string, quoted, as a machine-readable field — mirrors how every
existing plan already does it, e.g. `frontend-extenders-curation/plan.md:1-10` carries both the
frontmatter `title:` on line 2 and the H1 on line 10). Keep the existing inline `Status: draft` /
`Date: <today>` line directly under the H1 too (do not remove it) — the desk's own exemplars
carry both the frontmatter block AND the inline line (see
`frontend-extenders-curation/plan.md:1-8` frontmatter, then line 10 H1, then lines 25-26 inline
`Status:`/`Date:`); the fix adds the frontmatter, it does not replace an existing convention that
is still in active use and still human-scannable at a glance.
**Acceptance** (matches issue checkbox 1): a fresh `plan.md` produced by an agent following ONLY
`references/plan.md` (no prior exposure to this repo's existing plans) opens with a 6-key YAML
frontmatter block (`title, type, status, created, purpose, notes`) and would score
`PLANS-01..06 = PASS` if run through `repo-compliance-audit` (verify by hand-tracing the
checklist's `frontmatter-has:` checks against the produced doc, since audit is read-only tooling
and not itself invoked by this plan-only issue).

**B — the guidance cites PLANS-01..06 and points at the canonical schema doc.** Add one sentence
to `references/plan.md`'s frontmatter bullet citing
`repo-meta-structure/references/planning-docs.md` (the schema's canonical home, with field
semantics and the `type` vocabulary) and `repo-meta-structure/references/checklist.md`
(PLANS-01..06, the machine check). Point at the doc, do not inline a second copy of the
field-semantics table or the `type` vocabulary — `planning-docs.md:27-34` and `:38-46` are
already the single source of truth for those; duplicating them in `planning-desk` would create
two copies that can drift (the failure mode this whole issue is about, one level up).
**Acceptance** (matches issue checkbox 2): `references/plan.md` contains the literal string
`PLANS-01` (or equivalent unambiguous cite to the checklist rows) and a path reference to
`planning-docs.md`; grep confirms both.

**C — confirm no change to the three exempt artifacts.** No edits to
`assets/_config.template.md`, `assets/plans-README.md`, or `references/issue-body.md`. This
deliverable is a negative-space check, not new work: run a diff-free confirmation at the end of
the change (`git diff --stat` over the PR) and state in the PR description which files were
touched.
**Acceptance** (matches issue checkbox 3): `git diff --stat` for the fix PR shows changes to
`references/plan.md` only (plus the regenerated `targets/` mirror from `make build` — see Gate
hygiene); zero lines changed in `_config.template.md`, `plans-README.md`, or
`references/issue-body.md`, in either the source or any generated target copy.

## Should the template/README gain a frontmatter example? (resolved: no)

Considered per the brief's prompt and resolved during drafting, not left open: `plans-README.md`
and `_config.template.md` are both confirmed exempt (Deliverable C) and neither is a per-plan
authoring surface — `plans-README.md` is the desk INDEX (one row per plan, no plan content) and
`_config.template.md` is project-config, not a plan body. Adding a frontmatter example to either
would be scope creep against the issue's explicit third acceptance criterion ("no change to
`_config.md`/`README.md`/`issue-body.md` guidance"). The correct single place for a worked
frontmatter example is `references/plan.md` itself (Deliverable A) — that IS the plan-authoring
guidance the skill routes an agent to (`SKILL.md:57`: `plan mode -> references/plan.md`).

## Gate & contract hygiene

| Gate | Fires on #70? | Why |
| ---- | -------------- | --- |
| CI aggregate (make ci) | yes, once the fix PR lands | any PR + push to main, always |
| Roster drift guard (make check) | no | no primitive added, removed, or renamed in `primitives-core/` -- this is a prose edit inside an existing skill's existing reference file |
| Targets drift guard (make build-check / make build) | yes | edits `primitives-core/skills/planning-desk/references/plan.md`, a distributed primitive's source; `targets/` must be regenerated in the same PR (`make build`) or the drift guard fails |
| Naming taxonomy (make names) | no | no new primitive or plugin named |
| YAML / workflow lint | no | no `.yaml`/`.yml`/`.github/workflows/` edit (the frontmatter block ADDED to future plan.md docs is YAML-shaped content inside a markdown code fence in the guidance doc, not a `.yaml` file itself) |
| Canonical-doc amendment | no | `references/plan.md` is a skill reference doc, not one of `_config.md`'s listed canonical docs (`CLAUDE.md`, `AGENTS.md`, `docs/CHARTER.md`, `docs/plugins/*`, `docs/sops/*`); no spine doc describes plan-authoring behavior that this change would leave stale |
| project-workflow version bump | yes | `planning-desk` ships inside the `project-workflow` plugin; any primitive-source edit that regenerates `targets/` needs the plugin's version bumped per repo convention (brief's explicit gate hygiene note; confirm exact bump mechanism against `plugins.yaml` at build time, not planned here) |

This issue itself, this plan.md, is report-only (planning artifact under `_meta/plans/`) — no
gate fires on drafting the plan. The table above describes what fires on the IMPLEMENTATION PR
that will eventually execute Deliverables A/B/C; this plan does not implement them (PLAN-ONLY
per the brief).

## Parallelism + landing order

| Unit | Scope | Depends on | Notes |
| ---- | ----- | ---------- | ----- |
| A - frontmatter bullet | `references/plan.md:13-15` region | none | single small edit, no fan-out needed |
| B - PLANS-01..06 citation | `references/plan.md`, same edit region as A | none, but same file as A | fold into the same edit as A rather than a second pass - one file, one owner, no parallel writers on `plan.md` |
| C - confirm-exempt check | repo-wide diff review | A + B land first | trivial verification step, runs last as a gate check on the PR diff, not a build task |
| targets regen | `make build` over the whole `planning-desk` primitive | A + B committed | must run in the SAME PR as A/B per the targets drift guard - not a separate follow-on |

A and B are the same file edit and do not parallelize against each other (would be two agents
touching one file). C is a verification pass, not build work. No units here are independently
parallelizable — this is a single small, serial fix; the brief's "parallelism" framing mostly
matters for the SEQUENCING against sibling issues below, not within this one.

## Dependencies

- **#70 does not block on #68** (toolkit scripts: reconcile's blind spot to issue-body-only
  folders) — #68 touches `scripts/_utils/` behavior; #70 touches `references/plan.md` prose
  only. Independent file scopes, independent acceptance criteria.
- **#70 has a SAME-FILE overlap with #83.** #83's own body names `references/plan.md` as one
  of the three guidance files its "both files required" edit touches (alongside `SKILL.md`
  and `references/issue-body.md`), so #70 and #83 both edit `references/plan.md` — a
  materially higher collision risk than the generic shared-plugin gate below. The edits are
  logically disjoint (frontmatter bullet vs two-artifact requirement) but must land
  serialized on the same file, one rebasing over the other.
- **#70 shares the planning-desk-edit gate with #69/#68/#83.** All four land inside the same
  `project-workflow` plugin primitive (`planning-desk`), so each requires its own `make build`
  regen and its own version bump. **Concurrent planning-desk PRs collide on the version bump and
  the regenerated `targets/` mirror** (two PRs both bumping the same version field, or both
  regenerating overlapping generated files, produce a merge conflict or a silently-stale
  `targets/` if merged out of order). Serialize merges: land one planning-desk PR, merge, THEN
  branch the next off updated `main` — do not run #70's implementation concurrently with #68/#69/
  #83's implementations on stale bases.
- **#70 does not block on #82** (rename `_meta/plans` -> `_meta/issues`). #70 edits
  `references/plan.md` PROSE (the frontmatter bullet, the PLANS-01..06 citation) — it does not
  reference the `_meta/plans` path in a way that the rename would break, since the guidance text
  being edited doesn't hardcode the directory name in the frontmatter bullet itself. **However:**
  if #70 lands AFTER #82, any worked example or path mention added to `references/plan.md` as
  part of Deliverable A/B should use the post-rename `_meta/issues/<slug>/plan.md` path, not
  `_meta/plans/<slug>/plan.md` — check `references/plan.md`'s surrounding prose for the current
  path convention at implementation time and match whichever generation is live. If #70 lands
  BEFORE #82, no action needed (paths in the new frontmatter bullet, if any are added, use
  `_meta/plans/` as everything else in the skill does today).
- **Relates to (not blocked by):** `repo-meta-structure` PLANS-01..06 — the standard this issue
  conforms `planning-desk` TO; `repo-meta-structure` itself does not change as part of #70 (the
  schema is already correct there; only the CITATION from `planning-desk` is missing).

## Open questions / owner decisions

1. **Does the inline `Status: draft` / `Date: <today>` line (currently
   `references/plan.md:15`, and present in every existing plan alongside the new frontmatter)
   stay, now that it is fully redundant with `status:`/`created:` in the frontmatter block?**
   **Recommend: keep both** — every existing exemplar plan (`frontend-extenders-curation`, and
   8 others per the fresh `rg` sweep) already carries both, the inline line is human-scannable
   without opening YAML, and removing it would touch every future plan's shape for a cosmetic
   win only. Alternative: drop the inline line now that frontmatter is mandatory, accepting a
   visual diff from all 9 existing plans (which would then be inconsistent with new ones unless
   separately migrated - not in this issue's scope).
2. **Exact wording/placement of the PLANS-01..06 citation in `references/plan.md`** — inline in
   the frontmatter bullet (terse, stays in the existing list) vs. a new short paragraph after
   the bullet list (more room to name `planning-docs.md` and `checklist.md` explicitly).
   **Recommend: inline in the bullet**, one clause, consistent with how the rest of the bullet
   list cites things tersely (e.g. line 24's "from `_config.md`'s menu" cite pattern already used
   elsewhere in this same file) - matches house style, no new subsection needed for one sentence.
3. **Does `project-workflow`'s version-bump mechanism need to be identified precisely in this
   plan, or is "bump it, whatever the repo's convention is" sufficient for a report-only plan?**
   **Recommend: leave for implementation** — this plan is PLAN-ONLY per the brief; the exact
   bump command/location (`plugins.yaml` version field, semver rule) is a one-line lookup at
   build time and does not change any of the A/B/C deliverables or their acceptance criteria.
