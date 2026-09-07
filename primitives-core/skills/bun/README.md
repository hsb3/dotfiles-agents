# bun

Bun as the default JS/TS runtime, package manager, test runner, and bundler. Turns npm,
npx, node, and ts-node habits into their bun equivalents, replaces dependencies with
built-ins, and keeps an install from silently resolving the wrong version.

## How it fits together

```mermaid
flowchart TD
  task[A JS or TS task arrives]
  task --> bun[bun routes on what the task actually needs]

  bun -->|Reaching for npm or npx or node| mapping[Command mapping in the skill body]
  bun -->|About to add a dependency| built[cheatsheet - the built-in that replaces it]
  bun -->|Install resolved wrong or a binary vanished| traps[traps - measured evidence per failure]
  bun -->|A global tool or node version disagrees| interop[mise-interop - PATH and runtime ownership]
  bun -->|A whole repo still on npm or pnpm| move[migration - green baseline before any swap]

  mapping --> out[Work runs under bun with bun.lock committed]
  built --> out
  traps --> out
  interop --> out
  move --> out
```

## When it triggers

Running scripts, installing packages, testing, or bundling with bun; choosing between a
bun built-in and an npm dependency; a `bun install` that resolves a stale version or drops
a platform package; a global CLI that PATH or mise shadows; converting a repo's
`package.json` scripts and lockfile off npm, pnpm, or yarn.

## Requires

The `bun` binary on PATH. Nothing else — the references are plain markdown.

## Install

```
claude plugin install bun@dotfiles-agents
```
