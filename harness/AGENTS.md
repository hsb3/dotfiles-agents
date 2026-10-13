# harness

## Project workflow

Architecture lives in groma.md (`.groma/`); change it through the groma CLI, except the few files the skills name.
Committed work lives in backlog.md (`.backlog/`); change it through the backlog CLI, except the few files the skills name. backlog.md's own guide is `backlog instructions overview`.
Follow the groma-backlog-greenfield plugin's skills, one per phase, from `groma-backlog-greenfield:install-and-init` on; each names the next. They are the project workflow groma's block defers to: curate the architecture after a scan without asking first.

## Build rules

- `SPEC.md` is the whole statement of requirements. There is no earlier implementation to consult; build from the spec. Other files committed at init (data, test vectors, assets) are provided by the spec, which names each one; use them as they are.
- SOP steps 0 and 1 are done: the scaffold, `backlog init`, the Definition of Done, `groma init` and the scanners are committed as `init`. Start at `groma-backlog-greenfield:skeleton-and-design`.
- Nobody will answer questions. Where a tool, the plugin or the spec leaves a choice open, decide: a product call goes in the task's implementation notes, a technical choice becomes a backlog decision. Then continue.
- This session is confined to this folder: reads and writes outside it are refused by design, GitHub is unreachable, and no API keys are present. Do not work around a refusal. Tests run offline, with the stubs and fixtures the spec describes; anything that needs a live service is verified after the build, outside this session.
- Skip the plugin's visual check (no browser here); use the terminal equivalents it names.
- Record friction with the plugin and what worked in `SOP-FEEDBACK.md` as you go; commit it with any task.

<!-- groma:start -->
## Groma

This project uses Groma. Before you scan, inspect, or curate architecture, or create, work on, or finish a Backlog task, run `groma agent-instructions` and read the guide it names for that job; for Backlog task work that is `groma agent-instructions backlog`. When it reports a first scan, curate the architecture if the project workflow says to; ask the user whether to curate it only when no project workflow covers curation. Do not edit Groma-owned architecture files directly.
<!-- groma:end -->
