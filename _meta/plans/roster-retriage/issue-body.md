Roster hygiene from the 2026-07-05 owner review. Two disposition corrections; **record intent — no roster edits until this issue is worked.**

## Deliverable A — demote queue (move to dotfiles-agents-workbench incubator)

Authored skills that are not yet proven and should leave the distributed `core`/`toggle` shelves until they pass the workbench quality gates. Set `disposition: demoted` and move the source to `dotfiles-agents-workbench/incubator/` when worked.

| Skill | Why | Action |
|---|---|---|
| `api-server-design` | needs testing + quality gates | test -> re-promote or demote |
| `developer-focus` | needs testing + quality gates | test -> re-promote or demote |
| `python-standards` (**hook**, not skill) | needs testing | test the hook |
| `setup-project-dashboard` + `update-project-dashboard` | disambiguate from `board-reporting` | decide overlap, then keep/merge/demote |
| `cms-pdf-to-markdown` | CMS-specific | genericize |
| `cms-json-data-dictionary` | CMS-specific | genericize |
| `cms-bigquery-etl-generator` | CMS-specific | genericize |
| `obsidian-api-basics`, `obsidian-best-practices`, `obsidian-chat-ui`, `obsidian-cli`, `obsidian-dom-helpers`, `obsidian-mcp-server` (whole family) | needs testing + quality gates | test -> re-promote or demote |

## Deliverable B — correct external provenance

Skills currently `origin: authored` that were NOT authored here -> flip to `origin: sourced` and record the upstream (toward `externals.yaml` / #36 clone-at-build).

| Skill(s) | Real upstream |
|---|---|
| `framework-selection` | langchain-ai (https://www.skills.sh/langchain-ai) |
| `openspec-apply-change`, `openspec-archive-change`, `openspec-explore`, `openspec-propose` | the external openspec tool/plugin |

Already correctly `sourced` (no change, confirm only): `shadcn`, `find-skills`, `deep-agents-{core,orchestration,memory}`, `langgraph-persistence`, `langchain-fundamentals`, `langchain-dependencies`.

## Acceptance criteria
- Every skill in Deliverable A is either re-qualified (passes gates, `disposition` upgraded) or has `disposition: demoted` + source moved to the workbench incubator; none remains a distributed `grandfathered-pending-use` authored skill flagged here.
- `framework-selection` and the four `openspec-*` skills read `origin: sourced` with a recorded `upstream`; `make ci` green (roster + targets drift guards).
- No skill named in "already sourced" changed.

## Dependencies & gates
- **Blocks on:** nothing hard. Genericize/disambiguate items (CMS trio, dashboards) may spawn their own sub-work.
- **Gates:** `make check` (roster drift — dispositions/origins change), `make build` + `make build-check` (demoting drops skills from `targets/`), `make ci`. Physical moves to `dotfiles-agents-workbench` are cross-repo (workbench promotion gate applies there). Relates to #36 (clone-at-build externalizes `sourced` skills).

