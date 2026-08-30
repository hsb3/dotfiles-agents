# Per-project activation — `atelier.local.md`

The plugin's enforcement layer is off until a project turns it on. One file controls it:
`atelier.local.md`, in the harness's own config directory at the project root (gitignored by
convention — the harness attaches no behavior to this file; atelier's skill and hooks read it
themselves, per call, so editing it needs no restart).

<!-- harness:claude-code -->
The path is `.claude/atelier.local.md`.

```markdown
---
effort: deep          # optional: force the effort level (Step 0)
enforce: strict       # off (default when absent) | advisory | strict
protected:            # fnmatch patterns, project-relative; * crosses /
  - Makefile
  - .github/workflows/*
  - "*.config.js"
isolate: writers      # optional: off (default when absent) | writers | a list of agent types
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
The hook nudges on **absolute token counts**, overridable per environment with
`CONTEXT_WATERMARK_SOFT` and `CONTEXT_WATERMARK_HARD`. There is no window-relative arithmetic and
no `complexity:` key here: percent-of-window thresholds were inert against the ~967k auto-compact
default, so the figures in `SKILL.md` are stated absolutely. Read the hook for the values actually
in force before quoting a number.
<!-- /harness -->

## Design commitments

- **The strategy layer is never restricted.** Custody is role-scoped: it applies only inside
  subagents, never to the main session. The strategist owns config and git; no mode changes that.
  The `manager` is a subagent, so custody binds the management layer too, which is the intended
  reading: only the layer that wrote the definition of done may edit what checks it.
- **No command matching.** Path custody is fnmatch against a list the project wrote — Step 3's
  ownership map made machine-readable. Git stays advisory (the injected covenant plus the
  reconciliation check in `briefs.md`), because blocking a push or a merge would require matching
  Bash command strings, which is brittle by design. A project that wants a hard block on the
  operations reserved to the session can add deny rules to its own harness config — noting that
  permission rules are not role-scoped and bind the main session too.
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
