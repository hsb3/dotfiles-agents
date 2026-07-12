---
title: "Rename _meta/plans -> _meta/issues (planning-desk skill + toolkit)"
type: chore
status: draft
created: 2026-07-12
purpose: Source-grounded build plan for #82 -- rename the planning-desk's working-desk directory from _meta/plans/ to _meta/issues/ across the distributed skill primitive, its toolkit, sibling skills, and this repo's own live desk, then regenerate targets/.
notes: Drafted 2026-07-12 in worktree plans-wave. Consumer inventory re-verified fresh against the worktree (not the lead sweep's claims taken on faith) -- every citation below was re-grepped. PLAN-ONLY -- no rename performed. Must land LAST relative to #68/#69/#70/#83 (see Dependencies).
---

# Rename _meta/plans -> _meta/issues (planning-desk skill + toolkit)

_Renames the planning-desk's working-desk directory so the name states its purpose: each
subfolder is a GitHub issue's working desk, not a loose "plan." This is a skill-primitive
change with a large but fully enumerable consumer surface -- 36 enumerated files across
three categories (source primitive 15, sibling skills + tests + live forms 14, this repo's
docs/config layer 7), PLUS the desk's own content files (10 files / 38 prose hits today,
growing as the current plan wave adds folders -- re-derive with `rg` at execution time) --
plus a `targets/` regeneration. No part of this has shipped; the whole surface is RESIDUAL. This
issue's execution must land LAST among the current plan wave (#68, #69, #70, #83) because
those four also edit the toolkit scripts and skill docs this rename touches -- see
Dependencies._

Status: draft
Date: 2026-07-12

## Tracking

- Issue: #82 (`Rename _meta/plans -> _meta/issues (planning-desk skill + toolkit)`, OPEN,
  `type:chore`). Staged body: `_meta/plans/rename-plans-to-issues/issue-body.md` (verbatim
  copy of the live GitHub body, `gh issue view 82`).
- Origin: issue body states the directory name should state its purpose -- "each subfolder
  is a GitHub issue's working desk (`issue_body.md` = the contract, `plan.md` = build
  detail), not a loose 'plan.'"
