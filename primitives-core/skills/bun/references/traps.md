# Bun Traps

Behaviors that cost time on this machine. Each entry says whether it was **measured here**
or **read in the docs**, because the two deserve different levels of trust.

All measurements: bun 1.4.0 (34cbb9a40), macOS arm64, 2026-08-26.

---

## 1. `minimumReleaseAgeExcludes` takes exact names and silently ignores globs

**Measured.** This is the inverse of npm and the most dangerous item here, because every
wrong form fails *silently* — no error, no warning, just an older version installed.

Setup: a 7-day gate (`minimumReleaseAge = 604800`), then
`bun add @anthropic-ai/claude-code@latest`. True latest at the time was **2.1.246**,
published under 24h earlier, so the gate had to block it.

| `minimumReleaseAgeExcludes` | Resolved | Packages installed |
|---|---|---|
| `[]` | 2.1.235 (backwards) | `claude-code`, `claude-code-darwin-arm64` |
| `["@anthropic-ai/*"]` | 2.1.235 (backwards) | `claude-code`, `claude-code-darwin-arm64` |
| `["@anthropic-ai/claude-code"]` | 2.1.246 | `claude-code` **only — platform package dropped** |
| both names enumerated | 2.1.246 | both, at 2.1.246 |

Two separate failure modes:

- **The glob matches nothing.** `@anthropic-ai/*` behaves exactly like no exclusion at all.
  npm's `min-release-age-exclude[]` *requires* the scope glob; bun rejects it. Carrying the
  npm habit across gives you a silently stale install.
- **Naming only the parent drops the platform sibling.** `@anthropic-ai/claude-code-<os>-<arch>`
  carries the actual binary. Excluding just the parent installs 1 package instead of 2.

**Control, same run:** `vite` resolved to 8.2.1 while npm's latest was 8.2.2 — so the gate
was still active for everything not listed. The exclusions are narrow, not a global bypass.

**Consequence:** every new exemption needs *every* name, including any `-<os>-<arch>` sibling.
There is no wildcard.

---

## 2. The global `~/.bunfig.toml` is read for `[install]` only

**Documented** (bunfig reference, `bun run` section): *"For `bun run`, Bun only loads the
local project's `bunfig.toml` automatically (it doesn't check for a global `.bunfig.toml`)."*

So a `[run]` section in `~/.bunfig.toml` is dead config. Notably `run.bun = true` — the
"alias `node` to `bun` everywhere" switch — cannot be set globally this way. Not
independently re-tested here; the global file is kept `[install]`-only on that basis.

---

## 3. A floating `"latest"` in `package.json` is a landmine bun will find

**Measured**, during the `functionform-obsidian` migration.

`package.json` declared `"@assistant-ui/react": "latest"`. npm's `package-lock.json` had it
pinned at **0.12.27** and kept serving that. `bun install` re-resolved `latest` to
**0.15.16**, which had removed the legacy context hooks (`useThread`, `useThreadRuntime`,
`useMessage`) the code imported. Result: 8 TypeScript errors and 4 esbuild errors.

This is **not a bun defect.** `"latest"` pins nothing; any fresh `npm install` without the
lockfile would have done the same. Bun surfaced drift npm was hiding. Seven deps in that one
repo were declared `"latest"`.

Fix: pin real ranges. Do not "fix" it by going back to npm.

---

## 4. Dependency postinstall scripts are blocked by default

**Observed.** `bun install` reported `Blocked 1 postinstall` — `@parcel/watcher` attempting
`node scripts/build-from-source.js`.

This is bun's out-of-the-box equivalent of npm's `ignore-scripts=true`, and it is the
desired posture. A block is usually *correct*. Inspect with `bun pm untrusted`, and only
then `bun pm trust <pkg>`. In that repo the block was harmless: typecheck, 167 tests, and
the build all passed with it still in place.

---

## 5. mise shims can shadow `~/.bun/bin`

**Measured.** After moving CLIs from npm-global to bun, a login shell still resolved
`vercel` to `~/.local/share/mise/shims/vercel`, because mise shims sit earlier in `PATH`.

The shims still *worked* (they fell through to the bun copy and reported the bun version),
so this shadowing is confusing rather than broken. `mise reshim` did **not** remove the
stale shims — they had to be deleted by hand:

```bash
rm -f ~/.local/share/mise/shims/{vercel,vc,claude-agent-acp,firebase}
```

Check resolution in a real login shell (`zsh -lic 'command -v <tool>'`), not just the
current one — see the shell-snapshot caveat in `terminal-environment.md`.

---

## 6. `bun completions` prints, it does not install

**Measured.** `bun completions` takes no arguments and writes the completion script to
stdout when stdout is a pipe. It did not modify `~/.zshrc` or `~/.zshenv` (checksummed
before and after), which matters here because those are stow symlinks into the dotfiles repo.

Completions are already handled: the brew formula ships
`/opt/homebrew/share/zsh/site-functions/_bun`, and `_comps[bun]` is set in a real zsh. Since
the Brewfile carries `oven-sh/bun/bun`, the other Mac gets them too. Nothing to add.

---

## 7. `--bun` disables automatic `.env` loading

**Documented** (Prisma guide). Bun normally loads `.env` with no `dotenv` package. But when
`--bun` forces a node-shebang CLI onto the bun runtime, that automatic loading does not
happen, so `.env` must be passed explicitly:

```bash
bun run --bun --env-file=.env prisma migrate dev
```

---

## 8. Bun reads `~/.npmrc`

**Documented** (*"`bun install` reads npm registry configuration from npm's `.npmrc`"*).
This is why registry and auth config — e.g. `@scope:registry=https://npm.pkg.github.com` —
is deliberately **not** duplicated into `bunfig.toml`. One source of truth. Not
independently verified against the private registry here.
