# repo-standards

Bring a repo to a documented meta-structure standard without guesswork or destructive
changes: measure the gap, fill only what's missing, and turn the result into an honest
README. Six skills covering the audit → scaffold → standards-reference → README →
private-fork loop.

## What you get

| Skill | What it does |
|---|---|
| `repo-compliance-audit` | Read-only. Prints a pass/gap table (`ID \| Area \| Verdict \| Detail`) against the repo-meta-structure and memory-taxonomy standards, plus a `N pass / M gap` summary. Never writes to the repo it audits. |
| `mise-en-place-scaffold` | Fill-only. `--plan` (default) shows exactly what it would create for the gaps the audit found and writes nothing; `--apply` creates only those items. Never overwrites, edits, or deletes anything that already exists. |
| `repo-meta-structure` | Reference content: the canonical directory taxonomy, `.claude`/`.github` layout, and gitignore conventions the audit checks against and the scaffold builds from. |
| `memory-taxonomy` | Reference content: where agent memory should live (global vs. project-level), memory vs. rules vs. skills, and when a fact is worth promoting up a layer. |
| `readme-value-and-proof` | Turns a README into an honest pitch — what a user gets, backed by real screenshots captured from the running app, not mockups. |
| `private-fork` | Stands up and operates a private mirror of an upstream open-source repo: remotes, governance tier, a delete-vs-disable rubric for unwanted upstream content, a divergence ledger, and the recurring upstream-review cycle. |

## A worked example

```
You: "run the compliance audit"
→ repo-compliance-audit prints, e.g.:
    ID      | Area          | Verdict | Detail
    META-01 | _meta/ layout | gap     | HANDOFF.md missing
    MEM-02  | memory dir    | gap     | no tracked memory/ directory
    ...
    7 pass / 2 gap

You: "scaffold this repo"
→ mise-en-place-scaffold's --plan shows exactly those 2 gapped items and nothing else;
  --apply creates only those — every file that already existed is left untouched.

Re-run the audit → both gaps are now passes.

Later: "write me a real README for this"
→ readme-value-and-proof captures live screenshots of the app actually running and
  writes the value-proposition pitch around them — not a description of planned features.
```

## Honest scope

Every skill here is additive or read-only by design — nothing in this bundle merges,
deletes, or force-overwrites existing content. `mise-en-place-scaffold` reports a conflict
instead of resolving it when a file already exists but doesn't match the expected shape; a
human (or a separate, deliberate edit) still makes that call.
