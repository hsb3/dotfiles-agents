# site

## Project workflow

Architecture lives in groma.md (`.groma/`); change it through the groma CLI, except the few files the skills name.
Committed work lives in backlog.md (`.backlog/`); change it through the backlog CLI, except the few files the skills name. backlog.md's own guide is `backlog instructions overview`.
Follow the groma-backlog-greenfield plugin's skills, one per phase, from `groma-backlog-greenfield:install-and-init` on; each names the next. They are the project workflow groma's block defers to: curate the architecture after a scan without asking first.

## Working on this unit

- This is the documentation-site renderer of dotfiles-agents, landed at `site/` from its build sandbox with its history (git subtree). `SPEC.md` is its requirements of record: a change in behaviour updates `SPEC.md` in the same task.
- Start agent sessions in this folder. backlog and groma read `.backlog/` and `.groma/` here; from the repository root they report that nothing is initialised. Sessions need the `groma-backlog-greenfield` plugin (`groma-extras` marketplace).
- New work is a task on this unit's board, built with the plugin's build-task loop, one commit per task; a release closes with its close-release skill.
- Gate: `bunx tsc --noEmit && bun test` (CI lane `.github/workflows/site-test.yml`). `make docs-build` at the repository root builds the real site, and the `drift guards` CI job runs it on every pull request as the repo-wide link check.
- Dependencies are pinned exactly; Bun's 3-day `minimumReleaseAge` rejects anything newer.

<!-- groma:start -->
## Groma

This project uses Groma. Before you scan, inspect, or curate architecture, or create, work on, or finish a Backlog task, run `groma agent-instructions` and read the guide it names for that job; for Backlog task work that is `groma agent-instructions backlog`. When it reports a first scan, curate the architecture if the project workflow says to; ask the user whether to curate it only when no project workflow covers curation. Do not edit Groma-owned architecture files directly.
<!-- groma:end -->
