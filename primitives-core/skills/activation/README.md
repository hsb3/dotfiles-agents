# activation

Creates and verifies the per-project `.claude/atelier.local.md` file that arms atelier's
enforcement hooks, then reports per key what each hook actually resolved — including a key
that is present, looks configured, and is silently doing nothing.

## When it triggers

Use it when someone asks to turn on, configure, or check atelier enforcement (custody,
worker context, worktree isolation, protected branches, handoff routing) in a project, or
when a hook that should be firing appears silent. Every atelier loader fails open by design, so an absent
activation file and a typo'd one are indistinguishable from the outside. `check` reads the
installed file through the hooks' own loader functions rather than parsing it itself, and
exits nonzero on an inert key — a broken file becomes a failing command, not a hunch.

## One key is Claude Code only

`protected-branches:` is read by `worker-git-scope-guard`, which exists only here. The opencode
port's activation parser does not read it and that bundle ships no git guard at all, so the key
and its explanation sit in `<!-- harness:claude-code -->` blocks rather than in the shared key
table — a GFM table cannot carry a harness marker, so that row lives below the table. Do not
confuse it with `protected:`, the file-glob key, which both harnesses read. See
`docs/atelier-parity.md`.

## Install

```
claude plugin install atelier@dotfiles-agents
```

Ships in the `atelier` bundle — it arms the hooks the rest of the bundle
depends on.
