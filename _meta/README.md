# _meta — the local working desk

Tracked-by-default working desk (ADR-0006). Taxonomy:

- `HANDOFF.md` — the cold-start bridge (current build state, deliverable map). Tracked, secret-free.
- `operations/` — live URLs, credentials, runbooks with secrets. **Never tracked** (only
  `.gitkeep` is); its content is gitignored.

The `_meta/plans/` planning desk does **not** live here for this repo — planning migrated to
the executive desk before the rebuild.
