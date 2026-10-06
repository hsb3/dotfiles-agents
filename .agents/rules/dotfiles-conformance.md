# Dotfiles conformance

Obligations this repo has toward the machine contract in the dotfiles guide
`tooling-estate.md`, for what it installs outside the marketplace: the skill and OpenCode
laydowns and the weekly harness-campaign launchd job. That guide wins on any conflict.

## Paths

- Lay down only into the directories each harness reads (OpenCode under
  `$XDG_CONFIG_HOME/opencode/`). A harness that fixes its own path outside XDG is a declared
  exception in the dotfiles registry, with the reason.
- Runtime state and logs written outside this checkout go under
  `$XDG_STATE_HOME/dotfiles-agents/<tool>/`; data under `$XDG_DATA_HOME/dotfiles-agents/<tool>/`.
  Never under the system temp directory.
- Declare every installed path in the dotfiles registry entry for this repo; change the
  declaration in the same change as the installer.

## launchd

- Jobs use this repo's own label prefix and are rendered from a data file in this repo,
  never stowed.
- The installer boots out loaded jobs in that prefix that the data no longer lists, and
  writes PATH with the user bin directory first.

## Check

- Provide one read-only command, registered in the dotfiles registry, that exits non-zero
  when a laydown or job this repo installed is missing or stale. It writes nothing.
- Never read, source or call anything in dotfiles.

## Branches

- Work only on a branch in a `.worktrees/<branch>` checkout, branched off `dev`.
