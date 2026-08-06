# config-custody

Makes a project's ownership map machine-readable. `PreToolUse` on `Edit`, `Write`, `MultiEdit`, and
`NotebookEdit`: when a **subagent** tries to edit a path listed under `protected:` in
`.claude/atelier.local.md`, the hook denies the call and tells the worker what to do instead —
stop and report, do not route around it.

The main session is never restricted. No `agent_id` in the payload means the orchestrator is
editing, and the orchestrator owns the gate.

Its companion is `worker-context`, which states the same rule at subagent start. One tells the
worker; this one enforces it.

## Why

The source lab's finding F2: the gate is orchestrator property. A worker that can edit the config
defining its own acceptance can always make its brief pass, and the rule against doing so lived
only in prose an agent may reasonably read as advice. Prose alone cannot make a worker's
acceptance config read-only. This pair makes the ownership map a file the tools read, so the rule
holds at the point the edit happens rather than at the point someone remembers to restate it.

## Activation

Both hooks are inert until `<project>/.claude/atelier.local.md` exists and turns them on. YAML
frontmatter, parsed by a small tolerant reader (stdlib only, no PyYAML):

```markdown
---
effort: deep
enforce: strict
protected:
  - Makefile
  - .github/workflows/*
  - "*.config.js"
  - configs/*
---
```

Only `enforce:` and `protected:` are read; other keys and the prose below the frontmatter are
ignored. `protected:` also accepts the inline form `protected: ["Makefile", "configs/*"]`.

| `enforce` | config-custody | worker-context |
|---|---|---|
| `off`, absent, unknown value, or an unparseable file | inert | inert |
| `advisory` | logs would-be denials, denies nothing | injects the covenant |
| `strict` | denies subagent edits to protected paths | injects the covenant + the tool-layer sentence |

## Install

1. Copy this directory into `primitives-core/hooks/`.
2. Symlink it into the plugin assembly the way the other hooks are wired:
   `ln -s ../../../primitives-core/hooks/config-custody plugins/atelier/hooks/config-custody`
3. Add a roster row to `primitives-core.yaml` (id `config-custody`, type `hook`, source
   `primitives-core/hooks/config-custody`, origin `authored`, disposition `qualified`, targets
   `[claude-code]`) — `make ci` reconciles the roster against disk and requires every field,
   `targets` included.
4. Add the `PreToolUse` entry inside the **existing top-level `"hooks"` object** of
   `plugins/atelier/hooks/hooks.json` (wrapper shown for placement; do not add a second one):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "hooks": [
          {
            "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/hooks/config-custody/hook.py\"",
            "statusMessage": "Checking config custody...",
            "timeout": 10,
            "type": "command"
          }
        ],
        "matcher": "Edit|Write|MultiEdit|NotebookEdit"
      }
    ]
  }
}
```

## Configuration

| Env var | Default | Meaning |
|---|---|---|
| `CLAUDE_PROJECT_DIR` | set by Claude Code | Jurisdiction anchor; falls back to the payload `cwd` |
| `ATELIER_ACTIVATION_FILE` | `$CLAUDE_PROJECT_DIR/.claude/atelier.local.md` | Activation file location |
| `ATELIER_CUSTODY_LOG_PATH` | `$CLAUDE_PROJECT_DIR/logs/config-custody.jsonl` | Ledger |

## Design notes

- **Fail-open, always.** Every path exits 0, and an exception can never produce a deny: a broken
  hook must not become a broken editor. Unparseable activation file, unreadable ledger, missing
  anchor — all mean "off".
- **The main session is never restricted.** The absence of `agent_id` is the whole test. The
  orchestrator lifting a pattern or making the edit itself is the intended escape hatch.
- **fnmatch, never regex, and `*` crosses `/`.** Patterns are globs written by hand, matched with
  `fnmatch.fnmatch` against the project-relative path and again against the absolute path so
  absolute patterns work. Because fnmatch's `*` does not stop at a separator, `configs/*` protects
  the entire subtree — `configs/deep/nested/app.yaml` is covered. That is usually what a person
  writing `configs/*` meant; if you want direct children only, name them.
- **Matching is lexical, not `realpath`.** Paths are normalized (`..` collapsed, relative paths
  anchored on the project dir), but a symlink aimed at a protected file is not caught. This is a
  guardrail on honest tool calls, not a sandbox — which is also why the deny text names shell
  routing explicitly instead of trying to block it.
- **Out of jurisdiction is silent.** A path outside the project resolves to a relpath starting
  with `..` and is left alone; the hook has no opinion about files it does not own.
- **Advisory logs would-be denials.** Turning enforcement on blind is how a guardrail earns a
  reputation for false positives. Run `advisory` for a few waves, read the ledger, and graduate to
  `strict` on evidence.
- **When a deny is wrong.** A brief that legitimately hands a worker ownership of a protected file
  hits the deny once; the worker reports the conflict rather than working around it, and the
  orchestrating session either lifts the pattern for that wave or makes the edit itself. One
  round trip, no silent gate erosion. To stand the whole thing down, set `enforce: advisory` or
  `off`.
- **No restart needed to change policy.** The activation file is read on every call, so edits to
  `enforce:` or `protected:` take effect on the next tool call. Only a change to `hooks.json`
  requires restarting the session.

## Ledger

One row per **match**, appended to `logs/config-custody.jsonl` — denials and, in advisory mode,
would-be denials. Edits that match nothing are not logged, so the file stays a record of contested
paths rather than a transcript of every edit:

```json
{"session_id":"...","agent_type":"builder","tool_name":"Edit","path":"Makefile",
 "pattern":"Makefile","mode":"strict","denied":true}
```

`"denied": false` with `"mode": "advisory"` is a would-be denial: the edit went through, and this
row is the evidence for whether `strict` would have been right.
