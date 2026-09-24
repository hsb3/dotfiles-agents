# Per-project activation — `atelier.local.md`

The plugin's enforcement layer is off until a project turns it on. One file controls it:
`atelier.local.md`, in the selected native or shared directory at the project root (gitignored by
convention — the harness attaches no behavior to this file; atelier's skill and hooks read it
themselves, per call, so editing it needs no restart).

<!-- harness:claude-code -->
Use the activation skill’s selected policy: the sole native agent directory, or
`.agents` for multiple configured agents. Explicit overrides win; runtime reads never
migrate files. Setup safely relocates policies and rejects divergent copies.

```markdown
---
effort: deep          # optional: force the effort level (Step 0)
enforce: strict       # off (default when absent) | advisory | strict
protected:            # fnmatch patterns, project-relative; * crosses /
  - Makefile
  - .github/workflows/*
  - "*.config.js"
isolate: writers      # optional: off (default when absent) | writers | a list of agent types
protected-branches:   # optional: branch names a subagent may not commit or push onto.
  - main              # No default — an unset key leaves that half of the guard inert.
handoff: docs/HANDOFF.md   # optional: override the project's handoff location — a file
                           # path (above), or a {mode: external} mapping for a tracker
                           # or board (see below)
---
```
<!-- /harness -->

| `enforce` | `worker-context` | `config-custody` |
|---|---|---|
| absent / `off` | silent | silent |
| `advisory` | injects the worker covenant into every subagent | logs would-deny rows to the `config-custody` stream; never blocks |
| `strict` | injects, naming the tool-layer block | denies subagent edits to `protected:` paths, with an escalation-shaped reason |

<!-- harness:claude-code -->
`worker-context` runs on SubagentStart and `config-custody` on PreToolUse.
<!-- /harness -->

## Which copy of the file a hook reads

<!-- harness:claude-code -->
**Enforcement follows the main checkout into a linked worktree.** A worktree is a clean checkout
of a ref, and the activation file is conventionally ignored, so a worker running inside one used
to find no file at all and run with custody and the covenant silently off — in exactly the
dispatch shape isolation exists to protect. Every hook that reads the file now falls back to the
main checkout when it finds nothing at the worktree's own path, so a project that keeps the file
local keeps its enforcement.

**A tracked activation file is seen at its committed version there — by `config-custody`.** When
the file *is* tracked, the worktree carries its own copy, and that copy at the worktree's `HEAD` is
the policy `config-custody` enforces. Uncommitted edits to a tracked activation file therefore do
not reach workers until they are committed, and a copy that is present but untracked governs
nothing. Tracking the file is still worth it (it travels to a fresh clone and to a second machine);
just commit a policy change before dispatching against it.

The other hooks that read this file — `worker-context`, `worktree-isolation`,
`worker-git-scope-guard`, `handoff-freshness-guard`, `session-handoff-surfacer` — resolve from the
project directory alone, which Claude Code sets to the main checkout for the hook process even
inside a worktree. A worktree's own copy does not yet steer them, so a committed policy change on a
worker's branch can leave the covenant it is handed disagreeing with the gate it hits.

The fallback also covers what the file *names*, not only the file: a `handoff:` path and its
freshness stamp resolve through the main checkout too, so a worker in a worktree is neither told
there is no handoff nor refused a compaction over a stamp that only ever existed one directory
up. An explicit environment override of the activation file's location still wins outright and is
never re-resolved. With no `git` available, or a project directory that is not a worktree,
nothing about any of this changes.
<!-- /harness -->

`isolate` is read by `worktree-isolation`, which fires before a dispatch, and is independent of
`enforce` — a project can isolate writers without arming custody, or the reverse. It rewrites the
dispatch to run a writing worker in its own git worktree instead of sharing the strategist's
working tree and index.

<!-- harness:claude-code -->
The hook is PreToolUse on the `Agent` tool, and the rewrite adds `isolation: "worktree"` to the
call.
<!-- /harness -->

| `isolate:` | Effect |
|---|---|
| absent, `off`, any other scalar, or an unparseable file | inert |
| `writers` | isolates `builder`, `manager`, and the harness's built-in general-purpose agent |
| a list, block or inline (`[builder, my-writer]`) | isolates exactly those agent types |
| an empty list, or a bare `isolate:` with no items | inert — an empty set is an empty intent, not a request for the built-ins |

<!-- harness:claude-code -->
The built-in is `general-purpose`.
<!-- /harness -->

