# Migration: npm workspaces → bun

Worked example, 2026-08-26: an npm workspaces monorepo (Obsidian plugin + preact
webapp, esbuild bundler, vitest suite).

## Procedure

The order matters. Establishing a green baseline **first** is what makes a later failure
attributable instead of guesswork.

1. **Confirm a clean, committed tree.** Skipped the first candidate for exactly
   this reason: it had zero commits, so there was no rollback path.
2. **Baseline under the old toolchain** — install, then run every gate (typecheck, test,
   build) and record the numbers.
3. `rm -rf node_modules` (including per-workspace `node_modules`), then `bun install`.
   Bun auto-migrates `package-lock.json` → `bun.lock`, reporting `migrated lockfile from
   package-lock.json`.
4. **Re-run the gates before touching any script.** This isolates *install* differences
   from *runtime* differences.
5. Swap `node ` → `bun ` in `package.json` scripts.
6. Re-run the gates. Delete `package-lock.json`, commit `bun.lock`.
7. **Verify from a clean slate**: `rm -rf node_modules && bun install --frozen-lockfile`,
   then all gates again.

## Results

| | npm (baseline) | bun (after) |
|---|---|---|
| Install, cold | 7.8s / 411 packages | 8.4s / 397 packages |
| Install, from lockfile | — | **0.46s** / 401 packages |
| Typecheck | 0 errors | 0 errors |
| Tests | 167 passed, 2 skipped (20 files) | **identical** |
| Build | succeeds | succeeds |

Behavior parity was exact. The headline number is repeat installs: **0.46s versus 7.8s**,
roughly 17x.

## What the migration exposed

Step 4 failed: 8 TypeScript errors and 4 esbuild errors, none of them present at baseline.

Root cause was **not** bun. `package.json` declared `"@assistant-ui/react": "latest"`.
npm's `package-lock.json` had frozen that at 0.12.27; bun re-resolved `latest` to 0.15.16,
a version that had removed the legacy hooks (`useThread`, `useThreadRuntime`, `useMessage`)
the source imported.

Seven dependencies in that repo were declared `"latest"`. Each was pinned to the version
the lockfile had actually been serving, which made the migration behavior-preserving *and*
removed the latent footgun:

```
@assistant-ui/react            latest -> ^0.12.27
@radix-ui/react-dialog         latest -> ^1.1.15
@radix-ui/react-dropdown-menu  latest -> ^2.1.16
@radix-ui/react-slot           latest -> ^1.2.4
@radix-ui/react-tabs           latest -> ^1.1.13
@radix-ui/react-tooltip        latest -> ^1.2.8
obsidian                       latest -> ^1.12.3
```

**Lesson:** when a bun migration breaks a build, check for floating specs before concluding
bun is at fault. A stale lockfile is a cache, not a pin.

## Deliberate non-changes

- **vitest kept.** `bun test` is the default for *new* projects; swapping a working
  167-test suite onto a different runner is a separate change with its own risk, and
  bundling it into a package-manager migration would muddy attribution.
- **esbuild kept.** The Obsidian plugin needs specific output (cjs, `obsidian` external).
  Replacing the bundler is not a package-manager concern.
- **One blocked postinstall left blocked.** `@parcel/watcher` wanted to build from source;
  all gates passed without it. Trust nothing that does not need trusting.

`bun run` scripts genuinely execute on bun — confirmed via `process.versions.bun` (1.4.0).
The `(node:PID)` prefix on warnings is bun's node-compat formatting, not a fallback to node.
