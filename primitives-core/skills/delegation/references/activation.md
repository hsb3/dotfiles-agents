# Per-project activation — `.claude/atelier.local.md`

The plugin's enforcement layer is off until a project turns it on. One file controls it:
`.claude/atelier.local.md` in the project root (gitignored by convention — the harness attaches no
behavior to this file; atelier's skill and hooks read it themselves, per call, so editing it needs
no restart).

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

| `enforce` | `worker-context` (SubagentStart) | `config-custody` (PreToolUse) |
|---|---|---|
| absent / `off` | silent | silent |
| `advisory` | injects the worker covenant into every subagent | logs would-deny rows to the `config-custody` stream; never blocks |
| `strict` | injects, naming the tool-layer block | denies subagent edits to `protected:` paths, with an escalation-shaped reason |

`isolate` is read by `worktree-isolation` (PreToolUse on the `Agent` tool) and is independent of
`enforce` — a project can isolate writers without arming custody, or the reverse. It rewrites a
dispatch to carry `isolation: "worktree"` so a writing worker gets its own checkout instead of
sharing the strategist's working tree and index.

| `isolate:` | Effect |
|---|---|
| absent, `off`, any other scalar, or an unparseable file | inert |
| `writers` | isolates `builder`, `manager`, `general-purpose` |
| a list, block or inline (`[builder, my-writer]`) | isolates exactly those agent types |
| an empty list, or a bare `isolate:` with no items | inert — an empty set is an empty intent, not a request for the built-ins |

**`scout`, `reviewer`, `Explore`, `Plan`, and `fork` are never isolated, even when listed.** A
worktree is a clean checkout of a ref, so uncommitted and untracked files in the parent do not
exist inside it; isolating a reviewer would point it at a tree that lacks the very diff it was
sent to re-derive. The same caveat binds writers: a builder that must see uncommitted work needs
the work committed first, or that dispatch left un-isolated. The hook also stands down when the
dispatch already sets `isolation` or `cwd`, and outside a git repository (where forcing isolation
is a hard error rather than a no-op).

`handoff` names where the project's handoff lives, read by `session-handoff-surfacer`
(SessionStart), `handoff-freshness-guard` (PreCompact), and the `handoff` skill — all three
otherwise search `_meta/HANDOFF.md`, `HANDOFF.md`, `.claude/HANDOFF.md` in that order. It takes
two forms: a bare scalar path (`handoff: docs/HANDOFF.md`), or a mapping with a `mode` sub-key
(`file` | `external`, defaulting to `file` when the mapping omits it). The scalar form and
`{mode: file, path: ...}` are identical.

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

## Design commitments

- **The strategy layer is never restricted.** Custody is role-scoped through the documented
  `agent_id` hook payload field, present only inside subagents. The strategist owns config and git;
  no mode changes that. A `manager` is a subagent, so custody binds the management layer too, which
  is the intended reading: only the layer that wrote the definition of done may edit what checks
  it.
- **No command matching.** Path custody is fnmatch against a list the project wrote — Step 3's
  ownership map made machine-readable. Mutating git by workers stays advisory (the injected
  covenant plus the reconciliation check in `briefs.md`), because blocking it would require
  matching Bash command strings, which is brittle by design. A project that wants a hard git
  block can add `permissions.deny` rules (for example `Bash(git push *)`) to its own
  settings.json — noting that permission rules are not role-scoped and bind the main session too.
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

The custody model is `[untested]` (see `provenance.md`): the mechanism is proven by fixtures and
an adversarial matrix, but no real project has run under `strict` yet.
