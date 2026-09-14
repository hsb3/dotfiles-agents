---
name: bun
description: Work with the Bun JS/TS toolchain — running scripts, installing packages, testing, bundling, bunfig.toml, bun.lock, or migrating a repo from npm/pnpm/yarn to bun. Use when a task touches bun commands, when choosing between bun built-ins and an npm dependency, when a bun install resolves a stale version or drops a platform package, when debugging PATH/mise/node-version interactions with bun, or when converting package.json scripts and lockfiles to bun.
---

# Bun

Bun is the default runtime, package manager, test runner, and bundler for JS/TS on this
machine. Installed via brew (`oven-sh/bun/bun`), not mise — mise owns `node`. Use bun over
npm/npx/pnpm/yarn/node/ts-node habits unless an exception below applies.

## Command mapping

| Instead of | Use |
|---|---|
| `npm install` / `npm ci` | `bun install` / `bun install --frozen-lockfile` |
| `npm run <script>` / `npx <pkg>` | `bun run <script>` / `bunx <pkg>` |
| `node x.js` / `ts-node x.ts` | `bun x.js` / `bun x.ts` (TS runs directly) |
| `nodemon` | `bun --watch` (restart) or `bun --hot` (in-place reload) |
| `jest` / `vitest` (new projects) | `bun test` |
| `esbuild` / `webpack` / `pkg` | `bun build` / `bun build --compile` |

Commit `bun.lock` (text, reviewable). `bun install` auto-migrates `package-lock.json`.

## Prefer the built-in over a dependency

`.env` loads automatically (no `dotenv`); `Bun.$` shell (no `execa`/`zx`); `bun:sqlite`
(no `better-sqlite3`); `Bun.serve()` with routes + WebSockets; `Bun.file()`/`Bun.write()`;
`Bun.secrets` (OS keychain — the right home for tokens); `Bun.password`, `Bun.Glob`,
`Bun.hash`, `Bun.cron`, `Bun.markdown`. Signatures and examples:
[references/cheatsheet.md](references/cheatsheet.md).

## Traps — measured, not folklore

Full evidence per trap in [references/traps.md](references/traps.md). Headlines:

- **`minimumReleaseAgeExcludes` takes EXACT names; globs silently match nothing** (inverse
  of npm). Enumerate every name including `-<os>-<arch>` platform siblings, or the binary
  is dropped or a stale version installs with no error.
- **Global `~/.bunfig.toml` is `[install]`-only.** A `[run]` section there is dead config.
- **A `"latest"` spec is a landmine**: bun re-resolves what npm's stale lockfile froze.
  Pin real ranges; don't blame bun for surfaced drift.
- **Postinstalls are blocked by default** — usually correct. `bun pm untrusted`, then
  `bun pm trust <pkg>` only if needed.
- **`--bun` disables automatic `.env` loading** — pass `--env-file=.env` explicitly.
- **`NODE_OPTIONS` is ignored** (bun uses `BUN_OPTIONS`; no hard heap cap, only `--smol`).
- **`~/.bun/bin` is last in PATH** — after `bun install -g`, verify with
  `zsh -lic 'command -v <tool>'`. mise/brew shadowing detail:
  [references/mise-interop.md](references/mise-interop.md).
- Bun reads `~/.npmrc`, so registry/auth config is not duplicated into `bunfig.toml`.

## Migrating a repo

Green baseline first (install + typecheck + test + build under the old tool), then
`bun install`, re-run gates before touching scripts, swap `node `→`bun ` in scripts,
delete the npm lockfile, verify from a clean slate with `--frozen-lockfile`. Worked
example with numbers: [references/migration.md](references/migration.md). Keep an
existing vitest suite; runner migration is a separate decision.

## When NOT to use bun

Globals located via `npm root -g` (`playwright`, `openwiki`) stay npm. Repos committed to
pnpm/yarn workspaces migrate deliberately, not incidentally. Native-addon-heavy packages
needing real `node-gyp` stay on node. Polyglot task running stays in Makefiles.

Upstream full docs (bun 1.4) are not bundled: fetch or grep them from the canonical
source, <https://bun.sh/llms-full.txt> (~2MB, ~56k lines — grep it, never read it whole).
