---
title: "Build plan — project-workflow v2: pw- naming, ops/output cohesion skill, plugin README"
type: spec
status: draft
created: 2026-07-03
purpose: Source-grounded build plan for #27 — the verified rename set, the pw-workflow orchestrator, the translate.py README pass-through, gates, landing order, and the owner decisions the stale issue body forces.
notes: Drafted 2026-07-03. The issue body (2026-07-01) predates #62 (membership 10 to 14, plugin 0.2.0) and #64 (0.2.1, naming lint in ci); its counts and two of its gate claims are corrected here against live source. Design of record on the cowork desk (analyses/project-workflow-v2-design.md, decision 0001).
---

# feat: project-workflow v2 — pw- naming, ops/output cohesion skill, plugin README

_Nothing from #27 has shipped — the full scope (rename, `pw-workflow`, plugin README
pass-through, description rewrite, rebuild) is the residual. But the ground moved under the
issue body since it was drafted (2026-07-01): #62 added the four standards skills to the
plugin (membership is now 13 skills + 1 agent, not 9 + 1) and bumped it to 0.2.0; #64 bumped
it to 0.2.1 today; a naming lint (`make names`) now runs in CI; and a plugin user guide now
exists at `docs/plugins/project-workflow.md` that the rename must also update. This plan
keeps the issue's 10-primitive rename set (the four standards skills are a deliberate
open question, recommended NO), retargets every stale count and version, and adds the
doc/test surfaces the issue body could not have known about._

Status: draft
Date: 2026-07-03

## Tracking

- Issue: #27 (open, `enhancement`).
- Origin: cowork strategy desk — design of record
  `~/Documents/Claude/Projects/dotfiles-agents-cowork/analyses/project-workflow-v2-design.md`
  (status `decided`, 2026-07-01); gate exemption for the one net-new skill recorded at
  `~/Documents/Claude/Projects/dotfiles-agents-cowork/_structure/decisions/0001-gate-exempt-primitives-in-proven-plugins.md`.
- Relations: #40 / PR #62 (added the 4 standards skills to this plugin + bumped 0.2.0 —
  changed this plan's membership counts; its plan is archived at
  `_meta/_archive/40-docs-planning-standard.md`); #35 / PR #64 (2c6a960, today: plugin
  0.2.1, archive-dir rename); #24 / PR #60 (loadability smoke — the natural post-rename
  proof). No open issue conflicts on the same files were found.
- Contract impact: **full generated-targets surface.** Touches `primitives-core/` (10 dir/file
  renames + 1 new skill), `primitives-core.yaml` (10 id+source edits + 1 new entry),
  `plugins.yaml` (version + description), and `scripts/translate.py` (README pass-through).
  `targets/` and both marketplace catalogs are regenerated, never hand-edited
  (`_meta/plans/_config.md:38-39`).

## The problem (grounded in source)

**What exists:**

- The plugin has **14 members, not the issue's 10**: 13 skills + 1 agent tagged
  `plugins: [project-workflow]` in `primitives-core.yaml` — the original ten
  (`agent-dot-md-authoring` :22, `board-reporting` :42, `board-triage` :52, `comms` :102,
  `diagrams` :171, `github-project-board` :223, `handoff` :233, `planning-desk` :523,
  `readme-value-and-proof` :553, agent `board-analyst` :637) plus the four standards skills
  added by #62 (`memory-taxonomy` :373, `mise-en-place-scaffold` :383,
  `repo-compliance-audit` :563, `repo-meta-structure` :573). The issue's acceptance
  criterion "grep count unchanged at 10" is stale.