**`scout`, `reviewer`, and any other read-only role are never isolated, even when listed.** A
worktree is a clean checkout of a ref, so uncommitted and untracked files in the parent do not
exist inside it; isolating a reviewer would point it at a tree that lacks the very diff it was
sent to re-derive. The same caveat binds writers: a builder that must see uncommitted work needs
the work committed first, or that dispatch left un-isolated. The hook also stands down when the
dispatch already sets isolation or a working directory, and outside a git repository (where
forcing isolation is a hard error rather than a no-op).

<!-- harness:claude-code -->
The harness's own `Explore`, `Plan`, and `fork` agents are on the never-isolated list too.
<!-- /harness -->

<!-- harness:claude-code -->
`protected-branches` is read by `worker-git-scope-guard` and is a **separate key from
`protected:`**, which means protected file *paths* and is read by `config-custody`. Overloading
one key for two different kinds of thing would make both harder to read; they are independent and
either can be armed alone. The guard binds subagents only — the strategy layer owns integration,
so a hook that denied the session its own merge would be denying the layer that is supposed to do
it — and it covers two failures that were measured, not imagined:

| `protected-branches:` | Effect on a subagent's Bash command |
|---|---|
| absent, empty, or unparseable | the branch half is inert; the shared-tree half below still applies |
| a list, block or inline (`[main, release]`) | `commit`/`merge`/`rebase`/`cherry-pick`/`revert`/`am` are denied while HEAD is on a listed branch, and `push` is denied when its refspec targets one (falling back to the current branch when the push names no refspec) |

There is **no default list, deliberately.** `{main, master}` is wrong for any project whose working
branch is `main`, and equally wrong for one where `main` is a publish-only surface and the real
working branch is something else. A project that has not named its branches has not made the
decision, and the guard stays out of it.

The second half needs no key at all and cannot be turned off by one: a subagent working in a
**shared, un-isolated tree** — the parent's own checkout, not a linked worktree of its own — is
denied the mutating `git stash` forms outright. There is only one tree, so "stay inside your own
worktree" has nothing to bind, and a conflicted `stash pop` followed by a `drop` has already
destroyed a sibling's work irrecoverably. Inside its own linked worktree a worker may stash
freely, which is exactly the isolation `isolate:` buys. `stash list` and `stash show` are reads
and never fire.

`worker-git-scope-guard` is the peer-to-peer sibling of `live-worker-git-guard`, not a duplicate
of it: that one stops an *orchestrator* from clobbering the uncommitted state of children it
started, keyed off its own pending set, and it exempts an agent holding its own worktree. Two peer
builders are nobody's children, so their pending sets are empty and it never fires for them.
<!-- /harness -->

`handoff` names where the project's handoff lives, read by `session-handoff-surfacer`,
`handoff-freshness-guard`, and the `handoff` skill — all three otherwise search
`_meta/HANDOFF.md`, `HANDOFF.md`, `.claude/HANDOFF.md` in that order. It takes two forms: a bare
scalar path (`handoff: docs/HANDOFF.md`), or a mapping with a `mode` sub-key (`file` | `external`,
defaulting to `file` when the mapping omits it). The scalar form and `{mode: file, path: ...}` are
identical.

<!-- harness:claude-code -->
`session-handoff-surfacer` runs on SessionStart and `handoff-freshness-guard` on PreCompact.
<!-- /harness -->

**File mode** — `path` (the scalar, or the mapping's `path:`) is authoritative over the
standard search, with fail-open exceptions:

| `handoff:` (file mode) | Effect |
|---|---|
| absent, unparseable activation file, or an activation file with other keys but not this one | standard search runs unchanged |
| `path` resolves outside the project root | rejected; standard search runs unchanged |
| `path` names a file that exists (inside the project root) | wins over any standard candidate, even one that also exists |
| `path` names a file that does not (yet) exist (inside the project root) | treated as "no handoff" — does **not** fall back to the standard search, so a stale file left at a standard location is never resurrected |

**External mode** — for a handoff that lives on a tracker or board, not a file in this repo.
`stamp` is a project-relative path the `handoff` skill touches (never writes content to) as a
freshness signal; `location` is free text naming where the handoff actually lives — never
path-resolved, and optional:

| `handoff:` (external mode) | Effect |
|---|---|
| `stamp` absent, blank, or resolves outside the project root | the whole key is inert; standard search runs unchanged |
| `mode` present but neither `file` nor `external` | inert; standard search runs unchanged |
| `stamp` resolves inside the project root, file does not exist yet | armed: `handoff-freshness-guard` reads this as "missing" (same as a stale/absent file in file mode); `session-handoff-surfacer` still surfaces the `location` pointer on a cold session regardless — silence at cold start is the bug external mode exists to fix |
| `stamp` resolves inside the project root, file exists | armed: freshness judged by the stamp's mtime against the same freshness window file mode uses |

## The context watermark

`context-watermark` nudges toward a handoff at a soft and a hard threshold. **Scale those
thresholds to the model's own context window rather than fixing them as a flat count** — a fixed
number means different things on a 200k-window model and a 1M-window one. How far each harness has
taken that is its own business, and each states its concrete mechanism below.

<!-- harness:claude-code -->
The hook computes each stage as `min(layer_value × complexity, frac × window)`, with `frac` 0.30
for notice, 0.60 for soft and 0.80 for hard. `layer_value` comes from one of two bands, chosen by
whether the payload carries `agent_id`: worker 100k/160k/250k, session 150k/250k/400k
(notice/soft/hard). `window` comes from the model id on the transcript's last assistant line (no
hook payload carries a `model` field); `complexity` is 1.0 unless the activation file sets it.
The absolute terms are why a 1M-window model is still nudged: percent-of-window thresholds alone
were inert against the ~967k auto-compact default. An unknown model, or one the catalog has no
window for, gets the band values uncapped — never a fraction of an assumed window — and writes a
ledger row marking the fallback, so a check that could not measure never looks like one that
measured and found nothing.

