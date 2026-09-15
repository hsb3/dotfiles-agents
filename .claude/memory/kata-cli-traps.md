---
name: kata-cli-traps
description: kata CLI and sync behaviours that bit the 2026-09-14 triage — one label per `label add`, sync-created mirrors arrive without `github_issue` metadata, `create --json` can emit raw control characters
metadata:
  type: project
---

Three kata behaviours measured on 2026-09-14 (kata v0.17.2, daemon schema 27):

- `kata label add <ref> <label>` accepts exactly one label; a second label argument fails with "accepts 2 arg(s)". Loop per label.
- A card the GitHub sync creates (author `hsb3`, body ending "Imported from GitHub: …") has EMPTY metadata, so `make board-reconcile` classifies its issue as `untracked` until `kata meta set <ref> github_issue <N>` is run by hand (kk1m / #559 arrived this way; wvkc / #488 before it).
- `kata create --json` echoes the body, and a body containing a control character makes the JSON unparseable; read the new short_id back with `kata list` instead of parsing the create output.

**Why:** each one silently derails a scripted triage pass (the label loop half-applies, the reconcile lies, the create looks failed when it succeeded).

**How to apply:** one label per call; stamp `github_issue` on every fresh mirror as part of intake; never `set -e` on parsing create output. See [[signals-that-lie]] for the general pattern.
