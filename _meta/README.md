# _meta — the local working desk

Tracked-by-default working desk (ADR-0006). Taxonomy:

- `HANDOFF.md` — the cold-start bridge (current build state, deliverable map). Tracked, secret-free.
- `mise-en-place.yml` — per-repo variance manifest (default branch, required paths, GitHub knobs).
- `plans/` — the planning desk: scoped plans and staged issue bodies (frontmatter-audited).
- `briefings/` — dated readouts whose audience is this repo. Portfolio/executive briefings
  live on the executive desk (`dotfiles-agents-desk`).
- `research/` — live investigations and design references still in play.
- `reference/` — secret-free durable runbooks / how-to reference for this desk (per-repo
  variance, mise-en-place.yml).
- `_archive/` — frozen provenance: pre-reset snapshots and closed-wave build handoffs.
- `operations/` — live URLs, credentials, runbooks with secrets. **Never tracked** (only
  `.gitkeep` is); its content is gitignored.
