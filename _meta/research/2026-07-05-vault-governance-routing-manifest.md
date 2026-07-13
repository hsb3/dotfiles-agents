---
title: "Vault governance routing manifest (DEVTOOLS -> canonical homes)"
status: draft — awaiting owner review before any migration
created: 2026-07-05
---

# Vault → canonical-home routing manifest

_Source: `hsb-2026/…/02_Projects/02_DEVTOOLS/`. 72 md files routed (8 `1_Journal/` excluded — brainstorm stays).
Homes per [`docs/governance-map.md`](../../docs/governance-map.md). **No files moved yet — this is the plan for review.**_

## Headline

| Action | Count | Meaning |
|---|---|---|
| **DROP-DUPLICATE** | 11 | fully mirrored in CANON / dotfiles ADRs 0001-0003 / cowork decisions-log — vault copy redundant, safe to lose |
| **ARCHIVE** | 34 | shipped/historical (11 eng-specs + 11 test-plans + 6 briefings + 6 superseded PM/design) — keep for provenance |
| **MIGRATE** | 26 | the real payload — unique content that exists nowhere else |
| **STAYS** | 1 | T-16 inbox/daily routing manifest (vault housekeeping, not governance) |
| `1_Journal/` | 8 | brainstorm — stays in vault |

## The migration payload (26 MIGRATE — what's lost if the vault folder vanished)

**The whole `1_Product_Design/` tree (19 files) is the single biggest unique loss** — the cowork
desk has NO product-design docs, so this entire brief → one-pager → product-spec → feature-spec
decomposition exists only here. Decisions are in CANON; the *design narrative* is not.
→ **home: cowork strategy desk** (agent-extenders brief, 12 feature-specs, 3 one-pagers, 3 product-specs).

Standalone uniques:
| File | Home |
|---|---|
| `decisions/frontend-stack-vite-react-shadcn.md` (proposed, unshipped) | dotfiles `docs/decisions/` ADR (or keep proposed) |
| `decisions/rules-and-memory-translation-policy.md` (absent from CANON) | dotfiles `docs/decisions/` ADR |
| `decisions/use-case-driven-backlog.md` (backlog philosophy) | cowork `_structure/decisions/` ADR |
| `decisions/strategy-desk-boundary.md` (Q-16 rule, partial CANON 9) | cowork `_structure/decisions/` ADR |
| `frontend-stack-shortlist.md` + `2026-07-01-inbox-daily-sweep.md` (research) | cowork `analyses/` |
| `1_Project_Management/OPEN_QUESTIONS.md` (live residue ⚠) | cowork `_meta/` — IF still open |

## ARCHIVE (34, safe — code is the realization)

- **11 engineering-specs** — all shipped 2026-07-02 (`dotfiles-agents/_meta/plans/devtools-eng-spec-build.md`); realized in `primitives-core/` + workbench.
- **11 test-plans** — verify-layer for those specs (158-test suite green).
- **6 briefings** (2026-07-02 decision-queue / signoff decks+audio) — comms output.
- **6 PM/design provenance** — CURRENT_STATE, doc-build-plan, TASKS, skills-migration-inventory, 2 technical-designs.

## DROP-DUPLICATE (11, fully mirrored)

`hooks-as-script-plus-config` (=ADR 0002) · `skills-over-commands` (=ADR 0001) ·
`third-party-extenders-clone-from-source` (=ADR 0003) · `single-canonical-copy…` (=CANON 2+7) ·
`workbench-repo-for-incubation` (=CANON 4+10) · `retire-hsb3-custom-plugins` (=CANON 1+15) ·
`distribution-capability-matrix` + `distribution-targets…` (=CANON 5+6) · `requalification-on-next-use`
(=promotion-gate) · `DECISIONS.md` (=cowork decisions-log) · `primitives-core-architecture` (=technical plan).

## Owner decisions before migrating (the 5 flags)

1. **`OPEN_QUESTIONS.md` — live or closed?** If any Q is unresolved (Q-04 ratification, brownfield
   approval, TC sign-offs), it's decision-payload → migrate to cowork; if closed → archive.
