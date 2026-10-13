---
name: launchd-bash32-scripts
description: "launchd runs `#!/usr/bin/env bash` scripts under /bin/bash 3.2 — verify with /bin/bash explicitly, not the interactive shell"
metadata:
  type: project
---

launchd hands agents a bare PATH, so a `#!/usr/bin/env bash` script must remain compatible with
macOS `/bin/bash` 3.2. A script can pass an interactive check with Homebrew Bash and still fail
under its LaunchAgent. (The script that motivated this, `scripts/harness_campaign.sh`, was retired
2026-10-13; its replacement, `harness/scripts/launchd.sh`, is POSIX `sh`.)

**Why:** bash 3.2 reads an unparenthesized `case` pattern's `)` inside `$( )` / `<( )` as closing
the substitution (fixed in bash 4). Also: no `mapfile`, no associative arrays, and empty-array
`"${arr[@]}"` expansion errors under `set -u`.

**How to apply:** verify any LaunchAgent-invoked script with `/bin/bash -n` and a `/bin/bash`
dry run. Prefer plain glob loops over process substitution; parenthesize case patterns `(pat)`.
