---
name: activation
description: Create and verify the per-project `.claude/atelier.local.md` activation file that arms atelier's hooks. Use when someone asks to turn on, configure, or check atelier enforcement (custody, worker context, worktree isolation, handoff routing) in a project, or when a hook that should be firing appears silent.
---

# Activation

`.claude/atelier.local.md` is the one file that arms atelier's enforcement layer. Absent, it
means everything is off. This skill creates it and tells you whether it is actually doing
anything — the two states look identical from the outside otherwise, because every loader in
atelier fails open (`except Exception: return <inert default>`) by design.

## Procedure

Run from the target project's root:

```bash
S="${CLAUDE_PLUGIN_ROOT}/skills/activation/scripts/activation.py"
python3 "$S" create [--project-dir DIR] [--force]
python3 "$S" check  [--project-dir DIR]
```

Outside the harness `$CLAUDE_PLUGIN_ROOT` is unset — invoke the script by its own path
instead; it finds the hooks relative to itself, and fails loudly naming what it tried if they
are not there. `--project-dir` defaults to `$CLAUDE_PROJECT_DIR`, else the cwd.

`create` installs the copyable starting point at
[examples/atelier.local.md](examples/atelier.local.md) into `<project>/.claude/atelier.local.md`
(refuses to overwrite an existing file unless `--force`). `check` reads the installed file
*through the hooks' own loader functions* rather than parsing it itself, then reports per key
what each hook actually resolved. That is why its answer cannot drift from real behavior.

The state it exists to expose is **inert**: a key that is present and looks configured, but is set
to something no hook recognizes, so it is off. Nothing errors, nothing warns, the hook just never
fires — which is why an absent file and a typo'd one are indistinguishable without this. `check`
exits nonzero when it finds an inert key, so a broken file is a failing command, not a hunch.

Read the labels off `check` itself rather than from this page. The taxonomy is a fact about the
script, and a second copy here is exactly the drift this skill exists to catch.

## The keys

| key | read by | accepted values | enforced per hook call? |
|---|---|---|---|
| `enforce` | `worker-context`, `config-custody` | `advisory` \| `strict` (anything else is off) | yes |
| `protected` | `config-custody` | fnmatch globs, block or inline list | yes |
| `isolate` | `worktree-isolation` | `writers` \| an explicit agent-type list (empty list = off) | yes |
| `handoff` | `session-handoff-surfacer`, `handoff-freshness-guard` | a project-relative path to a file that **already exists** (file mode), or a mapping naming an external tracker plus a freshness stamp (external mode) - see below | yes |
| `effort` | nothing — prose only | `standard` \| `deep` | **no** |

**`effort` is not machine-enforced.** No hook reads it. It only takes effect if the agent
actually opens `.claude/atelier.local.md` and reads the frontmatter itself — the `delegation`
skill documents this at `primitives-core/skills/delegation/SKILL.md:215-217`. Setting it is a
request an agent might honor, not a control a hook applies. Do not describe it as equivalent to
the hook-enforced keys.

**`handoff` has two modes, and each has a failure shape only one side of which is safe.** File
mode (a bare scalar, or `{mode: file, path: ...}`) behaves as before: a path that resolves
*outside* the project root is rejected and the standard `_meta/HANDOFF.md` → `HANDOFF.md` →
`.claude/HANDOFF.md` search runs unchanged, but a path *inside* the root naming a file that
does not exist is authoritative anyway - both hooks report no handoff and do **not** fall back
to the search, so setting it early silently turns handoff surfacing off. That is why the
shipped example ships this key commented out.

External mode (`{mode: external, stamp: ..., location: ...}`) is for a handoff that lives on a
tracker or board, not a file in this repo: `stamp` is a freshness signal the `handoff` skill
touches, not the handoff itself. A `stamp` that is missing, blank, or resolves outside the
project root leaves the whole key inert - same fail-open posture as an out-of-root file
override - and so does a `mode` value that is neither `file` nor `external`. Once armed, an
in-root stamp that has never been touched reads as "no handoff" to the freshness guard (the
same missing-vs-stale logic file mode uses), but the surfacer still surfaces the pointer to
the board on a cold session regardless - silence at cold start is exactly what external mode
exists to fix, and the stamp is only a freshness gauge, never the thing being surfaced.
`check` reports either mode as armed with a warning when its file/stamp does not exist yet,
because it is live - just probably not as intended.

## Effect and location

Edits take effect on the **next tool call** — every hook re-reads the file per call, so there is
no restart or session reload needed. Gitignore it as a local file:

```gitignore
.claude/*.local.md
```

## Full semantics

This skill covers create/check mechanics only. For the deep behavioral tables — what each
`enforce` level actually blocks, which agent roles are never isolated even when listed, and the
`handoff` fallback matrix — read
[`primitives-core/skills/delegation/references/activation.md`](../delegation/references/activation.md),
which is authoritative.
