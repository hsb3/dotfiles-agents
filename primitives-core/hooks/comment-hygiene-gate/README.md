# comment-hygiene-gate

`PreToolUse` on `Bash`. Silent unless the command is about to land work — a `git commit` or a
`gh pr create`. On those it reads the change (`git diff --cached` for a commit, the merge-base
diff against the default branch for a PR), scans the **added comment lines only** for history
markers, and names what it found.

Markers: issue and board references, ISO dates, CI run ids, attributions ("owner directive",
"per the review call"), and superseded-history phrasing ("this used to", "the original version
of"). Board-key detection skips the obvious non-refs (`UTF-8`, `SHA-256`, `CVE-*`).

**Prose files are skipped entirely** (`.md`, `.rst`, `.txt`, `.adoc`, and friends). A markdown
`#` is a heading and an issue number mid-sentence is a sentence, so scanning them inverts the rule
this hook exists to enforce — a tracker card, a decisions log, or a handoff is exactly where
the harvested history is supposed to end up. Measured against 40 commits of this repo's own
history before the skip existed: 25 would have fired, 73 of 75 findings were markdown. After:
2 fired, both true positives in a `.yml` comment.

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