- Relations: coordinates with #83 (`Require both issue_body.md and plan.md per issue
  folder`, OPEN, `type:feat`) per the issue body's own note -- "coordinate with the
  both-files rule (sibling issue) since both edit the same toolkit + skill." Also touches
  files that #68 and #69/#70 (all OPEN, `type:fix`) are separately fixing (toolkit blind
  spots, `.yml` issue forms, `PLANS-xx` frontmatter). See Dependencies for the landing-order
  rationale.
- Contract impact: **primitives-core change** -- edits `primitives-core/skills/
  planning-desk/**` and sibling skills, so it fires the roster-adjacent targets drift guard
  (no roster row is added/removed/renamed, so `make check` itself does not fire -- see Gate
  table) and requires `make build` to regenerate `targets/`.

## The problem (grounded in source)

**What EXISTS today: `_meta/plans/` is the name everywhere -- 36 enumerated files outside
the desk plus 10 desk-internal content files (38 hits), re-verified fresh in the worktree
(`rg -n "_meta/plans" --hidden --glob '!.git' --glob '!.claude/worktrees'`,
excluding `_meta/_archive/`). The count is a snapshot: the in-flight plan wave adds desk
folders, so a builder re-derives the list with the same `rg` sweep at execution time
rather than trusting any frozen number here.** The lead's sweep undercounted by omitting the live
`.github/ISSUE_TEMPLATE/*.yml` forms and the `repo-meta-structure` asset mirror of them;
both are confirmed consumers below and added to scope.

**Category A -- source primitive (the skill; edit here, distributed via `make build`):**

| File | Cite | What it hardcodes |
| ---- | ---- | ------------------ |
| `primitives-core/skills/planning-desk/SKILL.md` | lines 4,10,20,27,55,61,69-70,80-82,92-94,98,115,118-119 | prose + a bootstrap code block (`mkdir -p _meta/plans/_utils`, gitignore snippet, `_config.md` fill instructions) |
| `primitives-core/skills/planning-desk/references/plan.md` | lines 4,7,8,35,57 | doc-authoring mode instructions (`_meta/plans/<slug>/plan.md` path text) |
| `primitives-core/skills/planning-desk/references/issue-body.md` | lines 5,7,13,51,59,64,68 | doc-authoring mode instructions |
| `primitives-core/skills/planning-desk/references/loop.md` | lines 9,23 | review-loop mode instructions |
| `primitives-core/skills/planning-desk/references/toolkit.md` | lines 3,8-9 | toolkit invocation docs (`python3 _meta/plans/_utils/<script>`) |
| `primitives-core/skills/planning-desk/assets/plans-README.md` | lines 1,17,32 | the README template seeded into a new desk (title line `# _meta/plans`, invocation examples) |
| `primitives-core/skills/planning-desk/assets/ISSUE_TEMPLATE/bug.md` | line 28 | one prose pointer (`see _meta/plans/_config.md`) |
| `primitives-core/skills/planning-desk/assets/ISSUE_TEMPLATE/feature.md` | line 32 | one prose pointer (`see _meta/plans/_config.md`) |
| `primitives-core/skills/planning-desk/scripts/_utils/reconcile.py` | lines 6,15-16,29,248 | docstring + usage examples + one comment -- **textual only, see functional-vs-textual note below** |
| `primitives-core/skills/planning-desk/scripts/_utils/coverage.py` | lines 6,23-24,161 | docstring + usage examples + one f-string message -- textual only |
| `primitives-core/skills/planning-desk/scripts/_utils/sequence.py` | lines 15,29-30 | docstring + usage examples -- textual only |
| `primitives-core/skills/planning-desk/scripts/_utils/deps-suggest.py` | lines 25-26 | usage examples -- textual only |
| `primitives-core/skills/planning-desk/scripts/_utils/evidence-audit.py` | lines 21-24 | usage examples -- textual only |
| `primitives-core/skills/planning-desk/scripts/_utils/sync-bodies.py` | lines 8,16-19,109 | docstring + usage examples + one print message -- textual only |
| `primitives-core/skills/planning-desk/scripts/_utils/conformance.py` | lines 20-21 | usage examples -- textual only |

**`assets/_config.template.md` -- NOT a consumer.** The lead's brief listed it as an
in-scope asset; re-grepped fresh (`rg -n "_meta/plans"
primitives-core/skills/planning-desk/assets/_config.template.md`) and it returns zero hits
-- the template is written generically (it doesn't hardcode its own future path). Dropped
from the file-touch list; noted here so a builder doesn't waste a pass looking for text
that isn't there.

**Functional vs. textual hardcoding in the seven `_utils/*.py` scripts -- VERIFIED.** The
scripts resolve their working directory via `Path(__file__)`, not a hardcoded string:
`reconcile.py:30` `PLANS_DIR = Path(__file__).resolve().parent.parent` and
`coverage.py:38` `PLANS_DIR = Path(__file__).resolve().parent` both compute the desk root
from the script's own file location, and `sync-bodies.py:32` imports `PLANS_DIR` from
`reconcile.py` rather than recomputing a path string. **Consequence: renaming the directory
on disk (Category C) requires ZERO code changes to make the scripts work post-rename** --
they will resolve correctly wherever `_utils/` physically lives. Every `_meta/plans` string
match inside the seven scripts (rows above) is in a **docstring, `--help`-style usage
comment, or a printed status message** -- cosmetic, not functional. In scope per the issue
body's explicit claim ("they hardcode `_meta/plans`") and per acceptance criterion 1 (zero
`rg` hits outside `_archive/`), but a builder should not expect or attempt any change to
`PLANS_DIR` resolution logic itself -- there is none to make.

**Category B -- sibling skills + tests (distributed primitives that reference the desk
path; in scope because the issue's acceptance criterion is a repo-wide zero-hit grep, not
scoped to planning-desk alone):**

| File | Cite | Content |
| ---- | ---- | ------- |
| `primitives-core/skills/repo-meta-structure/SKILL.md` | lines 9,11,30 | prose (planning-doc frontmatter pointer, inbox pointer, reference-doc table row) |
| `primitives-core/skills/repo-meta-structure/references/checklist.md` | lines 31,105,106,120,121,131,144-149 | 3 checklist IDs' probe commands (`META-03`, `IGNORE-02/03/17/18`) plus the `PLANS-01..06` frontmatter-gate table -- **checklist IDs and probe path strings, not just prose; a naming-sensitive file** |
| `primitives-core/skills/repo-meta-structure/references/layout.md` | lines 94-95 | gitignore-negation explanation prose |
| `primitives-core/skills/repo-meta-structure/references/planning-docs.md` | lines 3,10,42-46,51,60,63,70-71 | doc-type table (`reference`/`spec`/`canon`/`proposed-issue`/`reprioritization-memo` rows), inbox section |
| `primitives-core/skills/repo-meta-structure/assets/gitignore.template` | lines 17,39-41 | the gitignore stanza this skill seeds into NEW repos (parallel structure to this repo's own `.gitignore`, Category C) |
| `primitives-core/skills/repo-meta-structure/assets/github/ISSUE_TEMPLATE/feature.yml` | line 57 | one prose pointer -- **NOT in the lead's original list; found by re-grep, added here** |
| `primitives-core/skills/repo-meta-structure/assets/github/ISSUE_TEMPLATE/bug.yml` | line 50 | one prose pointer -- **NOT in the lead's original list; found by re-grep, added here** |
| `primitives-core/skills/repo-compliance-audit/scripts/audit.py` | line 318 | one docstring line (`Every *.md under _meta/plans/ ...`) |
| `primitives-core/skills/mise-en-place-scaffold/scripts/scaffold.py` | lines 127,443 | one prose comment + one docstring line (mirrors audit.py's) |
| `primitives-core/skills/dotfiles-expert/references/repo-and-stow.md` | line 59 | one table row describing `_meta/` layout |
| `tests/test_audit.py` | line 84 | test fixture string `"_meta/plans/inbox"` -- **verify whether this asserts a path that must track the rename, or is an independent fixture; treat as functional if the audit's inbox-detection logic keys on this literal** |
| `tests/test_scaffold.py` | line 704 | `self.assertIn("_meta/plans/.gitkeep", planned)` -- **functional test assertion; must be updated in lockstep with `scaffold.py`'s gitignore.template output or the test fails post-rename** |

**Category B, additionally in scope -- live repo issue-template forms, found by re-grep, NOT
in the lead's brief:**

| File | Cite | Content |
| ---- | ---- | ------- |
| `.github/ISSUE_TEMPLATE/feature.yml` | line 54 | prose pointer to `_meta/plans/_config.md` (this repo's actual live GitHub issue form, distinct from the skill's seeded asset) |
| `.github/ISSUE_TEMPLATE/bug.yml` | line 47 | prose pointer to `_meta/plans/_config.md` |

**Category B carries a STANDARD-vs-INSTANCE tension the string-substitution framing
hides.** `repo-meta-structure` is not just another consumer: it is the distributed
CROSS-REPO STANDARD, and its checklist rows define `_meta/plans/` as what "conformant"
MEANS -- `META-03` (`path-exists: _meta/plans/`, checklist.md:31), `IGNORE-02/03/17/18`
(probe paths, checklist.md:105-106,120-121), and the `PLANS-01..06` scope
(checklist.md:133). Two consequences a builder must not discover mid-PR:

1. **The checklist's own contract says "the stable IDs are the machine contract -- they
   never change" (checklist.md:9-11).** This rename keeps every ID but rewrites the Check
   column's probe ARGUMENT (e.g. `META-03` starts probing `_meta/issues/`). The contract
   text forbids ID changes, not argument changes -- but changing what an existing ID
   measures is a semantic break for any consumer tracking verdicts by ID over time.
2. **Cross-repo blast radius.** Every repo that adopted the standard with `_meta/plans/`
   (e.g. `mhi-raptorxai/raptorxai-infra`, per #68/#69/#70's origin reports) audits as
   NON-CONFORMANT against the updated checklist until it performs the same rename -- or,
   if the checklist is left unchanged, dotfiles-agents itself fails its own audit
   (`META-03`, `IGNORE-02/03`) the moment its desk moves. There is no state in which both
   the old-path adopters and the renamed instance pass the same checklist rows.

Whether the STANDARD renames with the instance (adopters migrate, tracked as follow-up
issues), the checklist gains either-path tolerance (or per-repo variance via
`_meta/mise-en-place.yml`, checklist.md:21-23), or this repo declares variance, is a
genuine owner decision -- Open Question 5. The issue body's acceptance criteria assume
the simple both-rename path; this plan records the tension rather than papering over it.

These two `.yml` files above are the **live, GitHub-facing issue forms for this repo** --
they render in the "New Issue" picker. They are near-duplicates of the `planning-desk/assets/ISSUE_TEMPLATE/
*.md` and `repo-meta-structure/assets/github/ISSUE_TEMPLATE/*.yml` seed templates but are
NOT generated from them (no codegen link found); each must be hand-edited independently.
Missing this pair would leave a live, user-facing GitHub form pointing at a path that no
longer exists after the rename.

**Category C -- this repo's live desk (rename on disk + edit references):**

- `_meta/plans/` itself -> `_meta/issues/`, via `git mv` of EVERY subfolder and file
  present at execution time -- enumerated by `ls _meta/plans/` when the rename runs, NOT
  from any frozen list in this plan. As of the main tree today that is 9 committed plan
  folders (`agnostic-base-format/`, `extender-ideas-backlog-seed/`,
  `externals-clone-at-build/`, `fleet-dashboard-pilot/`, `frontend-extenders-curation/`,
  `project-workflow-v2/`, `ra-platform-commands-skill/`, `retire-hsb3-custom-plugins/`,
  `roster-provenance-field/`), `_utils/` (8 scripts), `README.md`, `_config.md`, and
  `project-workflow-conformance.md`; the in-flight plan wave (#68/#69/#70/#82/#83) adds
  FIVE more folders (`toolkit-body-only-folders/`, `issue-template-format-align/`,
  `plan-frontmatter-schema/`, `rename-plans-to-issues/`, `require-both-artifacts/`, each
  carrying both `issue-body.md` and `plan.md`) that will be merged before #82 executes
  (it lands last) and must be moved too.
- **Desk-internal CONTENT edits -- a bare `git mv` is NOT sufficient.** The desk's own
  markdown files carry literal `_meta/plans` prose that survives the move: 10 files / 38
  hits in the main tree today (`README.md` x3, `project-workflow-conformance.md` x1,
  `ra-platform-commands-skill/plan.md` x14, `project-workflow-v2/plan.md` x6,
  `fleet-dashboard-pilot/plan.md` x6, `frontend-extenders-curation/plan.md` x3 +
  `issue-body.md` x1, `extender-ideas-backlog-seed/plan.md` x2,
  `externals-clone-at-build/plan.md` x1, `retire-hsb3-custom-plugins/plan.md` x1 --
  re-derive with `rg -c "_meta/plans" _meta/plans/ -g '!_utils'` at execution time, since
  the five wave folders, including THIS plan, add many more). Without these content edits
  the acceptance grep ("zero hits outside `_meta/_archive/`") fails on the renamed desk's
  own files. Whether staged `issue-body.md` copies may be edited locally without pushing
  to the live GitHub bodies is Open Question 6.
- `.gitignore` — **CORRECTION to the brief's line numbers.** Re-verified against the
  worktree: the negation stanza is lines **21-22** (`!_meta/plans/`, `!_meta/plans/**`), the
  Finder-litter re-inclusion guards are lines **24-25** (`_meta/plans/**/.DS_Store`,
  `_meta/plans/.DS_Store`), not "17-25" as stated in the task brief -- **line 17 is the base
  `_meta/*` ignore rule and correctly contains no `plans` substring; it was miscounted into
  the range, not actually a hit.** No line 44 hit either (line 44 is the Python-section
  header comment, unrelated) -- the brief's "and line 44" claim does not check out against
  this worktree's current `.gitignore`; the four real hits are lines 21, 22, 24, 25 only.
- `CLAUDE.md:24` -- **already partially edited.** Reads `_meta/plans/` → `_meta/issues/`
  (arrow notation) in the Strategy-Desk-vs-Engineering-Desk bullet -- someone pre-annotated
  the intended rename ahead of execution. This rename must finish the job: replace with the
  plain new path, not leave the arrow gloss in permanent prose.
- `docs/governance-map.md` -- lines 36, 50, 115, **same arrow-gloss pattern** already
  present (`_meta/plans/` → `_meta/issues/`) at two of three sites; line 115 has no arrow.
  All three need the final single-name form.
- `docs/plugins/project-workflow.md:137` -- one prose mention, no arrow gloss yet.
- `docs/sops/issues-and-plans.md` -- lines 11, 35, 43: prose + a directory-tree code block.
- `_meta/HANDOFF.md` -- lines 7, 18, 59 AT HEAD: prose in three places, including the
  archival convention note (`_meta/_archive/<issue>-<slug>.md` naming) -- that naming
  convention itself is untouched by this rename (archive folder name doesn't change), only
  the mention of `_meta/plans/_utils/` needs updating. **Line numbers pinned to HEAD:** the
  main tree already carries an uncommitted HANDOFF edit that shifts these hits (to 7, 27,
  64 in the current working tree); HANDOFF.md churns every session, so the builder re-greps
  this file at execution time rather than trusting any line numbers here.
- `_meta/briefings/2026-07-05-project-roadmap/sources.md` -- lines 10, 17, 18: a dated
  briefing snapshot citing toolkit output and a plan path. **Recommend leaving as-is** --
  per project-protocol, briefings are dated point-in-time artifacts, not living docs; a
  historical citation to a since-renamed path is expected drift, parallel to how
  `_archive/` is excluded from the acceptance grep. Flagged as an open question (below)
  since the issue's acceptance criterion is textually "zero hits outside `_archive/`" and
  briefings are not `_archive/`.
- `primitives-core.yaml:549` -- one line, the planning-desk roster entry's `summary:` field
  text ("Stand up and run a source-grounded planning desk under `_meta/plans/`"). This is
  the roster's own registered summary string -- editing it does NOT rename or re-key the
  roster entry (the `id: planning-desk` stays; only free-text `summary:` changes), so the
  roster drift guard (`make check`) does not fire from this edit alone.
- `AGENTS.md` -- **VERIFIED CLEAN.** Re-grepped fresh; zero hits. The issue body lists
  `AGENTS.md` as an expected consumer but it currently carries no `_meta/plans` text in
  this worktree. No action needed; note this so a builder doesn't hunt for a phantom edit.
- `_meta/plans/_config.md` and `assets/_config.template.md` -- **VERIFIED CLEAN, self-
  referential paths not present in their own body text.** Neither file names its own path
  inside its prose. Only the directory rename (the folder itself moving) applies; no text
  edit inside either file.

**MISSING / OUT OF SCOPE (explicitly excluded, confirmed):**

- `_meta/_archive/40-docs-planning-standard.md` -- 3 hits, historical, excluded per the
  issue's acceptance criterion ("zero hits outside `_meta/_archive/`"). No action.
- `targets/**` (opencode, claude-code, claude-agents mirrors of every Category A/B file) --
  **generated, never hand-edited.** Confirmed present with 60+ files under `targets/` that
  mirror Category A/B content; these self-correct via `make build` after Category A/B lands
  (Deliverable C, below). Do not hand-edit; the drift guard (`make build-check`) fails any
  PR whose `targets/` is stale relative to source.
- Sibling repo `ra-platform`'s planning desk, "if it adopted the skill" (per issue body) --
  **out of this repo's PR.** Not checked in this plan (would require access to that repo);
  recorded as an external follow-up, not a deliverable here.

## Deliverables

**A -- Source-primitive rename.** Edit the 15 Category-A files (`planning-desk/SKILL.md`,
4 `references/*.md`, `assets/plans-README.md`, 2 `assets/ISSUE_TEMPLATE/*.md`, 7
`scripts/_utils/*.py` docstrings/usage comments) to say `_meta/issues/` throughout. No
functional code change to any script (per the `PLANS_DIR = Path(__file__)` finding above)
-- text-only edits.
**Acceptance:** `rg -n "_meta/plans" primitives-core/skills/planning-desk/` returns zero
hits; all seven `_utils/*.py` scripts still run clean (`python3 --help` / dry-run on each,
no import errors) since no functional logic changed.

**B -- Sibling-skill + test rename.** Edit the 14 Category-B files: the 12 sibling-skill
files (`repo-meta-structure`'s 7 reference/asset files including its two `.yml` issue
form assets and `checklist.md`'s
`PLANS-xx`/`IGNORE-xx` IDs, `repo-compliance-audit/scripts/audit.py`,
`mise-en-place-scaffold/scripts/scaffold.py`, `dotfiles-expert/references/repo-and-
stow.md`) plus the 2 live `.github/ISSUE_TEMPLATE/*.yml` forms and the 2 test files
(`tests/test_audit.py:84`, `tests/test_scaffold.py:704`).
**Acceptance:** `rg -n "_meta/plans" primitives-core/skills/repo-meta-structure/
primitives-core/skills/repo-compliance-audit/ primitives-core/skills/mise-en-place-
scaffold/ primitives-core/skills/dotfiles-expert/ .github/ISSUE_TEMPLATE/ tests/` returns
zero hits; `python3 -m pytest tests/test_audit.py tests/test_scaffold.py` (or the repo's
equivalent test invocation) passes -- test_scaffold.py's `assertIn("_meta/issues/.gitkeep",
planned)` must match whatever `gitignore.template`'s Category-B edit actually emits, so B's
scaffold.py and gitignore.template edits and the test assertion land together, not in
separate passes.

**C -- Live-desk rename + regenerate.** `git mv _meta/plans _meta/issues` (preserves
history; covers every folder present at execution time, including the five wave folders
merged by then -- enumerate with `ls`, not this plan's snapshot). THEN edit the desk's own
content: the 10+ desk-internal `*.md` files carrying literal `_meta/plans` prose (38 hits
today; re-derive with `rg` since the wave folders add more, including this plan). Edit
`.gitignore` lines 21-22/24-25, `CLAUDE.md:24`,
`docs/governance-map.md:36,50,115`, `docs/plugins/project-workflow.md:137`,
`docs/sops/issues-and-plans.md:11,35,43`, `_meta/HANDOFF.md` (re-grep -- see the
line-drift note above), `primitives-core.yaml:549` (summary text only). Then `make build`
to regenerate `targets/`
from the Category A/B source edits. Bump `plugins.yaml:42` `project-workflow` version from
`0.2.4` to `0.2.5` (planning-desk is a `project-workflow`-plugin member per
`primitives-core.yaml:552`, `plugins: [project-workflow]`).
**Acceptance** (matches issue checkboxes verbatim): `rg -n "_meta/plans"` repo-wide returns
zero hits outside `_meta/_archive/`; `python3 _meta/issues/_utils/reconcile.py` runs clean;
`make ci` green; `targets/` regenerated with no hand-edits (`make build-check` passes);
skill docs and `_config.md` refer to `_meta/issues/` throughout.

## Gate & contract hygiene

| Gate | Fires on #82? | Why |
| ---- | -------------- | --- |
| CI aggregate (make ci) | yes | acceptance criterion states `make ci` green explicitly |
| Roster drift guard (make check) | no | no primitive added, removed, or renamed by ID -- `planning-desk` keeps its `id:`; only its `summary:` free text and the skill's internal file contents change |
| Targets drift guard (make build-check) | yes | Deliverable A/B edits `primitives-core/skills/**`; `make build` must run before commit or CI fails on stale `targets/` |
| Naming taxonomy (make names) | no | no NEW primitive or plugin named; `docs/naming.md` prefix rules are not engaged by a path-string rename inside existing primitives |
| YAML / workflow lint (yamllint) | yes, narrow | `.github/ISSUE_TEMPLATE/*.yml` and `repo-meta-structure/assets/github/ISSUE_TEMPLATE/*.yml` are touched (prose-only edits inside YAML `body:` blocks) -- run yamllint on these two pairs; no `.github/workflows/` file is touched so actionlint does not fire |
| Canonical-doc amendment | yes | `CLAUDE.md:24` and `docs/governance-map.md` (a spine doc per `docs/governance-map.md` itself) both describe the `_meta/plans/` path as current behavior; both must be amended in the SAME PR as Deliverable C, not deferred |

`plugins.yaml` version bump (`0.2.4` -> `0.2.5`) is a project-workflow-plugin convention,
not a listed `_config.md` gate row, but the issue body's own Dependencies & gates section
names it explicitly ("`project-workflow` plugin version bump") -- included in Deliverable C.

## Parallelism + landing order

| Unit | Scope | Depends on | Notes |
| ---- | ----- | ---------- | ----- |
| A -- source-primitive text edits | 15 files under `planning-desk/` | none | could parallelize by file since each edit is independent text substitution, but the blast radius is small enough (15 files) that ONE owner doing all of A serially is simpler than coordinating parallel writers on a single skill directory |
| B -- sibling-skill + test edits | 14 files across 4 sibling skills + `.github/ISSUE_TEMPLATE/` + `tests/` | none, but B's `scaffold.py`+`gitignore.template`+`test_scaffold.py` are a linked trio (see below), and B's checklist edits hang on Open Question 5's standard-vs-instance decision | the `checklist.md` PLANS-xx IDs, `scaffold.py`, `gitignore.template`, and `test_scaffold.py` form ONE serialized sub-chain (shared string contract: what the template emits, what the test asserts) -- do not split across two agents |
| C -- live-desk `git mv` + desk-content edits + doc edits + `make build` | `_meta/plans/` -> `_meta/issues/`, 10+ desk-internal content files, 7 doc/config files, `plugins.yaml` | A and B fully landed | must run LAST within this issue: `make build` needs A+B's source edits in place to regenerate a `targets/` that matches, and the `git mv` needs A+B's text edits already done or the moved files still say `_meta/plans` internally |

Within this issue, A and B can run as parallel agents (disjoint file scopes: A is
`planning-desk/` only, B is the four sibling skills + tests + `.github/`). C serializes
after both. No timelines -- landing order only.

## Dependencies -- sequencing against the wave (#68, #69, #70, #83)

**#82 must land LAST relative to #68, #69, #70, and #83.** All four are OPEN
(`gh issue view`, checked 2026-07-12) and each edits files this rename also touches:

- **#68** (`type:fix`, "governance toolkit is blind to issue-body-only plan folders") fixes
  `reconcile.py`'s handling of folders that hold only `issue-body.md` -- directly the same
  file this plan's Deliverable A edits (docstrings only, but #68 will touch the same
  file's logic).
- **#69** (`type:fix`, "planning-desk seeds .md issue templates; repo-meta-structure
  requires .yml issue forms") fixes exactly the `ISSUE_TEMPLATE/*.md` -> `*.yml` gap this
  plan's Category A/B tables list (`planning-desk/assets/ISSUE_TEMPLATE/{bug,feature}.md`
  and the `.yml` mirrors) -- same files, different concern (format, not path string).
- **#70** (`type:fix`, "planning-desk artifacts lack PLANS-xx frontmatter") fixes the
  `PLANS-01..06` checklist gate this plan's Category B table cites at
  `repo-meta-structure/references/checklist.md:144-149` -- same file, same line range.
- **#83** (`type:feat`, "Require both issue_body.md and plan.md per issue folder") is
  explicitly named in the live issue #82 body itself ("coordinate with the both-files rule
  (sibling #83) since both edit the same toolkit + skill") -- confirmed verbatim in the
  fetched body's Dependencies & gates section.

**Reason #82 goes last, not first:** #82 rewrites path strings across every file that #68,
#69, #70, and #83 ALSO edit (the toolkit scripts and skill docs). If #82 lands first, each
of the other four must rebase their in-flight edits onto already-renamed paths -- churn and
merge conflict risk across four separate branches touching the same handful of files. If
#82 lands last, it performs one clean sweep over files the other four have already
finished fixing, with no rebase cost. The plan wave's five new desk folders (one per
issue, each with both artifacts) will have merged by then and ride along in the `git mv`.
Note the recorded contradiction: #83's own body asks to land "after the `_meta/issues`
rename" -- the inverse of this ordering; the owner picks one (see #83's and #68's plans,
which surface the same conflict).

## Open questions / owner decisions

1. **`git mv` vs. `rm` + `add` to preserve history?** **Recommend: `git mv`.** Preserves
   blame/log continuity across the rename for every file under `_meta/plans/`; `rm`+`add`
   would show as a delete+create pair in history with no rename detection guarantee across
   ~10 subfolders. No functional downside to `git mv`.
2. **Rename the `plans-README.md` asset FILENAME to `issues-README.md`, or keep the
   filename and only change its content?** **Recommend: keep the filename, change content
   only.** The asset's filename (`plans-README.md`) is an internal implementation detail of
   the skill's `assets/` folder -- nothing outside the skill's own `SKILL.md` bootstrap
   step references the asset by that exact filename in a way a rename would improve; the
   content (title `# _meta/plans` -> `# _meta/issues`, path examples) is what a fresh-desk
   user actually reads. Renaming the file adds one more moving part (updating the
   `SKILL.md` bootstrap step's `cp assets/plans-README.md _meta/plans/README.md` line to
   reference a new source filename) for no externally visible benefit. Flagging as open
   since it's a legitimate judgment call, not a forced default.
3. **Does #83's `issue_body.md` (underscore) vs. this repo's current `issue-body.md`
   (hyphen) naming get resolved here or in #83?** **Recommend: #83 owns the artifact-
   filename question.** #82's scope is the DIRECTORY name (`_meta/plans/` ->
   `_meta/issues/`); #83's scope (per its title, "Require both issue_body.md and plan.md
   per issue folder") is the per-folder ARTIFACT naming convention, including the
   underscore-vs-hyphen question. Conflating the two inside #82 would widen its blast
   radius into territory #83 already owns; #82's plan (this document) does not touch
   `issue-body.md`/`issue_body.md` naming anywhere in its deliverables.
4. **`_meta/briefings/2026-07-05-project-roadmap/sources.md` -- amend or leave as
   historical drift?** **Recommend: leave as-is.** It is a dated briefing snapshot (project-
   protocol taxonomy: briefings are point-in-time, not living docs), and the issue's
   acceptance criterion excludes only `_meta/_archive/` by name -- briefings are a separate
   `_meta/` subfolder with different tracking rules (fully tracked per `.gitignore:26-31`,
   but not doc-maintenance-live). If the owner wants strict zero-hits with no carve-out
   beyond `_archive/`, this file needs one more edit; flagged rather than defaulted into
   Deliverable C's file list, since including it would make the acceptance grep's "outside
   `_meta/_archive/`" phrasing formally false if left unedited.
5. **Does the repo-meta-structure STANDARD rename with this instance, or gain tolerance?**
   (See the standard-vs-instance subsection under Category B.) Three options: (a) rename
   the standard's checklist probe paths in this same PR and file follow-up migration
   issues for every adopting repo (e.g. raptorxai-infra) -- adopters audit non-conformant
   until they migrate; (b) teach the checklist / audit to accept EITHER `_meta/plans/` or
   `_meta/issues/` (or route it through the `_meta/mise-en-place.yml` per-repo variance
   mechanism, checklist.md:21-23) -- preserves adopters but weakens the single-name
   standard; (c) leave the standard at `_meta/plans/` and declare variance for this repo
   -- cheapest, but the standard's home repo then permanently diverges from the standard
   it distributes. **Recommend (a)**: the issue's intent is that the NAME states the
   purpose, and a standard whose home repo diverges from it is worse than a one-time
   adopter migration; the checklist IDs stay stable (only probe arguments change), and
   the adopter migrations are small, mechanical follow-ups. The blast radius must be
   priced consciously, though -- hence an open question, not a silently applied default.
6. **May the desk's staged `issue-body.md` files be content-edited for the rename without
   pushing to GitHub?** The byte-identity convention (checklist.md:136-138 exemption
   rationale; `sync-bodies.py`'s DIFFERS check) says a staged body mirrors its live
   issue. Editing `_meta/plans` mentions inside staged bodies (e.g.
   `frontend-extenders-curation/issue-body.md`) breaks byte-identity until the live
   bodies are updated too. **Recommend:** update the live GitHub issue bodies in the same
   execution (owner-approved `sync-bodies.py --push` after local edits), so the
   acceptance grep passes AND `sync-bodies.py` stays clean. Alternative: exempt staged
   bodies from the acceptance grep like `_archive/`, at the cost of a permanently
   qualified acceptance criterion.
