---
title: "Vendor dist lanes, filtered append-only publish, and the flow manifest"
id: decision-027
type: decision
status: superseded-by-decision-030
created: 2026-07-22
summary: distribution grows a second vendor (opencode) — generated dist trees move under dist/<target>/, main becomes a filtered parented assembly of the dist lanes instead of a whole-tree force push, and flow.yaml + check_flow.py become the standing structural guard.
---

# Decision 027 · Vendor dist lanes, filtered append-only publish, and the flow manifest

> **Superseded by [decision-030](decisions-030-pointer-based-marketplace-symlink-plugin-assemblies-no-tracked-dist.md) (2026-08-03):** the dist-lane
> design (Decisions 1–3 — tracked `dist/<target>/` trees, the filtered lift-and-assemble
> publish payload, the roster-enum residency) is replaced by pointer-based distribution.
> Decision 4 (`flow.yaml` + `check_flow.py` as the standing structural guard) **remains in
> force** (task-7 revisits its scope). The publish *governance* (dev integrates, main
> publishes) was never this ADR's to change and stays with ADR 0007; the publish payload
> under the new architecture is open as backlog task-5.

_Owner-ruled 2026-07-22 ("proceed as proposed"). Old-desk ADR 0014 carries a matching
amendment (same date): its §3 already specified `main` as "rebuilt clean — marketplace file
+ plugin folders"; the whole-tree force push was the interim implementation's deviation, so
this ADR **restores** 0014 §3's intent and extends it with parentage and vendor lanes._

## Context

The repo is about to serve a second vendor: the same primitives shaped for **opencode**,
which was always the intent (`targets:` field, the dropped Phase-3 translation surface at
`4e8a05b`, restorable precedent on `dev-legacy`, both now in `hsb3/dotfiles-agents-archive`). Three structural facts force a decision:

1. **The Claude Code dist squats at the repo root** (`plugins/`, `.claude-plugin/`,
   `PLUGINS.md`) because consumers resolve the default branch's root
   `.claude-plugin/marketplace.json` (ADR 0007). Fine for one vendor; with two, generated
   lanes need a common, named home.
2. **Publish is a whole-tree force push** (`publish.yml`): `main` today is a byte-identical
   snapshot of `dev` — ~24 MB of which only ~3.3 MB is consumer surface; `evals/` alone is
   16 MB and grows with every weekly campaign. Every installer clones the workbench.
3. **opencode has no marketplace.** Its distribution shape is a laydown tree plus one
   mergeable config fragment plus an installer (per the `opencode-expertise` references and
   the live harness adapter). Skills translate near-verbatim (stricter name regex); agents
   need a mechanical frontmatter remap; MCP is a JSON reshape; **hooks require real rework**
   (TS-on-Bun plugin wrappers) and are excluded until that codegen exists.

## Decision

1. **Vendor dist lanes under `dist/`.** Generated, committed, drift-guarded trees per
   target: `dist/claude-code/` (the current root artifacts, relocated) and `dist/opencode/`
   (laydown: skills verbatim + name-regex guard, agents remapped per the mapping table, one
   `opencode-fragment.jsonc`, an `install.sh`, and an **exclusions manifest** — subset,
   never silently break; hooks stay Claude-Code-only until TS wrapper codegen is built).
2. **`main` becomes a filtered, parented assembly.** The publish workflow assembles the
   publish tree — `dist/claude-code/` contents lifted to the root (preserving the ADR 0007
   consumer contract) plus `dist/opencode/` published as `opencode/` — and commits it **with
   the previous `main` as parent**. No more force push: `main` is append-only, its history
   a release ledger (one commit per publish recording the source `dev` SHA and bumped
   versions), and the workbench (`harness/`, `evals/`, `_meta/`, `.claude/`, `.agents/`)
   never publishes. One published branch serves both vendors: Claude Code installs via the
   marketplace root; opencode consumers run the laydown installer from a clone.
3. **The roster's `targets:` field gets a real enum** (`{claude-code, opencode}`, enforced
   by `check_roster.py`) and a revived **capability matrix** (`translation.yaml`: per
   primitive type × target: native / transform / render / unsupported), reusing the dropped
   `translate.py` design.
4. **`flow.yaml` + `scripts/check_flow.py` (make `flow`, in `make ci`) are the standing
   structural guard**: every top-level path homed exactly once, planned paths must not
   exist until flipped, generated nodes must name generator + guard, automated edges must
   be acyclic (only manual owner edges close loops), and the `docs/FLOW.md` DAG is
   generated from the manifest under drift guard.

## Sequencing (deliverables and gates, no timelines)

- **W1 — flow guard (this ADR's PR):** `flow.yaml`, `check_flow.py`, `docs/FLOW.md`,
  wired into `make ci`. Gate: `make ci` green with the new check.
- **W2 — filtered parented publish:** rewrite `publish.yml` to assemble from the CURRENT
  root layout; verify a publish produces an append-only `main` whose root shape consumers
  already expect. Gate: `claude plugin marketplace add` against the new `main` resolves;
  `main` history gains exactly one parented commit per publish.
- **W3 — dist relocation:** move root artifacts to `dist/claude-code/`; update generators,
  drift guards, publish lift map, and flip the flow.yaml nodes. Gate: `make ci` + a
  publish round-trip.
- **W4 — opencode lane MVP:** `translation.yaml`, `gen_opencode.py` (skills + agents +
  fragment + installer + exclusions), `targets` enum enforcement. Gate: laydown verified
  against a live opencode (the harness adapter's mechanics are the reference), exclusions
  explicit, `make ci` green.
- **W5 — externals clone-at-build** joins the dist lanes (existing scope: #36/#122).

## Consequences

- Consumer clones shrink to the consumer surface; the eval corpus grows without taxing
  installers. `main` history becomes meaningful. The workbench stays private to `dev`.
- Two generated lanes mean two drift guards and a bigger `make build`; the flow guard keeps
  the growing structure honest (a new top-level path with no declared home fails CI).
- Hooks do not reach opencode users until wrapper codegen exists — recorded per lane in the
  exclusions manifest rather than silently absent.
- **ADR 0007's mirror rule:** 0007 mirrors old-desk ADR 0014, which "remains the authority
  of record" for branch governance. This ADR changes the publish **payload and parentage**,
  not the dev-integrates/main-publishes governance — but 0014 must be updated desk-side
  before W2 lands (owner action), per 0007's own precedence rule.

## Affects

`publish.yml` · `gen_marketplace.py` / new `gen_opencode.py` · `check_roster.py` (targets
enum) · root layout (W3) · `flow.yaml` / `docs/FLOW.md` (node flips per wave) ·
`.agents/skills/publish-to-main` (runbook rewrite at W2) · `README.md` layout table ·
old-desk ADR 0014 (update-first rule).
