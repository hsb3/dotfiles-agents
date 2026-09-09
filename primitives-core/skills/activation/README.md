# activation

Creates and verifies the harness-appropriate per-project activation file that arms atelier's
enforcement hooks, then reports per key what each hook actually resolved — including a key
that is present, looks configured, and is silently doing nothing.

## When it triggers

Use it when someone asks to turn on, configure, or check atelier enforcement (custody,
worker context, worktree isolation, protected branches, handoff routing, context
watermarks) in a project, or when a hook that should be firing appears silent. Every atelier loader fails open by design, so an absent
activation file and a typo'd one are indistinguishable from the outside. `check` reads the
installed file through the hooks' own loader functions rather than parsing it itself, and
exits nonzero on an inert key — a broken file becomes a failing command, not a hunch. One
key, `watermark`, overrides rather than arms: each sub-key it omits stays computed, so the
report calls it inert only when nothing under it is readable at all.

Reporting through the loaders is what keeps `check` honest, and the loaders now sit on one
frontmatter parser (`hooks/_lib/atelier_local.py`) instead of seven private copies — so two
hooks can no longer read the same key differently with no error on either side, which is the
failure `check` exists to expose. Path selection is shared too. Each hook still owns which BYTES it reads: `config-custody`
governs a linked worktree by the copy committed on its branch, and the others fall back to the
main checkout's copy, so `check` run in a worktree can legitimately differ from `check` run in
the main tree.

## Two keys are Claude Code only

`protected-branches:` is read by `worker-git-scope-guard`, which exists only here. The opencode
port's activation parser does not read it and that bundle ships no git guard at all, so the key
and its explanation sit in `<!-- harness:claude-code -->` blocks rather than in the shared key
table — a GFM table cannot carry a harness marker, so that row lives below the table. Do not
confuse it with `protected:`, the file-glob key, which both harnesses read.

`watermark:` is harness-local for a different reason: both harnesses scale a context watermark,
but they spell the override differently — a `watermark:` mapping of `soft`/`hard`/`complexity`
here, a top-level categorical `complexity:` key there. Same job, two schemas, so neither spelling
belongs in the shared table. See `docs/atelier-parity.md`.

## Install

```
claude plugin install atelier@dotfiles-agents
```

Ships in the `atelier` bundle — it arms the hooks the rest of the bundle
depends on.

## Codex

Codex selects `ATELIER_ACTIVATION_FILE` first, then `.codex/atelier.local.md`, then an
existing `.claude/atelier.local.md`. Claude Code selects the explicit override or the
`.claude` file. A relative explicit override is anchored at the target project root. When
both files exist, Codex uses only `.codex`; policies are never merged or migrated. A selected
malformed, unreadable or missing explicit file never falls back to another policy; `check`
reports it. A linked worktree uses its own selected file, or inherits the main checkout's
selection when neither local candidate exists. Config custody retains its additional rule:
worker edits are governed by the selected policy committed at that worktree's HEAD, so
uncommitted edits do not change that committed policy. Existing handoff paths and stamps are unchanged.


`codex-setup` renders native roles and project writable roots without touching global config or hook trust. `check --harness codex` verifies generated role/config currency and reports trust as unverified until checked in native `/hooks`. See the skill for setup and restart steps.

Setup rejects symlink or non-regular config/exclude destinations before writing any project files and clears inherited Git routing variables during discovery. Existing user permission tables are preserved.

Native manager workflows need `agents.max_depth >= 2`. Setup adds depth two when the agents table is absent, retains higher configured depths, and reports disabled agents or a known concurrency below two before any mutation. User-owned tables are never rewritten.

Codex setup guidance ships alongside the Claude activation workflow; the separate OpenCode port retains its own setup procedure.
