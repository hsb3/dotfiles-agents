---
title: "dotfiles-agents — project roadmap brief"
status: active
created: 2026-07-05
---

# Project roadmap brief — dotfiles-agents

_Status: active — 2026-07-05. A point-in-time readout. Live truth is the **Agent Extenders** board
(`hsb3` project #9) and [`docs/CHARTER.md`](../../../docs/CHARTER.md); where this brief and the board
disagree, the board wins._

## 1. Where the project stands

The **build is done; the proving has started.** dotfiles-agents is the git-tracked source of truth
for *proven* agent extenders (four primitive types — agent, skill, mcp, hook), rendered from one
canonical source copy into per-target bundles for Claude Code and opencode (and, third, Claude
managed agents), with a CI drift guard that keeps the generated `targets/` honest.

All six construction phases have closed:

| Phase | What it delivered | State |
|---|---|---|
| 0 — Governance scaffold | decision record + plan | done |
| 1 — Fresh repo + scaffold | primitives-core, roster, translation control files, targets | done |
| 2 — Migrate into primitives-core | the primitives moved to single-source | done |
| 3 — Translation service | `translate.py` + drift guards render targets | done |
| 4 — Workbench | the promotion gate (unproven -> proven) | done |
| 5 — Bootstrap | clean-machine clone + install + verify | done |

The plumbing works. What remains is **proving the system on real repos and rolling it out** — which
is exactly what the three open gates below track. One capability (clone-at-build externals) is the
only unbuilt piece of the translation service itself.

## 2. The roadmap is three promise-gates

The forward plan is not a phase list anymore; it is three gates, each a promise that is safe to make
only once its issues close. This is the spine of the roadmap.

### GATE — P1 · Lifecycle live
*The curation loop runs for real: roster bootstrap-triage, first real promotion + retirement
records, and the symlink/commands migration that unblocks retiring hsb3-custom-plugins.*

- **#32** (P1, High, Up Next) — repoint core-tier skill symlinks + migrate the 16 commands before
  retiring hsb3-custom-plugins. **This is the ready, next-to-build item.**
- **#48** (P2) — inventory + curate the frontend extenders to a core set.
- **#49** (P2) — seed the use-case-driven extender backlog.

### GATE 2 — P2 · Pilot proven
*project-workflow proven on a real repo (hsb3/fleet-dashboard): audit -> manifest -> scaffold ->
re-audit green, plus the standards/tooling fixes the pilot surfaces, plus the brownfield desk apply.*

> **Pilot target updated 2026-07-05:** re-pointed from mhi-raptorxai/raptorgpt-agents to
> hsb3/fleet-dashboard (a personal repo - cleaner canonical proof). The raptorgpt run (merged
> rgpt#541, defects fixed) is kept as a completed prior pilot; its vault sign-off no longer gates
> Gate 2.

- **#33** (P0, High, Up Next) — **the active top priority.** Run the standard end-to-end on
  hsb3/fleet-dashboard: baseline audit, mise-en-place, scaffold apply, re-audit, findings routing.
  Baseline TBD until the audit runs; raptorgpt is the routing precedent.
- **#39** (P2) — roster provenance/notes field + machine cross-ref to promotion records.
- **#68 / #69 / #70** (P2, type:fix) — the three planning-desk self-consistency fixes the pilot
  surfaced. Re-verified against current 0.2.4 source this session: **#68 is a live toolkit bug;
  #69 and #70 were re-scoped to their true (narrower) residual** — see §5.

### GATE 3 — P3 · Rollout and retire
*Enact the standard across the priority repos, retire hsb3-custom-plugins, and finish the last
translation capability.*

- **#36** (P2, XL) — clone-at-build externals: the last unbuilt translation capability. Blocked on
  owner decisions (network-at-build in CI, drop policy, pin format).
- **#37** (P2) — convert ra-platform `.claude/commands` to a formal skill (first skills-over-commands
  migration). planning-desk already subsumes the commands; this is adoption + retirement.
- **#27** (P3) — project-workflow v2: pw- naming, ops/output cohesion skill, plugin README. Deferred
  cohesion/rename polish.

### GATE 4 — P4 · Cross-tool parity  *(new, 2026-07-05)*
*Agnostic base format + cross-vendor tool/config mapping — move off Claude-Code-as-baseline so
opencode (and managed-agent) parity is real.*

- **#59** (P1, High, XL) — the strategic lever. High impact, XL, gated on its own open decisions
  (network/pin/drop policy shared shape with #36). Plan-and-decompose next, run in parallel.

## 3. The critical path

```
NOW ----------------------------------------------------> LATER
#33 Gate-2 pilot sign-off  (P0, active)
     |
     +--> GATE 2 closes (Pilot proven)  --- #39, #68/#69/#70 clear the pilot's tail
              |
              +--> #32 lifecycle/consolidation (P1, ready)  --> GATE P1 (Lifecycle live)
                        |
                        +--> #36 / #37 / #27  --> GATE 3 (Rollout and retire)

parallel strategic bet:
#59 agnostic base format + cross-vendor mapping (P1, XL)  --> unlocks true opencode parity
```

- **#33 is the one thing in flight.** Everything downstream keys off Gate 2 closing.
- **#32** is the only other item that is ready to build (has a plan, no open blocker).
- **#59 is the biggest strategic lever and runs in parallel** — it moves the project off
  "Claude-Code-as-baseline" to a genuine agnostic base format, which is what makes cross-tool
  (opencode) parity real. It is High impact but XL and gated on open owner decisions, so it is a
  *plan-and-decompose-next*, not a *start-tomorrow*.

## 4. Priority snapshot (as of 2026-07-05)

Twelve open issues, all conformant, labeled, and on the board. Distribution after this session's
triage: **P0 x1, P1 x2, P2 x8, P3 x1.** Every item has a Workstream and a Priority.

| Pri | Issue | Eff | Workstream | Gate | One-line |
|---|---|---|---|---|---|
| P0 | #33 | M | project-workflow | Pilot proven | Gate-2 pilot close-out (active) |
| P1 | #32 | M | lifecycle | Lifecycle live | symlink + commands migration (ready) |
| P1 | #59 | XL | extenders-core | Cross-tool parity | agnostic base format / cross-vendor mapping |
| P2 | #36 | XL | extenders-core | Rollout | clone-at-build externals |
| P2 | #37 | M | project-workflow | Rollout | ra-platform commands -> skill |
| P2 | #39 | M | extenders-core | Pilot proven | roster provenance field |
| P2 | #48 | M | extenders-core | Lifecycle live | inventory + curate frontend extenders |
| P2 | #49 | S | extenders-core | Lifecycle live | seed use-case extender backlog |
| P2 | #68 | S | project-workflow | Pilot proven | planning-desk toolkit blind to body-only folders |
| P2 | #69 | M | project-workflow | Pilot proven | planning-desk template format (.md vs .yml) |
| P2 | #70 | M | project-workflow | Pilot proven | planning-desk plan.md frontmatter |
| P3 | #27 | L | project-workflow | Rollout | project-workflow v2 cohesion/rename |

## 5. Decisions — resolved 2026-07-05

1. **Milestones assigned.** #48/#49 -> P1 Lifecycle live (curation loop); #59 -> the new P4 gate.
   Every open issue now carries a milestone.
2. **#59 gets its own gate.** Created **P4 — Cross-tool parity** (GATE 4); #59 moved there. Future
   opencode-parity work hangs off this gate.
3. **#69 template format: `.yml`.** planning-desk will ship the `.yml` issue-forms set to match the
   standard; `conformance.py` stays unchanged. Decision recorded on #69.

**Still open (issue-internal, not roadmap-level):**

- **#36 clone-at-build externals** carries its own open decisions 1-7 (network-at-build in CI, drop
  policy, pin format) before it can start. #59 shares that decision shape.

## 6. Notes / risks

- **The pilot tail is self-referential.** #68/#69/#70 are the planning-desk plugin failing its own
  sibling standards when dogfooded. Cheap to fix, but they are the signal that "proven on a real
  repo" is not yet true — Gate 2 is not just #33.
- **Nothing is blocked by a hard edge** (0 blocked-by edges open); the constraints are owner
  decisions, not code dependencies. Decisions in §5 are the actual bottleneck.
- **Truth discipline:** counts above are a snapshot; the board is the system of record. Re-run the
  triage pass (project-workflow board-triage) rather than trusting this table after new issues land.
