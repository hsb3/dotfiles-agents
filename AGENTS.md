# AGENTS.md

This repo's agent-facing conventions live in [CLAUDE.md](CLAUDE.md). Read it first.

Quick reference:
- Task interface: `make ci` (`make help` for targets).
- Edit primitives under `primitives-core/` only; `plugins/` and `.claude-plugin/marketplace.json`
  are generated — run `make build`, never hand-edit them.
- Branch off `dev`, PR into `dev`; `main` is publish-only.
