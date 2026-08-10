---
name: launchd-bash32-scripts
description: "launchd runs `#!/usr/bin/env bash` scripts under /bin/bash 3.2 — verify with /bin/bash explicitly, not the interactive shell"
metadata: 
  node_type: memory
  type: reference
  originSessionId: f88d2c41-439c-40b6-bbea-2ee31abb84ec
  modified: 2026-08-10T02:02:10.672Z
---

launchd hands agents a bare PATH, so `#!/usr/bin/env bash` resolves to macOS `/bin/bash` 3.2.57 —
not the Homebrew bash 5.x an interactive `bash -n` uses. A script can pass every interactive check
and still die at parse time under launchd (this caught a real failure in
`scripts/harness_campaign.sh`, 2026-07-21).

**Why:** bash 3.2 reads an unparenthesized `case` pattern's `)` inside `$( )` / `<( )` as closing
the substitution (fixed in bash 4). Also: no `mapfile`, no associative arrays, and empty-array
`"${arr[@]}"` expansion errors under `set -u`.

**How to apply:** verify any LaunchAgent-invoked script with `/bin/bash -n` **and** a
`/bin/bash script.sh` dry-run; prefer plain glob loops over process substitution; parenthesize
case patterns `(pat)`. First install of a Keychain-touching agent gets one
`launchctl kickstart -k gui/$UID/<label>` while logged in — it proves interpreter, PATH, and
Keychain in one shot.
