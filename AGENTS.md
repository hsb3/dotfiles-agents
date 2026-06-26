# AGENTS.md — dotfiles-agents

Cross-tool instructions for any coding agent working in this repo. See `docs/CHARTER.md` for the model and `CLAUDE.md` for the Claude-specific digest.

This repo is the source of truth for agent **extenders** (skills, agents, mcp, hooks).

## Rules
- Edit primitives only in `primitives-core/`. Never hand-edit anything under `targets/` — it is generated.
- One canonical source copy per primitive; the translation service renders per-target copies.
- Commands are not used. Hook handlers use standard-library only.
- Generated bundles + the results lock are drift-guarded in CI; regenerate, don't patch.
