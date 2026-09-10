# Compaction surfaces

Verified 2026-09-10 against installed Claude Code 2.1.266, Codex CLI 0.154.0,
and OpenCode 1.18.29. Recheck when the runtime or exposed tools change; do not
reinterpret user command syntax as an agent capability.

| Runtime | Established surface | Skill fallback |
|---|---|---|
| Claude Code 2.1.266 | Local `/compact` accepts optional summarization instructions; Skill cannot invoke it. | Print `/compact` followed by the completed prompt for the owner. |
| Codex CLI 0.154.0 | User `/compact`; app-server clients can call `thread/compact/start` with `threadId`. No ordinary agent compaction tool was exposed. | Submit the prompt as a normal message first, then use `/compact` separately. No custom command arguments are assumed. |
| OpenCode 1.18.29 | User `/compact`; server clients can POST `/session/:id/summarize` with model/provider fields. No prompt field. | Submit the prompt as a normal message first, then use `/compact` separately. |

Client APIs are controller surfaces, not tools automatically available to the model.
An API success response is not completion: observe the runtime's completion signal.
Without a custom-instructions surface, the submitted prompt becomes conversation
context; exact summarizer compliance is not guaranteed. Read back the resulting
summary/handoff and verify the original handles before claiming continuation.

## Official documentation

- [Claude skills](https://code.claude.com/docs/en/skills#restrict-claudes-skill-access)
  explicitly excludes `/compact` from Skill invocation. The [command reference](https://code.claude.com/docs/en/commands)
  documents its optional focus instructions. Hooks observe lifecycle events; they
  do not make this local command a model tool.
- [Codex commands](https://learn.chatgpt.com/docs/developer-commands?surface=cli)
  describes user `/compact`; [app-server](https://learn.chatgpt.com/docs/app-server#trigger-thread-compaction)
  documents the separate client request and `contextCompaction` item lifecycle.
- [OpenCode server](https://opencode.ai/docs/server/#sessions) documents summarize;
  its [plugins](https://opencode.ai/docs/plugins/) expose a compaction prompt hook.
  Installing such an integration is not part of this skill.

## Installed native evidence

- `claude --version`: 2.1.266. Its native binary registers `compact` as `type:"local"`,
  `supportsNonInteractive:true`, with optional custom summarization instructions.
  The Skill implementation rejects non-prompt commands (`skill_invoke_not_prompt_type`).
- `codex --version`: 0.154.0. Its binary registers `thread/compact/start` and a
  one-field `ThreadCompactStartParams`. The ordinary session tool inventory has no
  compact tool. Generating the installed app-server schema can confirm its fields.
- `opencode --version`: 1.18.29. Its embedded SDK's summarize request accepts
  `providerID`, `modelID`, and `auto`; the TUI invokes that endpoint. Its
  `experimental.session.compacting` hook can replace the prompt, separately from
  the summarize request. No existing agent-tool exposure was established.

Keep the command named `prepare-compact` and the skill named `compact-handoff`.
They must not compete for the same dispatch name. The command contains only a skill
invocation; it must load the skill body, not recursively invoke itself.