- Plugin metadata: `plugins.yaml:41-43` — `project-workflow`, `version: "0.2.1"` (bumped
  today by #64, commit 2c6a960, explicitly "content change, not roster membership"), and a
  description that already names the output work ("CLAUDE.md/AGENTS.md, value-and-proof
  READMEs, diagrams, and status comms") — the issue's deliverable D ("undersells the output
  family") is **already substantially done** by the #62-era rewrite; only family framing
  (ops vs output) is arguably missing.
- No naming convention across members, unlike `langchain-*` / `obsidian-*` /
  `deep-agents-*`; the taxonomy pattern is `<domain>-<capability>` for skills and
  `<domain>-<role>[-<verb>]` for agents (`docs/naming.md:13-14`).
- **A naming lint now exists and runs in CI**: `make names` = `scripts/check_naming.py`
  (Makefile:13-14), part of `make ci` (Makefile:28), which is all CI runs
  (`.github/workflows/ci.yml:20`). It enforces kebab-case, no client tokens, no vendor in
  id (`scripts/check_naming.py:1-22`) — it does NOT enforce prefix families, so `pw-`
  conformance stays a manual check. Both the issue body and the gate menu
  (`_meta/plans/_config.md:35`, "no auto-lint yet") are stale on this.
- No cohesion layer: no router/index skill exists; `primitives-core/skills/` has no
  `pw-workflow` and the only intent-to-skill routing table lives in the (repo-docs, not
  bundle) user guide `docs/plugins/project-workflow.md:59-62` — with old names, and a stale
  "(v0.1.0)" in its own intro (`docs/plugins/project-workflow.md:9`).
- No plugin README mechanism: `scripts/translate.py`'s plugin-assembly loop
  (`scripts/translate.py:387-437`) writes only `.claude-plugin/plugin.json`
  (:397-408), copies member skills/agents (:410-419), and copies per-plugin hook fragments
  from `primitives-core/hooks/<p>/` (:421-428). There is no `primitives-core/plugins/`
  directory at all (verified by listing `primitives-core/`: agents, hooks, mcp, skills,
  README.md), and no generated plugin under `targets/claude-code/plugins/` carries a README.
- Validators check frontmatter `name`/`description` **presence only**
  (`scripts/validate_primitives.py:127-129`) — nothing machine-enforces
  frontmatter-name == roster-id, so the rename's `name:` edits need a manual acceptance
  check.
- Old-id cross-references confirmed in source (the rename blast radius, all verified on
  disk):
  - Intra-plugin: `primitives-core/skills/board-triage/SKILL.md:68` (names
    `board-analyst`), `board-reporting/SKILL.md:50` (`board-triage`),
    `comms/SKILL.md:3,62,64` (`handoff`, `readme-value-and-proof`),
    `planning-desk/SKILL.md:2,119` + `assets/_config.template.md:3` (self-references).
  - Standards-skill prose (added by #62, not in the issue):
    `mise-en-place-scaffold/SKILL.md:64,66`, `scripts/scaffold.py:25,28,207-209,223-224,277,282,346,737`,
    `references/manifest.md:29-31`; `repo-meta-structure/references/layout.md:18,45`,
    `references/planning-docs.md:5`, `assets/github/ISSUE_TEMPLATE/{bug,epic,feature}.yml:6`.
  - Repo docs: `docs/plugins/project-workflow.md` (throughout, e.g. :59-62,106-137,185-200),
    `docs/sops/README.md:19-20`, `docs/sops/milestones-and-board.md:13-14,82`.
  - Tests use `board-analyst` as fixture names: `tests/test_smoke.py:17,65`,
    `tests/test_translate.py:120,133,142,158`.
  - Desk config prose: `_meta/plans/_config.md:3` ("planning-desk authoring modes").
- Machine state: the installed cache `~/.claude/plugins/cache/dotfiles-agents/project-workflow/`
  holds 0.1.0, 0.2.0, and 0.2.1 — the update loop works; post-merge the machine needs one
  more update to pick up the renamed skills.

**What's missing:**

- Any shared `pw-` prefix on the ten workflow members (dirs, roster ids, frontmatter names).
- The `pw-workflow` orchestrator skill (and its roster entry).
- A per-plugin README source location + a `translate.py` copy step for it.
- An explicit ops/output family framing in the `plugins.yaml` description (partial — see
  above) and in any artifact that travels with the bundle.
- A version bump carrying the membership change (renames + one addition are
  roster-membership changes; per the rule adopted at #40 decision 4
  (`_meta/_archive/40-docs-planning-standard.md:167`) and applied by #64's patch-vs-minor
  distinction, this is a **minor** bump: 0.2.1 to 0.3.0). That rule itself is still written
  down only in the archived plan + a commit message — nowhere normative.

## Deliverables

**A — Rename the ten original members under `pw-`.**
Scope: exactly the issue's table (design of record, confirmed 2026-07-01) — the four
standards skills are excluded (owner decision 1).

| Type | Current id | New id |
| ---- | ---------- | ------ |
| skill | planning-desk | pw-plan |
| skill | github-project-board | pw-board-setup |
| skill | board-triage | pw-board-triage |
| skill | board-reporting | pw-board-report |
| skill | handoff | pw-handoff |
| skill | comms | pw-comms |
| skill | diagrams | pw-diagrams |
| skill | agent-dot-md-authoring | pw-agent-md |
| skill | readme-value-and-proof | pw-readme |
| agent | board-analyst | pw-board-analyst |

Each rename is: `git mv` the source dir (agent: the `.md` file), update the roster entry's
`id:` + `source:`, update the frontmatter `name:` to match, and fix intra-plugin
cross-references (the "Intra-plugin" list above).
Acceptance:
- None of the 10 old paths exist under `primitives-core/skills/` or `primitives-core/agents/`;
  the 10 new `pw-*` paths do.
- `grep -c "plugins: \[project-workflow\]" primitives-core.yaml` returns **15**
  (10 renamed + 4 standards + pw-workflow), and every renamed entry's `id:` matches `^pw-`.
- For each new dir, frontmatter `name:` equals the roster `id:` (manual grep — not
  machine-enforced, see `validate_primitives.py:127-129`).
- `make check` passes (roster-vs-disk drift), `make names` passes (kebab + token rules).

**B — Author `pw-workflow`** — new skill at `primitives-core/skills/pw-workflow/SKILL.md`
plus its roster entry (`type: skill`, `shelf: core`, `origin: authored`,
`targets: [claude-code, opencode, claude-agents]`, `plugins: [project-workflow]`;
disposition per owner decision 3). Content per the design doc: routes intent across all 14
members (both the renamed ten and the four standards skills — it is the index over the
whole plugin as it exists today); narrates the ops loop (plan, stand up board, weekly
triage, status report, handoff) and the output layer (comms, diagrams, agent-md, readme)
plus the standards family; carries the actions-not-phases framing explicitly (every member
independently invokable, nothing gates on a prior step); triggers on entry-point language
("what's the project workflow here", "what should I run next", "run the weekly loop",
"what do I use to write a status update"). No workbench incubation — decision 0001 on the
desk exempts thin router/index skills authored directly into a proven plugin.
Acceptance:
- `primitives-core/skills/pw-workflow/SKILL.md` exists; description covers the triggers
  above; body documents both families + actions-not-phases; description contains no
  angle-bracket tags (`make validate` XML-tag guard, `validate_primitives.py:130-137`).
- Roster entry present; `make check` and `make validate` pass.
- The routing table names all 14 current members by their post-rename ids (grep: zero old
  ids inside `pw-workflow/`).

**C — Plugin README source + `translate.py` pass-through.**
New source file `primitives-core/plugins/project-workflow/README.md` (new source location —
`primitives-core/plugins/` does not exist yet; mirrors the per-plugin hooks pattern at
`primitives-core/hooks/<plugin>/`, consumed at `translate.py:421-428`). Extend the plugin
assembly loop: after the `plugin.json` write (`translate.py:405-408`), if
`primitives-core/plugins/<p>/README.md` exists, copy it to
`targets/claude-code/plugins/<p>/README.md`. Generic to every plugin; a no-op when absent.
README content: the human front door — what the plugin is, the ops/output/standards family
split, the routing table, actions-not-phases, install pointer; cross-link the deep user
guide (`docs/plugins/project-workflow.md`) rather than duplicating it (owner decision 6).
Note for the builder: `check_roster.py` walks `primitives-core/` for roster-vs-disk drift —
verify the new `plugins/` subtree is not misread as an unrostered primitive (its walk keys
on `skills/`/`agents/` shapes; confirm and add a test either way).
Acceptance:
- After `make build`, `targets/claude-code/plugins/project-workflow/README.md` exists and
  is byte-identical to the source (`cmp` exit 0).
- No other plugin's target dir gains a README (no-op proof).
- A unit test covers both branches (README present / absent); `make test` passes.
- `make check` still passes with `primitives-core/plugins/` present.

**D — `plugins.yaml`: description framing + version 0.3.0.**
Rewrite the `project-workflow` description (`plugins.yaml:43`) to name the ops/output
family split explicitly (the current text already lists the output deliverables, so this is
a framing edit, not a rescue); bump `version:` 0.2.1 to 0.3.0 (roster-membership change:
10 renames + 1 addition; rule per #40 decision 4, precedent per #64's patch-only bump).
If owner decision 4 approves, add the one-line membership-bump rule to
`docs/naming.md` in the same commit.
Acceptance:
- `plugins.yaml` description mentions both families; version reads `0.3.0`.
- Regenerated `plugin.json` + both marketplace catalogs carry 0.3.0 (root catalog currently
  at `.claude-plugin/marketplace.json:97`).

**E — Repo-docs and residual-reference sweep.**
Update every non-generated old-id reference outside the plugin sources: the user guide
`docs/plugins/project-workflow.md` (member tables :59-62, per-skill sections :106-137,
footprint/safety tables :185-200, the stale "(v0.1.0)" at :9, and a new `pw-workflow` row),
`docs/sops/README.md:19-20`, `docs/sops/milestones-and-board.md:13-14,82`, the
standards-skill prose (scaffold.py owner-note strings :207-209 etc., manifest.md :29-31,
layout.md :18,45, planning-docs.md :5, ISSUE_TEMPLATE assets :6), test fixture names
(`tests/test_smoke.py:17,65`, `tests/test_translate.py:120,133,142,158`), and
`_meta/plans/_config.md:3` prose. While in `_config.md`, correct the stale naming-gate row
(:35, "no auto-lint yet") to cite `make names` — the config's own header says to update it
when gates change.
Acceptance:
- `git grep -l -E "planning-desk|github-project-board|board-triage|board-reporting|board-analyst|agent-dot-md-authoring|readme-value-and-proof" -- ':!targets' ':!_meta/_archive' ':!_meta/plans'`
  returns nothing (archive and desk history keep old names as provenance; targets checked
  post-build below). Spot-check `comms`, `diagrams`, `handoff` as ids (word-boundary grep —
  they are common English words in prose that legitimately stays).
- `make test` passes with renamed fixtures.

**F — Rebuild, gates, machine update (foreman).**
`make build`; commit regenerated `targets/` + both marketplace catalogs +
`primitives-core-translation-results.json`. Run `make ci` (= check + validate + names +
build-check + test, Makefile:28). Run `make smoke` once (opt-in loadability check,
Makefile:25-26 — renames are exactly the class of change it exists for). Post-merge:
update the installed plugin so the cache advances past 0.2.1; then handle the out-of-repo
name references (owner decision 5).
Acceptance:
- `make ci` green locally and in CI.
- `make smoke` passes against the rebuilt targets.
- Old-id grep over `targets/` (excluding nothing) returns zero hits.
- `~/.claude/plugins/cache/dotfiles-agents/project-workflow/` gains `0.3.0`.

## Gate & contract hygiene

| Gate | Fires? | Why |
| ---- | ------ | --- |
| CI aggregate (make ci, required) | yes | always; it is the only CI step per .github/workflows/ci.yml line 20 |
| Roster drift guard (make check) | yes | 10 primitives renamed and 1 added in primitives-core/ plus primitives-core.yaml |
| Targets drift guard (make build-check) | yes | primitives-core/, the roster, plugins.yaml, and translate.py all change; regenerate with make build and commit |
| Naming lint (make names) | yes | every renamed or new id is linted for kebab-case, client tokens, vendor-in-id; NOTE: pw- prefix-family conformance is NOT machine-checked, confirm manually against docs/naming.md lines 13-14 |
| Content validation (make validate) | yes | new and moved SKILL.md frontmatter, XML-tag description guard on pw-workflow |
| Loadability smoke (make smoke) | yes, deliberately | opt-in and not in ci per Makefile line 25, but run once: renames are the loading-breakage class it tests |
| yamllint | local-hook lane only | primitives-core.yaml and plugins.yaml are edited, so it applies where configured; CI itself runs only make ci |
| actionlint | no | no .github/workflows/ edits |
| Workbench promotion gate (H1-H5, J1-J4) | no | nothing enters the workbench incubator; pw-workflow is exempt per desk decision 0001 (thin router over proven members, authored for this insertion, same PR) |

Contract notes: `targets/` and both marketplace catalogs are generated — never hand-edit
(`_meta/plans/_config.md:38-39`). The plugin cache's `.in_use` concern from the #40 plan
applies again: do the machine-side update (F) outside live sessions.

## Parallelism + landing order

| Unit | Owner | Depends on | Notes |
| ---- | ----- | ---------- | ----- |
| A rename set | one builder | owner decisions 1-2 | owns primitives-core/ member dirs plus the roster file |
| B pw-workflow | same builder as A | decision 3; A ids fixed | shares primitives-core.yaml with A, so serialize behind A in one lane |
| C README + translate.py | one builder | none | disjoint files: translate.py, primitives-core/plugins/, tests; can run parallel to A and B |
| D plugins.yaml + rule line | foreman | decision 4 | two-line edit; do at reconcile time to avoid a third writer on YAML |
| E docs and reference sweep | one builder | A's final names | parallel drafting is fine since the name map is already fixed; lands after A |
| F rebuild + gates + machine update | foreman | A-E landed | single serial pass: make build, make ci, make smoke, install update |

Land as **one PR** (A-F), per the issue and decision 0001 ("ships in the same PR as other
work to the same plugin, so it gets the same review"). If any other in-flight PR touches
`primitives-core.yaml`, land it first — the rename diff is wide and rebases badly.

## Open questions / owner decisions

1. **Do the four standards skills (`repo-meta-structure`, `repo-compliance-audit`,
   `mise-en-place-scaffold`, `memory-taxonomy`) also take the `pw-` prefix?** They joined
   the plugin after the design was decided (#62), so neither the issue nor the design doc
   rules on them. **Recommend: no** — keep the issue's 10-rename set. They already read as
   their own coherent standards family, they cross-reference each other and the DOCS-xx
   checklist shipped days ago, and renaming them would churn the just-ratified #40 work for
   no discoverability gain. Revisit only if `ls skills/` legibility bites later.
2. **Confirm the 10 new names as tabled** (in particular `pw-plan` for `planning-desk` and
   `pw-agent-md` / `pw-readme`). The design doc records Henry as open to them with no
   changes requested (design doc, Decisions section). **Recommend: as tabled.**
3. **Roster `disposition:` for `pw-workflow`.** The vocabulary is
   qualified / grandfathered-pending-use / demoted / untriaged (`primitives-core.yaml:8-15`);
   a gate-exempt net-new primitive fits none cleanly. **Recommend: `qualified`**, citing
   desk decision 0001 as the qualification authority (the exemption IS the ruling);
   alternative is `grandfathered-pending-use` if you want use-evidence tracked before it
   counts as proven.
4. **Codify the version rule** ("any roster-membership change bumps the plugin minor
   version") — today it lives only in the archived #40 plan (decision 4) and #64's commit
   message. **Recommend: yes, one line in `docs/naming.md`** in this PR; this is the
   rule's second application and the naming manifest is where id/version conventions
   already live.
5. **Out-of-repo references to old skill names.** The global dotfiles instructions invoke
   "the `/handoff` skill" (session-continuity instruction), and installed caches keep old
   names until updated; nothing in this repo can fix those. **Recommend:** after merge +
   plugin update, do a separate dotfiles-repo sweep for `handoff` / `comms` / `diagrams` /
   `planning-desk` invocations; track as a follow-up checklist item on #27, not in this PR.
6. **Plugin README vs `docs/plugins/project-workflow.md` user guide.** Two overlapping
   surfaces now exist where the design assumed one. **Recommend: keep both with a split** —
   README = short bundle front door (families, routing table, install pointer, travels with
   the plugin); user guide = deep per-skill documentation in repo docs; each links the
   other, routing table lives in README + `pw-workflow` and the guide points at it.

## Could not verify

- The exact rendering of `plugins.yaml`'s description in third-party marketplace UIs (out
  of scope; plugin.json carries it verbatim).
- Whether `check_roster.py`'s disk walk tolerates the new `primitives-core/plugins/`
  subtree — flagged as a builder check inside deliverable C rather than asserted here.
