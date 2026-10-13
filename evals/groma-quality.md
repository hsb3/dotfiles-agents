# groma map quality

The checks the map last passed, and the groma and scanner versions they ran with. `groma-quality.sh write` rewrites the Versions section from `groma --version` and `.groma/scanners.json`, and the session-start check reports the record stale when either differs; never edit that section by hand. `groma-quality.sh set "<check>" "<result>"` enters a check's result (what the command printed, or what you found) with the date it ran, `<check>` being the start of the row's Check column; a check that does not apply reads `n/a`. An entered row reads, for example, `| Stable rescan | groma scan (created 0) | created 0 | 2026-01-02 |`.

## Versions

groma: 0.6.6+hsb3.eecf3502

| Scanner | Source |
|---|---|
| react | `@hsb3/scanner-react@0.2.8` |
| typescript | `@hsb3/scanner-typescript@0.2.13` |

## Checks

| Check | Command | Result | Date |
|---|---|---|---|
| Containers match the deployment manifests | `groma view <system> --plain` beside the workspace packages and manifests | evals-cli (package.json bin), toolbox-ui (ui/index.html Vite root), pocketbase-service declared for the Dockerfile/railway.toml service; data stores declared | 2026-10-13 |
| Externals from call sites; no unmatched request | `groma scan` (its `unmatched request:` lines) | no unmatched request; externals: dotfiles-agents-checkout, agent-harness-output, railway, pocketbase-release, local-pocketbase-binary (PB_URL is configuration, so no external host line) | 2026-10-13 |
| No component owns only build config | `groma view <container> --plain` | none (ui/vite.config.ts and tsconfig are excluded or unowned) | 2026-10-13 |
| Dead-code candidates | `grep -c '^file .* is not imported' <(groma lint --unimported)` | 0 (ui/src/main.tsx, loaded by ui/index.html, acknowledged as an entry point) | 2026-10-13 |
| Leaves: components with no relationship | `groma lint` (its `has no relationship` lines; acknowledged leaves named) | none: groma lint reports no component without a relationship; no leaf acknowledged | 2026-10-13 |
| Stable rescan | `groma scan` (`created 0`) | created 0 | 2026-10-13 |
| Rescan after a move | `groma scan` after the `git mv` commit (`moved:` lines, `created 0`) | n/a: the only git mv (test/synthetic-tree.ts -> src/synthetic-tree.ts) left an excluded path, so the scan created the record and it was combined into fixture | 2026-10-13 |
| Lint | `groma lint --strict` (exit 0) | groma lint --strict: No findings (exit 0) | 2026-10-13 |
| Map renders | `groma-quality.sh render` (`groma view --check`) | renders: 16 views draw: the overview and 15 terminal depths, 335 routes. | 2026-10-13 |
| backlog.md task references | `groma lint` (the clean summary's `N task references across M tasks`) | 32 task references across 11 tasks | 2026-10-13 |
