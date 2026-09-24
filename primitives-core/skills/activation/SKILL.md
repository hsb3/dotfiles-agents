---
name: activation
description: Create and verify the harness-appropriate per-project activation file that arms atelier's hooks. Use when someone asks to turn on, configure, or check atelier enforcement (custody, worker context, worktree isolation, handoff routing) in a project, or when a hook that should be firing appears silent.
---

# Activation

Atelier keeps `atelier.local.md` in the sole configured agent's native directory
(`.claude`, `.codex` or `.opencode`), or `.agents` when multiple agents are configured.
Native directories and root `opencode.json`/`opencode.jsonc` files identify agents;
installed binaries, instruction files and `.agents` itself do not.
Symlinks are not configuration markers. With no configured
agent, creation defaults to the current harness.

`ATELIER_ACTIVATION_FILE` is authoritative, relative to the project root when relative.
Otherwise readers select an existing `.agents` policy first, the canonical location next,
then legacy `.claude`, `.codex`, `.opencode` locations in that fixed order. A selected
malformed file never falls back. A worktree's local policy wins before main-checkout
inheritance. Runtime readers never migrate files. `create` and setup move an existing
policy without changing its bytes or permissions, coalesce byte-identical duplicates,
and reject divergent policies before any mutation, even with `--force`. Repeating
`create` leaves an existing canonical policy unchanged. Existing handoff paths and
stamps remain unchanged.

It is the one file that arms atelier's enforcement layer. Absent, it means everything is off.
This skill creates it and tells you whether it is actually doing anything — the two states look
identical from the outside otherwise, because every loader in atelier fails open
(`except Exception: return <inert default>`) by design.

## Procedure

Run from the target project's root:

<!-- harness:claude-code -->
In Claude Code (for Codex, use the setup commands below):

```bash
S="${CLAUDE_PLUGIN_ROOT}/skills/activation/scripts/activation.py"
python3 "$S" create [--project-dir DIR] [--force]
python3 "$S" check  [--project-dir DIR]
```

Outside the harness `$CLAUDE_PLUGIN_ROOT` is unset — invoke the script by its own path
instead; it finds the hooks relative to itself, and fails loudly naming what it tried if they
are not there. `--project-dir` defaults to the cwd in Codex; Claude Code uses
`$CLAUDE_PROJECT_DIR` when set, else the cwd.
<!-- /harness -->

`create` installs the copyable starting point at
[examples/atelier.local.md](examples/atelier.local.md), and leaves an existing
canonical file unchanged unless `--force`.

<!-- harness:claude-code -->
It safely migrates existing policies before checking their contents. Config custody
selects from the committed HEAD tree, including configured-agent markers, so uncommitted
policy or directory changes cannot weaken worker protection.

`check` reads the installed file *through the hooks' own loader functions* rather than parsing
it itself, then reports per key what each hook actually resolved. That is why its answer cannot
drift from real behavior.
<!-- /harness -->

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

<!-- harness:claude-code -->
Two more keys are read only on this harness, and a GFM table cannot carry a harness marker, so
they sit here instead of in the table above:

| key | read by | accepted values | enforced per hook call? |
|---|---|---|---|
| `protected-branches` | `worker-git-scope-guard` | branch names, block or inline list (empty list = off) | yes |
| `watermark` | `context-watermark` | a mapping of `notice` / `soft` / `hard` (absolute token counts) and `complexity` (a multiplier on all three), plus optional `worker:` / `session:` sub-mappings of the same keys that override the flat ones for that layer; every sub-key optional | yes |
| `checkout-root` | `codex_workers.py`, `activation.py` | a path, relative to the main checkout, `~`-relative, or absolute (absent/blank = default; invalid = dispatch refused) | yes |

**No activation file at all** means every key is off. `session-handoff-surfacer` says so at each
cold main-session start inside a git worktree (`atelier is enabled here but not activated: ...`). A project that runs
atelier unarmed on purpose silences that line with the environment variable
`ATELIER_ACTIVATION_NUDGE=off`: with no file there is nowhere to put a key.
<!-- /harness -->

**`effort` is not machine-enforced.** No hook reads it. It only takes effect if the agent
actually opens the activation file and reads the frontmatter itself — the `delegation` skill
documents this. Setting it is a request an agent might honor, not a control a hook applies. Do
not describe it as equivalent to the hook-enforced keys.