Precedence, applied per value: `CONTEXT_WATERMARK_NOTICE` / `_SOFT` / `_HARD` in the environment
(how an external coordinator such as wave-lanes sets session numbers), then a `watermark:` key in
the activation file (`notice`, `soft`, `hard`, `complexity`, each independently optional and each
fail-open to the tier below; a `worker:` or `session:` sub-mapping overrides the flat keys for
that layer), then the computed default. The wiring deliberately supplies no shell-expanded env
default: that would leave the variable always set, and the top tier would win forever.

A delegated worker is watched on `PostToolUse` (only a worker's payload carries `agent_id`),
against the worker band, because it cannot hand off, compact, or start a fresh session — the
nudge therefore names the one move it has, wrap up and report. Read the hook
for the values actually in force before quoting a number.
<!-- /harness -->

## Design commitments

- **The strategy layer is never restricted.** Custody is role-scoped: it applies only inside
  subagents, never to the main session. The strategist owns config and git; no mode changes that.
  The `manager` is a subagent, so custody binds the management layer too, which is the intended
  reading: only the layer that wrote the definition of done may edit what checks it.
- **Path custody does no command matching.** It is fnmatch against a list the project wrote —
  Step 3's ownership map made machine-readable, with no command string anywhere in it. Whether
  anything below it parses a command at all is a harness question, answered next.

<!-- harness:claude-code -->
- **The git guards do parse commands, and say so.** Git was left advisory for a long time on the grounds that
  blocking a push or a merge means matching Bash command strings, which is brittle. Two losses
  measured in the field overrode that: sibling workers in one shared tree destroying each other's
  uncommitted work with `git stash`, and a worker whose HEAD sat on a publish-only branch
  committing to the real one. `protected-branches:` therefore arms a guard that *does* parse the
  command, and it states its own ceiling rather than pretending to contain anything: a shell
  script, or git driven through some other tool, walks straight past it. Server-side branch
  protection is the layer that actually contains those; this one catches the path agents take and
  leaves a refusal in the transcript. A project that wants a broader hard block can still add deny
  rules to its own harness config — noting that permission rules are not role-scoped and bind the
  main session too.
<!-- /harness -->

- **Fail-open.** A missing, malformed, or unrecognized activation file means `off`. A hook error
  can never produce a deny.
- **Escape hatches.** Drop to `advisory` (or remove the key) to stop blocking everywhere; lift a
  single pattern to hand one file's ownership to a wave. The deny message itself routes the
  worker to the doctrinally correct move — escalate, never route around.
- **False-positive story.** A brief that legitimately grants config ownership hits the deny once;
  the worker reports the conflict; the strategist lifts the pattern for that wave or makes the edit
  itself. One bounced tool call is the entire cost.
- **Graduation path.** Run `advisory` first: the would-deny ledger shows exactly what `strict`
  would have blocked. Move to `strict` when the log shows no false positives.

<!-- harness:claude-code -->
Role scoping rides on the documented `agent_id` hook payload field, present only inside subagents.
The deny-rule syntax is `permissions.deny` in the project's `settings.json`, for example
`Bash(git push *)`.
<!-- /harness -->

The custody model is `[untested]` (see `provenance.md`): the mechanism is proven by fixtures and
an adversarial matrix, but no real project has run under `strict` yet.
