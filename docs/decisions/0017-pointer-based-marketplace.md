---
title: "Pointer-based marketplace — symlink plugin assemblies, no tracked dist"
type: decision
status: Accepted
created: 2026-08-03
summary: one repo serves both runtimes with zero tracked generated artifacts — plugins/<id>/ become thin symlink assemblies over primitives-core/ with the marketplace manifest at the repo root, Claude Code installs natively by dereferencing, opencode generates its laydown at install time, and READMEs travel with their skill.
---

# 0017 · Pointer-based marketplace — symlink plugin assemblies, no tracked dist

_Replaces the generate-and-track distribution model with pointers: the source tree IS the
installable surface for Claude Code, and the only real transformation (opencode) runs at
install time instead of being committed._

- **Provenance:** owner ruling 2026-08-03 (backlog decision-2), after a DAG review of the
  distribution machinery, verification against current plugin docs, and a live
  proof-of-concept install. Formalized here per backlog task-1 (milestone m-0). The
  README-placement ruling in §Decision 4 was added by the owner 2026-08-03 when work started.
- **Raised by:** backlog decision-2; executed by tasks 2–4 (with 7 and 9 downstream).

## Context

The distribution machinery had grown far heavier than what it distributes: ~733 lines of
generators (`gen_marketplace.py`, `gen_standalone.py`, `gen_opencode.py`) producing 530
tracked files under `dist/`, each lane wrapped in a drift guard, plus a filtered-assembly
publish workflow — all to ship 38 primitives whose bodies already live once in
`primitives-core/`. Every change pays the build/check/regen tax; every reviewer reads
generated diffs; the eval loop has two trees that claim to be the product.

A verification pass against the current plugin docs plus a live PoC established the facts
that make the machinery unnecessary for Claude Code:

- A marketplace's `source` field accepts **relative paths** into the marketplace repo.
- **Symlinks inside a plugin dir are dereferenced at install** — confirmed live for
  `skills/`, `agents/`, and `hooks/` dirs pointing anywhere within the marketplace repo.
- Symlinks pointing **outside** the marketplace repo are **silently skipped** (a failure
  mode to lint for, not a blocker).
- An installed plugin cannot reference paths outside its own root — dereferencing at
  install is what makes the assembly self-contained.

The opencode lane is different in kind: its translation (stricter name regex, agent
frontmatter remap, config fragment) is genuinely irreducible. But irreducible
transformation does not require tracked output.

## Decision

One repo serves both runtimes; nothing generated is tracked.

1. **`plugins/<id>/` become thin symlink assemblies.** Each plugin dir holds a
   hand-authored `.claude-plugin/plugin.json` (plus `hooks.json` where the plugin ships
   hooks); its `skills/`, `agents/`, and `hooks/` entries are symlinks into
   `primitives-core/`. Multi-homing a primitive into another plugin = one more symlink.
   The `bundles/` source dir dissolves — a bundle's README is hand-authored directly at
   `plugins/<id>/README.md` (it describes the composition, which lives there).
2. **`.claude-plugin/marketplace.json` moves to the repo root**, hand-maintained, listing
   every plugin by relative `source` path. Claude Code installs natively from the repo —
   no build step.
3. **The opencode lane generates at install time.** `gen_opencode.py` + `translation.yaml`
   stay as the one irreducible translation step, but run by the installer/consumer;
   `dist/opencode/` is no longer tracked.
4. **READMEs travel with their skill** (owner ruling, 2026-08-03). The
   `primitives-core/standalone-readmes/` side-tree dissolves: a standalone skill's README
   lives at `primitives-core/skills/<id>/README.md`, next to the `SKILL.md` it documents.
   The standalone plugin's root README is one more symlink to it — same mechanism as
   everything else.
5. **A symlink lint replaces the drift-guard class.** Every symlink under `plugins/` must
   resolve inside the repo (the silent-skip failure mode above), checked in `make ci`.
   The roster (`primitives-core.yaml`) slims to a provenance manifest
   (origin/upstream/targets/disposition) — ADR 0015 enforcement continues against it.
6. **Two repos only if a tripwire fires.** Split the repo when: shared-body primitives
   become the minority, an external consumer needs an independent release cadence, or the
   translation layer outgrows declarative config. Until then, one repo.

### Relation to prior ADRs

- **Supersedes ADR 0008's dist-lane design** (its Decisions 1–3: `dist/<target>/` tracked
  lanes, the filtered lift-and-assemble publish payload, the roster-enum residency in
  `check_roster.py`). 0008's Decision 4 — `flow.yaml` + `check_flow.py` as the standing
  structural guard — **remains in force**; task-7 revisits its scope after the
  restructure. 0008 is marked `Superseded-by-0017` with a callout naming the surviving
  part.
- **Amends ADR 0016, does not supersede it:** the 15-plugin lineup stands unchanged; only
  its implementation surface moves (its Affects list — `plugins.yaml`,
  `skill-catalog.yaml`, `bundles/`, the generators — is retired by task-3).
- **ADR 0007's governance (dev integrates, main publishes) is untouched here.** What
  publishing *means* under a pointer-based repo is an open decision — see below.

### Linked open decisions

- **Publish model (task-5):** with no dist to assemble, `main` could become a plain merge
  gate of `dev`, or consumers could install straight from `dev`. Undecided; the current
  publish machinery stays as-is until task-5 rules.
- **`evals/` + `harness/` extraction (task-6):** whether the workbench leaves the repo
  changes what a consumer clone weighs, which feeds task-5.

## Sequencing

Execution order (backlog, milestone m-0): task-2 (build `plugins/` symlink assemblies +
root marketplace.json + symlink lint, dist output byte-identical) → task-3 (retire
`dist/`, generators, drift guards, `plugins.yaml`, `skill-catalog.yaml`; slim the roster)
→ task-4 (opencode install-time generation). The dist/generator/publish machinery stays
fully operational until each retirement lands green.

## Consequences

- `make ci` loses `build`/`build-check` and gains the symlink lint; PRs stop carrying
  generated diffs; the regen-tax on every primitive edit disappears.
- The eval loop benchmarks one unambiguous source tree.
- Hand-authored per-plugin metadata (`plugin.json`, root `marketplace.json`) replaces
  generated metadata — small, reviewable files; the lint keeps the assembly honest.
- Symlinks become load-bearing in the tracked tree: contributors on filesystems or
  tooling that mangle symlinks (e.g. Windows without developer mode) will need care;
  acceptable for this repo's audience, revisit only if a tripwire-adjacent consumer
  appears.
- `standalone-readmes/` and `bundles/` disappear as top-level concepts; `flow.yaml` nodes
  flip accordingly (task-2/3), and flow enforcement itself may shrink after (task-7).
- If the symlink-dereference install behavior ever regresses upstream, the marketplace
  breaks loudly at install — the PoC is the reference; re-verify before task-2 merges.

## Affects

`plugins/` (new home, symlink assemblies) · root `.claude-plugin/marketplace.json` ·
`primitives-core/` (READMEs move into skill dirs; `standalone-readmes/` dissolves) ·
`bundles/` (dissolves into `plugins/<id>/README.md`) · `dist/` + `gen_marketplace.py` +
`gen_standalone.py` + `plugins.yaml` + `skill-catalog.yaml` + their guards (retired,
task-3) · `gen_opencode.py` + `translation.yaml` (kept, run at install time, task-4) ·
`primitives-core.yaml` (slims to provenance manifest) · `Makefile` + `tests/` ·
`flow.yaml` / `docs/FLOW.md` · `.github/workflows/publish.yml` (pending task-5) ·
ADR 0008 (status) · ADR 0016 (implementation surface).
