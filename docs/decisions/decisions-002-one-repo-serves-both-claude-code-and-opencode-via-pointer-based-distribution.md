---
id: decision-002
title: One repo serves both Claude Code and opencode via pointer-based distribution
date: '2026-08-04 00:44'
status: accepted
---
## Context

Owner ruling, 2026-08-03, after a DAG review found the distribution machinery
overcomplicated: 733 lines of generators producing 529 tracked `dist/` files, plus drift
guards and a filtered-assembly publish lane. Verified against current plugin docs and a live
proof-of-concept: marketplace `source` accepts relative paths; symlinks inside a plugin dir
pointing anywhere within the marketplace repo are dereferenced at install (skills, agents,
and hooks dirs all confirmed); out-of-marketplace symlinks are silently skipped; installed
plugins cannot reference paths outside their root.

## Decision

One repo serves both runtimes. Claude Code plugins become thin symlink assemblies
(`plugins/<id>/` linking into `primitives-core/`) with `.claude-plugin/marketplace.json` at
the repo root — no build step, multi-homing = one more symlink. The opencode lane keeps its
genuinely irreducible translation step (`gen_opencode.py` + `translation.yaml`) but runs it
at install time; no generated artifacts are tracked anywhere. Split into two repos only if a
tripwire fires: shared-body primitives become the minority, an external consumer needs an
independent release cadence, or the translation layer outgrows declarative config.

## Consequences

- Formalized by the ADR in task-1; executed by tasks 2-4; publish model (task-5) and
  evals/harness extraction (task-6) are the linked open decisions.
- dist/, gen_marketplace.py, gen_standalone.py, plugins.yaml, skill-catalog.yaml, and their
  drift guards are deleted (task-3). A symlink lint replaces the drift-guard class.
- The eval loop keeps one unambiguous source tree to benchmark against.
