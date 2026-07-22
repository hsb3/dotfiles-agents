---
name: agent-harness-standing-permission
description: "Henry pre-authorized commit/push/PR/merge for the agent-harness build lane (dev only, never main)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 7cd91ebc-af47-437b-8eec-c3a53e5836ad
  modified: 2026-07-21T17:58:00.173Z
---

On 2026-07-21, during the agent-harness build (branch `feat/agent-harness`, design at
`_meta/research/agent-harness/DESIGN.md`), Henry granted standing permission: "permission
granted to push, commit, create pr and merge."

**Why:** the harness build runs in waves with foreman-verified gates; per-action asking would
block an effort he already signed off (design §8, decisions D1–D5 resolved 2026-07-21).

**How to apply:** commit/push on `feat/agent-harness` (or successor harness branches), open
PRs into `dev`, squash-merge them once the wave's hard gates pass (`make ci`,
`make harness-test`, live smoke where the wave requires it). This never extends to `main` —
publish-only, CI-guarded — and doesn't cover other lanes (e.g. `feat/extender-db`, whose
promotion stays in Henry's court). After opening any PR, watch CI to green and report
(standing global feedback).
