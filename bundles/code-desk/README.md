# code-desk

Bring a software repo to a documented meta-structure standard and run next-release work
through it: audit compliance, scaffold what's missing, apply the memory-taxonomy and
repo-layout standards, turn the README into an honest value-and-proof pitch, operate a
private fork's upstream review cycle, and reach for opencode reference knowledge whenever an
extender needs to run in both Claude Code and opencode.

## What you get

| Skill | What it does |
|---|---|
| `repo-compliance-audit` | Read-only. Prints a pass/gap table (`ID \| Area \| Verdict \| Detail`) against the repo-meta-structure and memory-taxonomy standards, plus a `N pass / M gap` summary. Never writes to the repo it audits. |
| `mise-en-place-scaffold` | Fill-only. `--plan` (default) shows exactly what it would create for the gaps the audit found and writes nothing; `--apply` creates only those items. Never overwrites, edits, or deletes anything that already exists. |
| `repo-meta-structure` | Reference content: the canonical directory taxonomy, `.claude`/`.github` layout, and gitignore conventions the audit checks against and the scaffold builds from. |
| `memory-taxonomy` | Reference content: where agent memory should live (global vs. project-level), memory vs. rules vs. skills, and when a fact is worth promoting up a layer. |
| `project-memory` | Opts a repo into tracked, in-repo auto-memory so its learnings travel with the repo (wires `.claude/memory/` as the memory directory; never overwrites), and recovers memory after a folder move (dry-run by default). Pure Python 3 stdlib. |
| `readme-value-and-proof` | Turns a README into an honest pitch — what a user gets, backed by real screenshots captured from the running app, not mockups. |
| `private-fork` | Stands up and operates a private mirror of an upstream open-source repo: remotes, governance tier, a delete-vs-disable rubric for unwanted upstream content, a divergence ledger, and the recurring upstream-review cycle. |
| `opencode-expertise` | Reference content for opencode's extension surfaces (config, agents, skills, commands, custom tools, plugins, MCP, rules) and the Claude Code → opencode translation mapping — reach for it when an extender needs to run in both harnesses. |

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

Porting a skill to run under opencode too?
→ opencode-expertise carries the extension-surface reference and the Claude Code →
  opencode translation mapping, so the port doesn't start from scratch.
```

## Honest scope

Every skill here is additive or read-only by design — nothing in this bundle merges,
deletes, or force-overwrites existing content. `mise-en-place-scaffold` reports a conflict
instead of resolving it when a file already exists but doesn't match the expected shape; a
human (or a separate, deliberate edit) still makes that call. `opencode-expertise` is
reference knowledge, not an installer — it does not itself translate or port anything.
