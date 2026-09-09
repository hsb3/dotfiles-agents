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

### In a linked worktree

**Custody follows the tree the edited file lives in.** A worker dispatched with
`isolation: "worktree"` lands in a linked checkout, and that raises two separate questions: which
activation file supplies the patterns (**policy**), and what the edited path is relative to
(**jurisdiction**).

Policy resolves in this order, first hit wins:

1. `ATELIER_ACTIVATION_FILE` — an explicit override, never re-resolved.
2. `.claude/atelier.local.md` in the linked worktree the **edited file** sits in — including when
   that worktree *is* the project dir — read at `HEAD` via `git show`, never from disk.
3. `$CLAUDE_PROJECT_DIR/.claude/atelier.local.md` on disk, falling back to the payload `cwd`'s.
4. The **main checkout's** copy, when 3 holds no file and that dir is a linked worktree — asked via
   `git rev-parse --git-common-dir`, so an activation file that is gitignored and therefore never
   travelled still governs the worktree it did not reach.

Step 2 is tried only when that worktree holds a copy on disk, so a tree with no copy costs nothing
extra; when it does hold one, the `git show` is one subprocess per `Edit`/`Write` — measured at
~50 ms end to end on a live worktree. Both git reads are bounded at 3 s and can run on the same
call, so the worst case is 6 s plus interpreter startup, inside the 10 s `config.json` declares
with room to spare. Each failure falls to the next step, so with no `git` on `PATH` policy comes
from step 3 on disk, which is where it came from before any of this resolution existed.

**The committed version is what governs, deliberately, and an uncommitted one has no effect at
all.** Editing your own `.claude/atelier.local.md` is a permitted `Edit` in most projects, so
reading it from disk would let a worker turn the gate off for the rest of the session with one
tool call and no trace. Untracked, deleted, unborn `HEAD`, no `git`, timeout: none of those is a
committed copy, and each falls through to step 3.

Two ceilings on that, because it is a guardrail on honest tool calls and not a sandbox. **The
`.git` file is trusted.** A worktree root is any directory under the project whose `.git` is a
file, and the hook does not check where that file points — rewrite it and `git show` reads a
different repository. **`HEAD` is the tree's HEAD, not the branch you will review.** A detached
`HEAD` inside the worktree is what governs there, which need not be the tip of the branch the work
lands on.

**A worker can still un-govern its own tree, by committing** a permissive activation file:
`enforce: off`, a shorter `protected:` list, or a file mangled past parsing all mean "off" there,
and so does an empty one. That is intended — policy inside a worktree belongs to that tree, and
unlike a disk edit the change is a commit. It reaches no further: policy is resolved from the
worktree of the **edited file**, never from the caller's cwd, so an edit aimed at the main checkout
or at a second worktree is judged by that tree's own policy.

Jurisdiction is the second resolution, and it matters more often than it looks. Claude Code sets
`CLAUDE_PROJECT_DIR` on the *hook process* even when the worker's own shell has none, and it points
at the **main checkout** — so an isolated worker whose worktree carries no copy of its own is
governed at step 3, with nothing below it firing. What breaks then is the pattern match:
relativizing the edited file against the main checkout turns every path the worker touches into
`.claude/worktrees/agent-<id>/Makefile`, which no project-relative pattern can match, silently
exempting exactly the workers custody is aimed at.

So the edited path is relativized against the **worktree root** when it sits inside one:
`Makefile` means that worktree's `Makefile`. The root is found by walking up from the edited file
to the first directory holding a `.git` **file** — a linked worktree's `.git` is a file pointing at
the shared git dir, where an ordinary checkout's is a directory, so a vendored sub-repo nested in
the project is correctly *not* a jurisdiction. The walk stops at the project dir, so custody can
never be relocated to a tree outside the project, and a path outside the project is still not
governed at all. No subprocess: a handful of `os.path` calls on the miss.

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
| `ATELIER_CUSTODY_LOG_PATH` | `${XDG_DATA_HOME:-~/.local/share}/agent-logs/claude-code/atelier/config-custody.jsonl` | Ledger |

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

One row per **match**, appended to the `config-custody` stream — denials and, in advisory
mode, would-be denials.

Ledgers live outside the project, in one partitioned root shared with every other hook in
this plugin (and with the opencode mirror, which writes under its own `<harness>` segment):

```
${XDG_DATA_HOME:-~/.local/share}/agent-logs/<harness>/<plugin>/<stream>.jsonl
```

Every row carries an identity envelope — `v`, `plugin`, `harness`, `stream`, `ts`
(ISO-8601 UTC), `project` — so a row stays attributable after the files are concatenated.
The append path is `hooks/_lib/agentlog.py`; no hook writes its own rows.

Edits that match nothing are not logged, so the stream stays a record of contested paths
rather than a transcript of every edit:

```json
{"v":1,"plugin":"atelier","harness":"claude-code","stream":"config-custody",
 "ts":"2026-08-20T15:37:08.666Z","project":"/repo/x",
 "session_id":"...","agent_type":"builder","tool_name":"Edit","path":"Makefile",
 "pattern":"Makefile","mode":"strict","denied":true}
```

`"denied": false` with `"mode": "advisory"` is a would-be denial: the edit went through, and this
row is the evidence for whether `strict` would have been right.

## Codex

With `ATELIER_HARNESS=codex`, custody examines every path header in normalized
`apply_patch` command text, including both sides of moves, using the shared worker
registry's effective checkout. Strict mode denies the entire patch when any path
matches; advisory emits context, and off remains inert. Routing/identity failures
in an armed project deny the operation. Claude file-path handling is unchanged.
