---
name: rg-color-masking-gotcha
description: rg default color output in the Bash tool masks matched terms; re-run with --color=never for verifiable quotes
metadata:
  type: feedback
---

When re-running `rg` inside the Bash tool to verify a claim, the default colorized
output gets mangled in this harness: matched substrings render collapsed or replaced by
adjacent fragments (e.g. searching `postmortem` showed up as `ln`; `2 weeks in progress`
showed as `in weeks in`). This makes quoted evidence unreliable and can fake a "term
absent" result.

**Why:** the tool strips/garbles ANSI match highlighting.

**How to apply:** always pass `--color=never --no-heading` (and set
`RIPGREP_CONFIG_PATH=/dev/null` to defeat any global config forcing color) when the rg
output will be quoted as verdict evidence. Cross-check a suspicious "no matches" or a
weird token by `Read`-ing the actual file lines before ruling a provenance claim refuted.
