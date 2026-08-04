# AGENTS.md

This repo's agent-facing conventions live in [CLAUDE.md](CLAUDE.md). Read it first.

Quick reference:
- Task interface: `make ci` (`make help` for targets).
- Edit primitives under `primitives-core/` only; `plugins/<id>/` are hand-authored symlink
  assemblies over it (ADR 0017) listed in the root `.claude-plugin/marketplace.json` —
  nothing generated is tracked.
- Branch off `dev`, PR into `dev`; `main` is publish-only.
- Contributor SOP + the full `make ci` invariant list: [.github/CONTRIBUTING.md](.github/CONTRIBUTING.md).
