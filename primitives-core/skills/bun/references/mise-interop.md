# Bun + mise

How the two coexist on this machine. All measured 2026-08-26 against bun 1.4.0 and mise,
with `node = "26"` in `~/.config/mise/config.toml`.

**Division of labour:** mise owns `node`. brew owns `bun` (`oven-sh/bun/bun`, self-updating
via `bun upgrade`). Bun is deliberately *not* in mise `[tools]`.

---

## Footguns

### 1. `NODE_OPTIONS` does not apply to bun — including the heap guard

`zsh/.zsh/path.zsh` exports `NODE_OPTIONS="--max-old-space-size=4096"`, with the stated
purpose of stopping runaway AI agent sessions from exhausting RAM and crashing macOS.

**Bun ignores `NODE_OPTIONS` entirely.** Proof — a flag that does not exist:

```
$ NODE_OPTIONS="--this-flag-does-not-exist" node -e 'console.log("ok")'
node: --this-flag-does-not-exist is not allowed in NODE_OPTIONS     # node rejects it
$ NODE_OPTIONS="--this-flag-does-not-exist" bun  -e 'console.log("ok")'
ok                                                                   # bun never read it
```

`NODE_OPTIONS` appears nowhere in bun's documentation. Bun's equivalent is `BUN_OPTIONS`.

**There is no direct port of the guard.** Bun offers `--smol` (reduce memory usage at some
cost to performance), not a hard heap ceiling like `--max-old-space-size`. So as tooling
moves from node to bun, that memory guard silently covers less. Options, none free:

- Accept it, and rely on `--smol` (via `BUN_OPTIONS` or `bunfig.toml` `smol = true`) where
  a process is known to be memory-hungry.
- Cap at the OS level (`ulimit -v`) if a hard ceiling actually matters.

Note `BUN_OPTIONS` is lenient too — a bogus flag there did **not** error, so do not rely on
it to fail loudly when misconfigured.

### 2. `~/.bun/bin` is LAST in `PATH`

Measured order in a login shell:

| Position | Entry |
|---|---|
| 13 | `/opt/homebrew/bin` |
| 30 | `~/.local/share/mise/shims` |
| 45 | `~/.bun/bin` |

Any globally-installed bun CLI whose name collides with a brew formula or a mise shim
**loses**. This is not hypothetical: an orphaned npm-global `firebase` in
`/opt/homebrew/bin` shadowed bun's newer `firebase` until it was removed.

After `bun install -g <tool>`, verify resolution in a *real login shell*:

```bash
zsh -lic 'command -v <tool>'
```

### 3. mise's two mechanisms have different precedence

`mise activate` (dynamic per-directory `PATH`) **beats** homebrew. mise *shims* sit at
position 30 and **lose** to homebrew. So a project-pinned bun works interactively, while
the shim path may not. Trust `mise which` / `mise exec`, not the shim's existence.

### 4. Nested non-login shells silently drop the pinned version

With `bun = "1.3.14"` pinned in a project's `mise.toml`:

```
$ mise exec -- bun --version                    → 1.3.14   correct
$ mise exec -- bash -c 'bun --version'          → 1.4.0    brew's, WRONG
```

The nested shell re-sources a profile that re-prepends `/opt/homebrew/bin`. Any script that
shells out can silently run a different bun than the pin says. Invoke bun directly rather
than through a wrapper shell.

### 5. Every bun shares one global package store

`bun pm bin -g` returns `~/.bun/bin` for **both** the brew bun and a mise-managed bun. Two
bun versions therefore read and write the same `~/.bun/install/global`. Fine while versions
are close; a lockfile or cache format change across a major would make it a problem.

### 6. This machine currently has two bun installs

An **undeclared** mise-managed bun 1.4.0 (61MB, installed 2026-08-22) sits in
`~/.local/share/mise/installs/bun` with no version set in any config. It is inert today
because brew's copy wins in `PATH`, but any project adding `bun` to its `mise.toml` would
silently activate it.

Pick one owner. To drop the mise copy and leave brew authoritative:

```bash
mise uninstall bun@1.4.0
```

---

## What works correctly

**`bun run` honors the project's mise node.** In a project pinned to `node = "24"`, with the
machine default at 26.5.0:

```
$ bun run whichnode        # script is: node --version
v24.18.0
```

So hybrid repos — bun as package manager and script runner, node as the actual runtime for
some scripts — compose properly. This is what makes "bun by default, node still present"
viable rather than a constant fight.

**Bun tolerates `NODE_OPTIONS` without erroring.** It ignores the variable rather than
choking on it, so the global export breaks nothing. It just does not do what it says.

---

## Stale shims: what is fixable and what is not

Cleaned up 2026-08-26, 16 broken shims → 2. The three causes need different fixes:

- **Installed but never declared** (`golangci-lint`, `prek`, `process-compose`, `npm:oxfmt`,
  `npm:vite-plus`). mise had them installed with no global version set, so every shim they
  owned failed with `No version is set for shim`. Fixed with `mise use -g <tool>@<version>`.
  This is the "enabled means intended" case — installed, so wanted, but silently inert.
- **Bins from non-active runtime versions.** Seven came from `python/3.13.13`; removing the
  stale versions removed the shims. Note `mise prune` pruned only *configuration links* here
  and did **not** remove tool versions — `mise uninstall <tool>@<version>` was required.
- **Structurally unfixable while an old runtime is kept.** `codex-acp` (in `node/24.18.0`)
  and `corepack` (in `node/22.23.1`, `24.16.0`, `24.18.0`, and **not shipped by Node 26**)
  are bins that exist only in non-active versions. mise creates shims for bins across *all*
  installed versions but can only resolve them for the active one, so these stay broken until
  node 24.x goes away. Expected, not a defect.

**`mise reshim` only ever creates shims — it never removes stale ones.** Deleting by hand does
not stick either, because the next `mise install` regenerates them from whatever versions are
still installed. Removing the owning version is the only durable fix.

**Quirk worth knowing:** mise's `github:` backend treats every file in an extracted release
archive root as a bin. `process-compose` ships a `readme.md` there, so mise created a
`readme.md` *shim* that tried to execute the README as a shell script. Harmless, but delete it.

## Best practices

1. **One manager per tool.** mise for `node`, brew for `bun`. Do not add `bun` to mise
   `[tools]` globally — it duplicates a self-updating brew formula and invites version skew
   through the shared global store.
2. **Pin bun in `mise.toml` only when a project genuinely needs a specific version**, and
   verify it took effect with `mise which bun` in a real login shell.
3. **Verify global CLI resolution after `bun install -g`**, given `~/.bun/bin` is last.
4. **Do not assume node's env vars carry over.** `NODE_OPTIONS`, and node-specific flags
   generally, are node's. Bun has its own (`BUN_OPTIONS`, `bunfig.toml`).
5. **Keep `bun.lock` committed** and let mise handle only the runtime versions, exactly as
   `rules/mise.md` already says for node and python.
