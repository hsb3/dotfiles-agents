# comment-hygiene-gate

`PreToolUse` on `Bash`. Silent unless the command is about to land work — a `git commit` or a
`gh pr create`. On those it reads the change (`git diff --cached` for a commit, the merge-base
diff against the default branch for a PR), scans the **added comment lines only** for history
markers, and names what it found.

Markers: issue and board references, ISO dates, CI run ids, attributions ("owner directive",
"per the review call"), and superseded-history phrasing ("this used to", "the original version
of"). Board-key detection skips the obvious non-refs (`UTF-8`, `SHA-256`, `CVE-*`).

**Prose files are skipped entirely** (`.md`, `.rst`, `.txt`, `.adoc`, and the extensionless
`LICENSE`/`NOTICE`/`CHANGELOG` family). A markdown `#` is a heading and an issue number
mid-sentence is a sentence, so scanning them inverts the rule this hook exists to enforce — a
tracker card, a decisions log, or a handoff is exactly where the harvested history is supposed
to end up.

## Finding a comment

Precision is the whole currency of an advisory nudge: one that cries wolf gets ignored, which
costs more than the findings it would have surfaced. So the lexer errs toward silence.

It walks each added line left to right, **tracking quote state** — a marker inside a string
literal is code, not history (`print("see #NNN")`). Which sequences open a comment is **keyed by
file extension**, because `#` starts a comment in Python and names a colour in CSS; one
universal table is what makes `color: #141413` read as an issue reference. `--` opens a comment
only when followed by a space (otherwise it is `i--` or a CSS custom property), and `//` does
not open one directly after a `:` (a URL scheme). An unrecognized extension falls back to the
hash and C families.

Measured against this repo, using Python's `tokenize` as ground truth on the 156-file Python
corpus: **27 findings in real comments, 1 false.** Across all 425 source files the false
positives from CSS, string literals, and license URLs are gone. The one remaining is the
documented ceiling — a comment character inside a *multi-line* string, whose opening quote sits
on a line a single-line lexer never sees.

Advisory only. It never emits `permissionDecision`, so it cannot block a commit, and it fails
open on every error path: no git, not a repo, no staged diff, an oversized diff, or a malformed
payload all exit silently. A hook that breaks someone's commit is worse than one that misses.

Fires unconditionally, like `context-watermark` and `delegation-watermark`. It reads no
activation file — only the enforcing hooks (`config-custody`, `worker-context`,
`worktree-isolation`) gate on `.claude/atelier.local.md`.

## Why

History and commentary belong on the related task, not in the code. A repo audit found 1,175
of 5,015 source lines were comments, most of them board numbers, dated rulings, CI run ids, and
investigation narratives. Prose in a skill does not make the cleanup happen; a check at the
moment work lands does. The companion `comment-hygiene` skill carries the keep test, the cut
list, and the harvest-before-you-cut rule.

## Configuration

| Env var | Default | Meaning |
|---|---|---|
| `COMMENT_HYGIENE_GIT_TIMEOUT` | `10` | Seconds allowed per git invocation |

## Install

1. Copy this directory into `primitives-core/hooks/`.
2. Symlink it into the plugin assembly the way the other hooks are wired:
   `ln -s ../../../primitives-core/hooks/comment-hygiene-gate plugins/atelier/hooks/comment-hygiene-gate`
3. Add a roster row to `primitives-core.yaml` (id `comment-hygiene-gate`, type `hook`, source
   `primitives-core/hooks/comment-hygiene-gate`, origin `authored`, disposition `qualified`,
   targets `[claude-code]`).
4. Add the `PreToolUse` entry with matcher `Bash` inside the existing top-level `"hooks"`
   object of `plugins/atelier/hooks/hooks.json`.

## Codex

Normalized `Bash` calls use the shared worker registry's effective cwd, so the gate
reads the worker's staged index instead of the inherited parent index. It remains
observational: findings emit context and never deny a commit. Unsupported registry
state is enforced by the worktree boundary hook; this observer still fails open.

Stage and commit in separate tool calls when relying on this advisory. The hook inspects
the index before a command executes; a combined `git add && git commit` can have no staged
bytes yet at that boundary.
