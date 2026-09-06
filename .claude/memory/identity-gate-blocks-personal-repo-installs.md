---
name: identity-gate-blocks-personal-repo-installs
description: "The identity gate cannot express \"install my own tool\" — the owner handle is an unconditional regex ban, and the gh-discovery workaround only resolves for the owner"
metadata:
  type: reference
---

A skill that wraps a CLI living in a **personally-owned** repo cannot tell the user where to get
it. `scripts/check_identity.py` bans the owner handle as a hardcoded regex (alongside the personal
names and client tokens) with **no exemption surface at all**: no per-file allowlist, no inline
pragma, no path exclusion, and `references/*.md` is scanned exactly like `SKILL.md`. The
`requires: [cli:<tool>]` roster field does **not** help — it only gates a fixed `LOCAL_TOOLS`
tuple and `DOTFILES_PATH`, and never reaches the identity rules. The one sanctioned identity
surface is `.claude-plugin/plugin.json`, which is metadata, not prose a user reads.

The gate-legal workaround, verified 2026-08-17 on the `opencode-sandbox` skill — resolve the repo
through the caller's own GitHub account, naming nobody:

```
repo=$(gh search repos <repo-name> --owner @me --json fullName --jq '.[0].fullName')
gh release download --repo "$repo" --pattern '<asset-prefix>-*' --dir /tmp
```

**Its ceiling:** `--owner @me` resolves only for the account that owns the repo, so this works for
the owner and nobody else. Everything shipped elsewhere in the marketplace installs from public
package coordinates instead (brew formula, npm/pip package), which is why the problem had not
surfaced before.

**How to apply:** for a personal-repo tool, put the `gh`-discovery commands **inline in the skill
body**, not in a `references/` file — a pointer fails at exactly the moment the agent is blocked
(tested: the session read "references/install.md has the commands" and asked the user where the
project was instead of opening it). Expect the agent to still ask permission before installing;
that is correct behavior, and the goal is that it presents a runnable install rather than an
unanswerable "where is it?". A real fix means an allowlist in the checker or publishing under a
namespace the gate does not ban. See [[plugin-enablement-needs-per-project-install]].
