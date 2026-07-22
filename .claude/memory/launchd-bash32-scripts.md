---
name: launchd-bash32-scripts
description: "launchd runs `#!/usr/bin/env bash` scripts under /bin/bash 3.2 — verify with /bin/bash, not shell default"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 364a10ba-855c-4c98-a1e5-d7e7bae3dacf
  modified: 2026-07-22T01:30:51.671Z
---

launchd hands agents a bare PATH, so `#!/usr/bin/env bash` resolves to macOS `/bin/bash`
3.2.57 — NOT the Homebrew bash 5.x that an interactive `bash -n` / `bash script.sh` check
uses (PATH puts /opt/homebrew/bin first). A script can pass every interactive check and
still die at parse time under launchd.

**Why:** bash 3.2's parser treats an unparenthesized `case` pattern's `)` inside `$( )` /
`<( )` as closing the substitution (fixed in bash 4). Also no `mapfile`, no associative
arrays, and empty-array `"${arr[@]}"` expansion errors under `set -u`.

**How to apply:** any script a LaunchAgent invokes gets verified with `/bin/bash -n` and a
`/bin/bash script.sh` dry-run explicitly; prefer plain glob loops over process
substitution; parenthesize case patterns `(pat)`. First install of a Keychain-touching
agent always gets one `launchctl kickstart -k gui/$UID/<label>` while logged in — it
proves interpreter, PATH, and Keychain in one shot (caught a real 3.2 parse failure in
dotfiles-agents' harness-campaign agent, 2026-07-21; fix in `scripts/harness_campaign.sh`).