<!-- harness:claude-code -->
**`protected-branches` is a different key from `protected`, and has no default.** One names branch names, the other names file paths, and neither hook reads the other's key - a file glob must never be taken for a branch name. Absent, an explicit empty list (`[]`, deliberately off), or unparseable leaves the protected-branch half of its hook off; nothing is protected until the project names it, because a built-in `main`/`master` guard is wrong in every project whose default branch is a publish-only surface. The same hook's shared-tree stash ban needs no key and is live wherever the plugin is installed, which is why `check` reports an absent key as not configured rather than as the hook being off.
<!-- /harness -->

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

<!-- harness:claude-code -->
**`checkout-root` places automatic Codex worker checkouts, resolved by `codex_workers.py` and
added as a writable root by `activation.py`'s Codex setup; absent or blank keeps the default
`<git-common-dir>/atelier-codex/checkouts`. Claude Code subagent worktrees: not yet.**

**`watermark` is the one key whose sub-keys are independently optional.** Absent, blank, or
unusable leaves that one value computed from the lead model's context window rather than turning
anything off — so `check` calls a key with nothing readable under it inert, and a key naming only
one threshold armed. `worker:` and `session:` sub-mappings override the flat keys per layer. It
is also the one key the environment outranks: `CONTEXT_WATERMARK_NOTICE`, `CONTEXT_WATERMARK_SOFT`,
and `CONTEXT_WATERMARK_HARD` beat the file, which beats the computed default. `complexity` is 1.0
unless this key sets it. The bundle's wiring sets neither variable, on
purpose: a shell-expanded default would leave it always set and the top tier would win forever.
<!-- /harness -->

## Effect and location

Edits take effect on the **next tool call** — every hook re-reads the file per call, so there is
no restart or session reload needed. Gitignore it as a local file:

<!-- harness:claude-code -->
```gitignore
.claude/*.local.md
.codex/*.local.md
```
<!-- /harness -->

## Full semantics

This skill covers create/check mechanics only. For the deep behavioral tables — what each
`enforce` level actually blocks, which agent roles are never isolated even when listed, and the
`handoff` fallback matrix — read
[`delegation/references/activation.md`](../delegation/references/activation.md), which is
authoritative.


<!-- harness:claude-code -->
## Codex setup

Use the installed skill directory to locate `scripts/activation.py`; Codex does not set
`CLAUDE_PLUGIN_ROOT`. Setup reconciles policy placement after creating `.codex`, which can make a project
multi-agent. Native role and config files stay under `.codex`. Invoke the activation skill directly;
`/atelier:activate` is a Claude Code command, not a registered Codex slash command.

```bash
python3 /path/to/activation/scripts/activation.py create --harness codex
python3 /path/to/activation/scripts/activation.py codex-setup
python3 /path/to/activation/scripts/activation.py check --harness codex
```

Skip `create` when the file already exists. `codex-setup` uses current managed global roles
when present; otherwise it generates project-local native role TOMLs from the installed canonical
agents and adds the derived writable roots needed
by isolated checkouts, Git indexes, objects, refs, and logs to `.codex/config.toml`.
It sets `agents.max_depth = 2` when the project has no agents table: Codex V1 defaults
to one level, which leaves an atelier manager unable to dispatch an execution worker.
An existing agents table must enable agents, allow depth at least two, and must not set
concurrency below two. Setup reports the exact needed entries before any write instead
of replacing a user-owned table; higher existing depth is retained.
It refuses to replace a conflicting user-owned permission table or role file. Stale global roles
are reported without mutation and refresh only through explicit `codex-setup --refresh-global`. It adds
local Git excludes for these generated files; nothing generated belongs in a commit.
The writable roots support collision isolation between cooperating workers, not separate
OS security boundaries for each worker. A configured permission profile can override the
legacy sandbox settings: verify the actual session permissions before dispatch.

Restart Codex after setup. Open `/hooks`, review and approve the installed atelier hooks,
and verify that they are enabled and trusted for this project. `check` explicitly reports
hook trust as unverified: parsing an activation file cannot establish runtime enforcement.
Missing or outdated role files and missing writable roots are failing setup checks.
Context watermarks use the rollout’s actual effective context limit and latest usage.
<!-- /harness -->