2. **The 6 briefings — where?** Rubric home `cowork/_meta/briefings/` does not exist yet; the
   repo-meta-structure standard says comms land in `dotfiles-agents/_meta/plans/inbox/`. Pick one.
3. **2 technical-designs** (`primitives-core-architecture`, `translation-service-architecture`)
   marked DROP-DUPLICATE vs the cowork technical plan — not diffed line-by-line. If they carry
   extra design detail, downgrade to MIGRATE/merge.
4. **`memory-standard.md`** — shipped as the memory-taxonomy skill; ARCHIVE vs migrate-as-provenance
   to cowork is a judgment call.
5. **`2026-07-02-t16-routing-manifest.md`** — routes OTHER vault folders, not DEVTOOLS; STAYS as
   vault ops, or archive once executed.

## Note on the "drop-duplicate" safety

Only 3 ratified decisions are individual dotfiles ADRs (0001/0002/0003); the other CANON decisions
live consolidated in cowork `_structure/CANON.md`. So DROP-DUPLICATE relies on **CANON remaining the
record** — confirm CANON is authoritative before deleting vault decision copies.

---

# v2 — reconciled final dispositions (2026-07-05, after 3-agent discovery + cowork pass)

## Corrections to v1
- **Decisions (13): MOVE, don't drop.** CANON (last 2026-06-30) never absorbed 6 post-06-30 rulings -> move all to Strategy Desk `_structure/decisions/` + a **CANON catch-up decision record**; leave vault tombstones. 3 (skills-over-commands, hooks, externals) are already dotfiles ADRs 0001-3 -> tombstone-only. 2 repo-scoped (rules-and-memory-translation-policy; frontend-stack, proposed) -> dotfiles `docs/decisions/`. **2 are cited by wikilink in the workbench promotion record (distribution-capability-matrix, rules-and-memory) -> tombstones + pointer fix, or the gate's first precedent dangles.**
- **Feature-specs (12): 10 archive, 2 MIGRATE-DURABLE** (unbuilt/forward design): `hook-composition-standard` (deferred, shipped code cites it as pending) + `distribution-bundle-generation` (raw-primitive path + Q-10) -> Strategy Desk `_structure/`.
- **Technical-designs (3): all FILE-DELTA-FIRST, not archive-as-is:**
  - `memory-standard` -> capture rationale delta (loading-tier mechanics, alternatives, risks, authorship-asymmetry) to a dotfiles `docs/` home; **re-point 2 shipped citations** (`memory-taxonomy/SKILL.md:24`, `references/taxonomy.md:7`), then archive.
  - `translation-service-architecture` -> capture the **Cowork hook-less subset design** (4th harness thru 3 outputs; exclusion-manifest recommendation; `requires:`-driven subsetting) + **Q-05 trigger policy** (both fully uncommitted) to a dotfiles `docs/` home; fold 3 clone-at-build edge cases into #36, then archive.
  - `primitives-core-architecture` -> capture the **Q-11 functionform-asmbl ecosystem edge** to CANON, then archive.

## Route-before-freeze payload (must land before registries freeze)
- **NEW issue:** T-23(b) + Q-14 -> "use-case entry + shared milestone-set standard" (zero home today).
- **Desk STATUS (cowork):** Q-07 (UI gate), Q-11 (repo/marketplace edges), Q-12 (provider-agnostic runtime, park), Q-06 (3 sandbox items), wb#6/wb#7 attestations, project-9 board-views (owner manual).
- **Already covered / drop:** T-19->#37, T-23(a)->#49, T-27 residue->#36; T-18/T-20/T-27-main/Q-05/Q-10 closed; HANDOFF §5.2/3/4/6 moot.

## Execution waves
1. **Desk capture (no vault touch):** decisions->Strategy `_structure/decisions/` + CANON catch-up; durable design (7 + 2 feature + 2 research)->Strategy; tech-design deltas + repo ADRs->dotfiles `docs/`; route issue + desk-STATUS entries; #36 edge-case comment.
2. **Vault freeze (last):** move eng-specs(11)+test-plans(11)+briefings(6)+registries(4)->vault `05_Archive/`; tombstones for moved decisions; rewrite vault CLAUDE.md/HANDOFF -> journal+archive only.
