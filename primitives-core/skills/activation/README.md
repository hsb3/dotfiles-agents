# activation

External handoffs may opt into `scope: session`; the check validates the contained stamp and
reports the native-hook/launch-identity requirement. Leave scope absent for legacy project
handoffs. See [handoff](../handoff/SKILL.md#opt-in-concurrent-sessions) before enabling it.
Codex session scope is reported as configured, not proof that native hooks ran. Unsupported
Claude session scope is inert in this report; ordinary tools work and manual compaction refuses.

Creates and verifies the harness-appropriate per-project activation file that arms atelier's
enforcement hooks, then reports per key what each hook actually resolved — including a key
that is present, looks configured, and is silently doing nothing.

## When it triggers

Use it when someone asks to turn on, configure, or check atelier enforcement (custody,
worker context, worktree isolation, protected branches, handoff routing, context
watermarks) in a project, or when a hook that should be firing appears silent. Every atelier loader fails open by design. On Claude Code an
absent activation file is announced at each cold session start by `session-handoff-surfacer`
(`ATELIER_ACTIVATION_NUDGE=off` silences it); a typo'd one is indistinguishable from the outside. `check` reads the
installed file through the hooks' own loader functions rather than parsing it itself, and
exits nonzero on an inert key — a broken file becomes a failing command, not a hunch. One
key, `watermark`, overrides rather than arms: each sub-key it omits stays computed, so the
report calls it inert only when nothing under it is readable at all. An explicit empty
list (`isolate: []`, `protected-branches: []`) is the documented off value, so `check`
reports it `off (explicit)` and passes; the hook wrappers read it and a malformed value
alike as off, so that one verdict asks the shared parser underneath them.

Reporting through the loaders is what keeps `check` honest, and the loaders now sit on one
frontmatter parser (`hooks/_lib/atelier_local.py`) instead of seven private copies — so two
hooks can no longer read the same key differently with no error on either side, which is the
failure `check` exists to expose. Path selection is shared too. Each hook still owns which BYTES it reads: `config-custody`
governs a linked worktree by the copy committed on its branch, and the others fall back to the
main checkout's copy, so `check` run in a worktree can legitimately differ from `check` run in
the main tree.

## Two keys are Claude Code only

`protected-branches:` is read by `worker-git-scope-guard`, which exists only here; that hook's
stash half (no stash outside a worker's own worktree, no pop/drop/clear/branch anywhere) needs no
key. The opencode
port's activation parser does not read it and that bundle ships no git guard at all, so the key
and its explanation sit in `<!-- harness:claude-code -->` blocks rather than in the shared key
table — a GFM table cannot carry a harness marker, so that row lives below the table. Do not
confuse it with `protected:`, the file-glob key, which both harnesses read.

`watermark:` is harness-local for a different reason: both harnesses scale a context watermark,
but they spell the override differently — a `watermark:` mapping of `notice`/`soft`/`hard`/
`complexity`, with optional `worker:`/`session:` sub-mappings, here, a top-level categorical
`complexity:` key there. Same job, two schemas, so neither spelling
belongs in the shared table. See `docs/atelier-parity.md`.

## Install

```
claude plugin install atelier@dotfiles-agents
```

Ships in the `atelier` bundle — it arms the hooks the rest of the bundle
depends on.

## Codex

`ATELIER_ACTIVATION_FILE` is authoritative. Otherwise a shared `.agents/atelier.local.md`
wins when present; one configured agent uses its native directory and multiple agents use
`.agents`. Existing native policies remain readable until safe setup migrates identical bytes.
Malformed selected policies never fall back. Custody reads the selected policy from HEAD.


`codex-setup` resolves each role from its project profile first, then a current managed global profile, and only bootstraps missing roles locally. It adds project writable roots without touching hook trust. `check --harness codex` is read-only; stale global profiles require explicit `codex-setup --refresh-global`. It reports trust as unverified until checked in native `/hooks`. See the skill for setup and restart steps.

Watermark diagnostics include an optional `notice` threshold when the hook loader returns it.

Setup rejects symlink or non-regular config/exclude destinations before writing any project files and clears inherited Git routing variables during discovery. Existing user permission tables are preserved.

Native manager workflows need `agents.max_depth >= 2`. Setup adds depth two when the agents table is absent, retains higher configured depths, and reports disabled agents or a known concurrency below two before any mutation. User-owned tables are never rewritten.

Codex setup guidance ships alongside the Claude activation workflow; the separate OpenCode port retains its own setup procedure.

The checker labels OpenCode `models`, `complexity`, and `worktreeBaseRef` as other-harness
settings without validating their values; unknown keys still fail. Migration preserves
source bytes and permission bits, and repeated creation leaves canonical policy unchanged.
