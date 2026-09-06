# iterm2

Configuring iTerm2 and exploiting the features that separate it from other terminal emulators —
the preferences model, dynamic profiles, tracking the config in a dotfiles repo, shell
integration, the macOS default-terminal binding, and the power-feature catalog.

## When it triggers

Use it for any iTerm2 request: setting it as the macOS default terminal, adding or fixing
profiles and themes, version-controlling the configuration, installing shell integration, wiring
up triggers or a status bar or a hotkey window, diagnosing a preference that reverts, or
answering which iTerm2 features a user is not yet exploiting.

## Why it exists

iTerm2 has two properties that defeat naive automation, and both fail *silently*:

- It holds its entire configuration in memory and rewrites the plist on quit, so a
  `defaults write` issued while it is running is clobbered with no error. The obvious guard
  (`pgrep -xq iTerm2`) never matches, and the obvious `ps | grep -q` rewrite inverts under
  `pipefail` via SIGPIPE — so scripts tend to report success while doing nothing.
- Its best features are inert until shell integration is installed, and the standard rc guard
  makes a missing installation a no-op rather than an error.

The skill front-loads both, then routes to references for configuration, shell integration, the
default-terminal UTI bindings, and the feature catalog.

## Install

```
claude plugin install solo-skills@dotfiles-agents
```

Ships in the `solo-skills` bundle. macOS only; the shell-integration and
default-terminal paths assume iTerm2 is installed locally.
