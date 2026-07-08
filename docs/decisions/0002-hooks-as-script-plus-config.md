---
title: "Hooks as script + config, never inline"
type: decision
status: Accepted
created: 2026-06-28
updated: 2026-07-03
summary: A hook is a directory (config + event-named script), never inline bash in settings.json.
---

# 0002 · Hooks as script + config, never inline

_A hook is a directory (config + event-named script), never a raw command string in
`settings.json`._

- **Provenance:** working convention since the Phase-2 migration (2026-06-28); ADR
  backfilled 2026-07-03 per #40
- **Raised by:** the dotfiles hook-packaging convention (hook dirs with `config.json` + a
  script — never inline bash in `.claude/settings.json`); encoded in the workbench gate H4
  and the naming grammar `<plugin>.<Event>.<slug>.sh` (`docs/naming.md`)

## Context

Claude Code accepts hooks two ways: inline command strings in `.claude/settings.json`, or
script files referenced by config. Inline hooks are undiffable against the packaged hook
set, unreviewable in isolation, invisible to the naming lint, and impossible to distribute
through the translation service (which ships hook *files* to claude-code targets).

## Decision

Hooks are packaged as **script + config**: an event-named script file
(`<plugin>.<Event>.<slug>.sh`, stdlib-only per gate H4) plus the JSON config that wires it.
`settings.json` may only *reference* hook scripts, never carry inline command strings.

## Consequences

- The repo meta-structure audit's interim `HOOK-01` check (`no-inline-hooks`) is sourced
  directly from this decision; the full `HOOK-xx` family arrives with the deferred
  hook-composition standard.
- The workbench gate blocks promotion on hook filename grammar (H2/H4).
- Machine-local one-off hooks still follow the same shape — there is no "quick inline"
  escape hatch.

## Affects

`primitives-core/hooks/` packaging · repo-meta-structure `references/checklist.md` HOOK-01
(the check that cites this ADR) · workbench `scripts/promote_check.py` H2/H4 ·
`docs/naming.md` hook grammar.
