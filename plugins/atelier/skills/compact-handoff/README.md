# compact-handoff

Prepare compaction without losing the handles needed to continue delegated work.
The skill invokes `handoff`, checks persisted content, and prints a KEEP/DROP prompt
covering active agents, dependent commands, owner rulings and exact next actions.
Persistence failure stops the workflow before compaction.

Use the skill when asked to compact with a handoff. Claude Code also offers the thin
`/atelier:prepare-compact` entrypoint; its distinct name keeps the skill reachable.
Codex invokes the skill directly. Both ship in the `atelier` plugin.

## Install

```sh
claude plugin install atelier@dotfiles-agents
```

For Codex, use `codex plugin add atelier@dotfiles-agents`.

Compaction invocation depends on the runtime. See [verified support and manual
fallbacks](references/runtime-support.md). A prepared prompt is not evidence that
compaction ran, and a summary is not proof that background handles survived.
