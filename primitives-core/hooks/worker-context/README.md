# worker-context

`SubagentStart` on every subagent. When the project's activation file turns enforcement on, the
hook injects the delegation covenant as `additionalContext`, so the rules a worker is judged by
arrive with the worker instead of depending on the dispatching session restating them in each
brief.

Its companion is `config-custody`, which enforces the same rule at the tool layer. This one makes
sure the worker was told before it is stopped.

Stateless: no ledger, no state file, writes nothing anywhere, and fails open on every error path.

## Why

The source lab's finding F2: the gate is orchestrator property. The rule that config defining
acceptance is read-only lived only in an agent definition, where a task-specific brief can quietly
outrank it, and prose alone cannot make a worker's acceptance config read-only. This pair makes
the ownership map machine-readable and enforced: stated at subagent start it is project policy
rather than one brief's preference, and under `strict` it is also a tool-layer block.

## The covenant

One paragraph, five clauses: (1) configuration that defines acceptance is read-only unless the
brief grants ownership, and an unsatisfiable gate is an escalation rather than a check to weaken;
(2) work in your own worktree and commit there, but never push, merge, or touch state outside it;
(3) a brief without an owned-file list or checkable criteria is reported before the work starts;
(4) verify by running commands and paste actual output; (5) leave no scratch files.

Under `strict` one extra sentence is appended, naming the tool-layer block and telling the worker
that a denied edit *is* the escalation. It is added only under `strict` on purpose: promising a
block that is not armed teaches a worker to discount the rest of the paragraph.

## Activation

Shared with `config-custody`: `<project>/.claude/atelier.local.md`, YAML frontmatter, parsed by a
small tolerant reader (stdlib only, no PyYAML).

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

This hook reads only `enforce:`; the `protected:` list is config-custody's business.

| `enforce` | worker-context | config-custody |
|---|---|---|
| `off`, absent, unknown value, or an unparseable file | inert | inert |
| `advisory` | injects the covenant | logs would-be denials, denies nothing |
| `strict` | injects the covenant + the tool-layer sentence | denies subagent edits to protected paths |

### In a linked worktree

The covenant follows the main checkout. A worker started with its cwd inside a linked worktree
finds no activation file there — it is normally gitignored — so before this resolution the isolated
workers, the ones most in need of the covenant, were the ones that never got it. When no activation
file sits at the project dir, the hook asks `git rev-parse --git-common-dir` whether that dir is a
linked worktree and, if it is, reads the **main checkout's** activation file instead.

The lookup is lazy — it costs a `git` subprocess only when the direct path holds no file. The
consequence is that a **tracked** activation file present in the worktree wins, read at the version
committed on that worktree's branch rather than the main checkout's working-tree version.
`ATELIER_ACTIVATION_FILE` still wins outright and is never re-resolved, and with no `git` on `PATH`
— or a project dir that is not a linked worktree — behaviour is exactly what it was.

## Install

1. Copy this directory into `primitives-core/hooks/`.
2. Symlink it into the plugin assembly the way the other hooks are wired:
   `ln -s ../../../primitives-core/hooks/worker-context plugins/atelier/hooks/worker-context`
3. Add a roster row to `primitives-core.yaml` (id `worker-context`, type `hook`, source
   `primitives-core/hooks/worker-context`, origin `authored`, disposition `qualified`, targets
   `[claude-code]`) — `make ci` reconciles the roster against disk and requires every field,
   `targets` included.
4. Add the `SubagentStart` entry inside the **existing top-level `"hooks"` object** of
   `plugins/atelier/hooks/hooks.json` (wrapper shown for placement; do not add a second one):

```json
{
  "hooks": {
    "SubagentStart": [
      {
        "hooks": [
          {
            "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/hooks/worker-context/hook.py\"",
            "statusMessage": "Briefing worker on the delegation covenant...",
            "timeout": 10,
            "type": "command"
          }
        ],
        "matcher": "*"
      }
    ]
  }
}
```

## Configuration

| Env var | Default | Meaning |
|---|---|---|
| `CLAUDE_PROJECT_DIR` | set by Claude Code | Anchor for the activation file; falls back to the payload `cwd` |
| `ATELIER_ACTIVATION_FILE` | `$CLAUDE_PROJECT_DIR/.claude/atelier.local.md` | Activation file location |

No ledger: the hook is stateless and deliberately has no log path, since a row per subagent start
would record only that a constant string was emitted.

## Design notes

- **Fail-open, always.** Every path exits 0 and prints nothing on error. A broken injection must
  never keep a subagent from starting; a worker briefed only by its dispatcher is the normal case
  this degrades to.
- **Injected, not appended to each brief.** A rule the dispatching session has to remember is a
  rule that goes missing on the busy waves — exactly the ones where it matters.
- **Advisory still injects.** Telling workers the covenant costs nothing and is worth doing while
  `config-custody` is still gathering evidence in advisory mode; only the tool-layer sentence
  waits for `strict`.
- **The activation parser is shared; the sourcing is not.** Parsing lives in
  `hooks/_lib/atelier_local.py` — `_lib/` is a member of every hooks assembly (ADR 0017), so
  importing it is safe where importing another hook's module is not. This hook keeps its own path
  resolution, size cap and fail-open default.
- **Escape hatches.** Set `enforce: advisory` to keep the briefing without the tool-layer sentence,
  or `off` (or delete the activation file) to stand both hooks down.
- **No restart needed to change policy.** The activation file is read on every subagent start, so
  edits take effect on the next dispatch. Only a change to `hooks.json` requires restarting the
  session.
