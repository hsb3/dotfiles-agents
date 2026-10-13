# groma map quality

The checks the map last passed, and the groma and scanner versions they ran with. `groma-quality.sh write` rewrites the Versions section from `groma --version` and `.groma/scanners.json`, and the session-start check reports the record stale when either differs; never edit that section by hand. `groma-quality.sh set "<check>" "<result>"` enters a check's result (what the command printed, or what you found) with the date it ran, `<check>` being the start of the row's Check column; a check that does not apply reads `n/a`. An entered row reads, for example, `| Stable rescan | groma scan (created 0) | created 0 | 2026-01-02 |`.

## Versions

groma: 0.6.6+hsb3.eecf3502

| Scanner | Source |
|---|---|
| typescript | `@hsb3/scanner-typescript@0.2.13` |

## Checks

| Check | Command | Result | Date |
|---|---|---|---|
| Containers match the deployment manifests | `groma view <system> --plain` beside the workspace packages and manifests | 1 executable (package.json bin site -> site-cli) plus 3 declared stores (site-config, stylesheet, site-output); no deployment manifests | 2026-10-12 |
| Externals from call sites; no unmatched request | `groma scan` (its `unmatched request:` lines) | no unmatched request or external host lines (the CLI makes no requests); 6 externals declared from SPEC | 2026-10-12 |
| No component owns only build config | `groma view <container> --plain` | 9 components, each owns one src/*.ts file | 2026-10-12 |
| Dead-code candidates | `grep -c '^file .* is not imported' <(groma lint --unimported)` | 0 (groma lint --unimported: no files nothing imports) | 2026-10-12 |
| Leaves: components with no relationship | `groma lint` (its `has no relationship` lines; acknowledged leaves named) | 0 has no relationship lines; no acknowledged leaves | 2026-10-12 |
| Stable rescan | `groma scan` (`created 0`) | created 0, refreshed 9, matched 0 | 2026-10-12 |
| Rescan after a move | `groma scan` after the `git mv` commit (`moved:` lines, `created 0`) | n/a (no file moved in v1) | 2026-10-12 |
| Lint | `groma lint --strict` (exit 0) | groma lint --strict exit 0, No findings | 2026-10-12 |
| Map renders | `groma-quality.sh render` (`groma view --check`) | renders: 10 views draw: the overview and 9 terminal depths, 185 routes. | 2026-10-12 |
| backlog.md task references | `groma lint` (the clean summary's `N task references across M tasks`) | 25 task references across 7 tasks | 2026-10-12 |
