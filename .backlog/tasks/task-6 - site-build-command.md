---
id: TASK-6
title: site build command
status: Done
assignee:
  - '@claude'
created_date: '2026-10-13 03:07'
updated_date: '2026-10-13 03:22'
labels: []
milestone: m-0
dependencies:
  - TASK-1
  - TASK-2
  - TASK-4
  - TASK-5
references:
  - build
  - commands
  - cli
  - site-output
  - stylesheet
  - check-links-on-a-pull-request
  - publish-the-site
  - links
modified_files:
  - .groma/index.md
  - .groma/systems/docs/containers/site-cli/components/build.md
  - .groma/systems/docs/containers/site-cli/components/cli.md
  - .groma/systems/docs/containers/site-cli/components/commands.md
  - README.md
  - src/cli.ts
  - src/links.ts
  - test/fixture.ts
  - .groma/flows/check-links-on-a-pull-request.md
  - .groma/flows/publish-the-site.md
  - src/build.ts
  - src/commands.ts
  - test/build.test.ts
  - test/cli.test.ts
priority: high
type: feature
ordinal: 6000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
CI runs `site build` as the repo-wide link check on every pull request and as the build step of the Pages deploy, so it must report every problem in one run and write nothing on failure. Builds the groma ghosts `build` (src/build.ts) and `commands` (src/commands.ts) and wires `cli` to them; the output folder is the store `site-output`.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [x] #1 `site build [--root] [--config] [--output] [--ref]` with the SPEC defaults renders every page and prints `<N> pages built, links verified: <output>`
- [x] #2 On problems, stderr gets one sorted line per problem then `build: <K> problems; nothing written`, exit 1, nothing written
- [x] #3 An output folder that is the checkout or inside it (after resolving symlinks) is refused
- [x] #4 A successful build writes each page and a byte-identical `assets/site.css`, overwrites same-named files and leaves others; output is byte-identical across runs
- [x] #5 No subcommand, or an unknown subcommand or option, prints usage to stderr and exits 1
- [x] #6 Fixture checkouts cover the SPEC list: symlinked plugin README, both frontmatter shapes, renamed CONTRIBUTING, excluded page linked, Mermaid, folder link, image, every error message
- [x] #7 README.md documents the build command, the config keys and the link rules
<!-- AC:END -->

## Definition of Done
<!-- DOD:BEGIN -->
- [x] #1 bunx tsc --noEmit && bun test
- [x] #2 Modified files and groma element refs recorded on the task
- [x] #3 groma scan run; planned components accepted (a clean scan when the task planned none); groma lint clean
<!-- DOD:END -->

## Implementation Plan

<!-- SECTION:PLAN:BEGIN -->
1. src/build.ts: build(options) loads the config, checks the output folder is outside the checkout (realpath of the nearest existing ancestor), selects pages, renders every page, collects ids (+ content), rewrites links, lays out pages; collects config, output and per-page problems (pages in sorted order, document order within a page); writes pages and copies assets/site.css only when there are none.
2. src/commands.ts: run(args) parses 'build' options (--opt value or --opt=value), defaults (root = folder containing the unit, config = unit site.config.json labelled relative to cwd, output /tmp/<name>-site/<name>, ref from config), prints the success line or problems + 'build: <K> problems; nothing written'; usage to stderr and exit 1 for missing/unknown subcommand or option.
3. src/cli.ts calls run and sets the exit code.
4. Links: a target page that failed to render is not fragment-checked (no noise).
5. Tests: test/build.test.ts end to end over a dotfiles-like fixture (symlinked plugin README, both frontmatter shapes, renamed CONTRIBUTING, excluded page linked, Mermaid, folder link, image) asserting outputs, no relative URLs, root URLs naming built files, determinism, overwrite/leave-alone, nothing written on failure, every error message; test/cli.test.ts spawns process.execPath for stdout/stderr/exit codes and usage.
6. README.md: commands, config keys, link rules.
7. Gate, scan, accept build/commands + relations, flows 'Check links on a pull request' and 'Publish the site', lint, finish.
<!-- SECTION:PLAN:END -->

## Implementation Notes

<!-- SECTION:NOTES:BEGIN -->
Product calls: the summary line always says `problems` (`build: 1 problems; nothing written`), as the spec writes it; config problems (and the output-folder and stylesheet problems) print before page problems; a missing --root prints `<root>: checkout folder not found`; the output-inside-checkout refusal prints `<output>: output folder is the checkout or lies inside it` and counts as a problem; the default config is named relative to the working folder (`site.config.json` from the unit folder, `site/site.config.json` from the repo root), a --config path as given; options accept `--opt value` and `--opt=value`, a repeated option takes the last value, and a value starting with `--` is treated as missing; a link to a page that itself failed to render is not fragment-checked, so one bad page does not cascade into missing-heading noise; the success line prints the absolute output path.
Evidence: `bunx tsc --noEmit && bun test` -> 107 pass, 0 fail. test/build.test.ts builds the DOTFILES fixture (symlinked plugins/bun/README.md resolving from plugins/bun/, both decision shapes, renamed CONTRIBUTING, excluded template linked, Mermaid, folder links, images) and checks files, SPEC rewrites, the stylesheet bytes, no relative URL and every root URL naming a built file, --ref, byte-identical rebuilds, overwrite/leave-alone, nothing written on failure (incl. a stale docs/old.html not satisfying a link), every page/config/output/stylesheet error message. test/cli.test.ts spawns process.execPath: usage cases, success line, exit codes, stderr format, config label, defaults. `bun install --frozen-lockfile` -> no changes. `groma scan` matched 2 (build, commands); accepted both and the planned relations cli->commands, commands->build, build->config/pages/render/links/layout/stylesheet/site-output; flows check-links-on-a-pull-request and publish-the-site added; `groma lint` -> No findings.
<!-- SECTION:NOTES:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Added src/build.ts (whole build, problems collected, output-folder refusal, write only when clean, stylesheet copy), src/commands.ts (option parsing, defaults, usage, output lines, exit codes), wired src/cli.ts, and the unit README (commands, config keys, link rules). Added the two CI flows to the map. Verified by 31 new end-to-end and CLI tests and a clean scan/lint.
<!-- SECTION:FINAL_SUMMARY:END -->
