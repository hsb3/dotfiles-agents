# Extender-DB — Open Items

_The project's issue tracker: open items, catalog findings awaiting triage, and the resolved
log. One line per item; promote to a GitHub issue only if it outgrows this file._
Status: active · 2026-07-20

Conventions: `EDB-N` ids, newest first within each section. An item moves to **Resolved**
with a one-line outcome (and stays there — the log is the promotion-gate evidence for
"findings → actions").

## Open — tool

| Id | Item | Notes |
|---|---|---|
| EDB-8 | Standalone distribution rows carry no version | `skill-catalog.yaml` wrappers get a generated version at assembly; decide whether to read it from `gen_standalone.py` output or leave blank. |
| EDB-7 | No snapshot/time-series story | Rows are mutate-in-place; trend analysis needs a `snapshots` collection keyed by git ref (see README expansion path). Decide at W4 whether it earns its cost. |
| EDB-6 | Frontmatter parser is flat-only | `parse_frontmatter` handles single-line `key: value` only. All 27 current extenders are flat; a future nested/multi-line frontmatter would be silently truncated to its flat keys. Guard or extend before W2 if hook configs need it. |
| EDB-5 | Judged assessments not yet run | W1 in [PLAN.md](PLAN.md). Archetype + section-taxonomy frameworks are seeded but have zero assessment rows. |

## Open — catalog findings (from the data, awaiting triage)

| Id | Item | Notes |
|---|---|---|
| EDB-4 | Custom frontmatter keys with no spec | skill `metadata` (2), skill `version` (2), agent `memory` (1). Decide each: adopt into an internal spec framework (requirement != custom), or remove from the bodies. |
| EDB-3 | Two skills exceed the ≤500-line SKILL.md guideline | `diagrams` 653 lines, `obsidian-cli` 753 lines (framework `anthropic-agent-skills` / `concise-body`). Candidate fix: push depth into `references/`. |

## Resolved

| Id | Item | Outcome |
|---|---|---|
| EDB-2 | PocketBase default 5000-char cap broke ingest of large bodies | Explicit `max` on `extenders.body` and `files.content` (2 MB); documented in schema.py. |
| EDB-1 | Collection PATCH without field ids drops-and-recreates columns (data loss) | schema.py merges by field name and preserves ids on update; noted as invariant in CHARTER.md. |
