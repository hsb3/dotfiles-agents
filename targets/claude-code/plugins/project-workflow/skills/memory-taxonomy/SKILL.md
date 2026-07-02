---
name: memory-taxonomy
description: >-
  The memory taxonomy v1 — consult it whenever the question is where agent memory lives or
  how it moves: "where does this memory go", "promote a memory", "set up project memory",
  "memory vs rule vs skill". Defines the two layers (global dotfiles-managed vs project
  git-tracked `.claude/memory/`), the two loading modes (always-on `MEMORY.md` index vs
  situational topic files), the three kinds (memory = facts, rules = directives, skills =
  procedures), the secret-only birth rule, and the curation-time promotion mechanism —
  with the approved v1 defaults for cadence and limits. Use when recording a learned fact,
  running a curation pass at a wrap-up/handoff boundary, opting a repo into tracked memory,
  or deciding whether something is a memory, a rule, or a skill. This skill is reference
  content only — the compliance audit reads its checklist; the memory system itself is the
  cc-project-memory CLI plus Claude Code's native mechanisms.
---

# Memory taxonomy standard

The **single consultable source** for where agent memory lives and how it moves. Three
consumers read this identical content: a human/agent session (you, now), the
repo-compliance-audit skill (checks structure against `references/checklist.md`), and
Henry at curation time. The system *design* behind it — storage mechanics, loading
semantics, settings precedence — is the memory-standard technical design (hsb-2026 vault,
`02_Projects/02_DEVTOOLS/1_Engineering/technical-designs/memory-standard.md`); this
content is the standard a session applies, and it links to that design rather than
restating it.

## How to answer "where does this go"

| Question is about… | Read |
|---|---|
| The layers, loading modes, kinds, birth rule, promotion mechanism, v1 defaults | `references/taxonomy.md` |
| A specific compliance check, its `MEM-xx` ID, or its pass condition | `references/checklist.md` |
| The CLI that opts a repo in (`cc-project-memory`) or migrates a relocated one | `references/tooling.md` |

Answer from the reference content directly — do not reconstruct the taxonomy from memory
or from how some repo happens to look.

## Error path — repo not opted in (read this before writing any memory)

If the current repo has **no git-tracked `.claude/memory/` with a `MEMORY.md` index**, the
structure this standard requires is missing. Do NOT silently fall back to Claude Code's
hidden machine-local default (`~/.claude/projects/<slug>/memory/`) — that is exactly the
invisible, non-portable state this standard eliminates. Instead:

1. **Name the gap to the user**: this repo is not opted into tracked project memory.
2. **Point at the fix**: run `cc-project-memory init` in the repo (see
   `references/tooling.md`), or use the mise-en-place scaffold skill, then commit
   `.claude/memory/`.
3. If the session must proceed before the structure exists, **flag** that anything written
   meanwhile lands in the hidden default and should be migrated
   (`cc-project-memory init --migrate`) once the repo is opted in.

## What this skill does NOT do

- **No memory system implementation** — storage, loading, and settings precedence are the
  memory-standard technical design and the as-built `cc-project-memory` CLI; this is the
  document a session reads.
- **No auditing** — pass/gap verdicts come from the sibling `repo-compliance-audit` skill,
  which reads `references/checklist.md` from this skill's directory.
- **No content judgment** — the `MEM-xx` rows are structure-only; what a memory *says* is
  Henry's curation judgment, never a compliance surface.
- **No layout ownership** — that `.claude/memory/` appears in the repo layout at all is the
  repo-meta-structure standard's row (`CLAUDE-03` / `IGNORE-12`); everything
  memory-specific beyond placement is owned here.
- **No cross-harness memory rendering** — this standard is Claude Code-native; a memory
  equivalent for other harnesses is an open question owned by the translation service, and
  this content ships as ordinary skill text on all targets.

## For the audit (machine consumer)

- Checklist contract: `references/checklist.md` — a table `ID | Area | Check | Pass
  condition` with stable `MEM-xx` IDs, same contract as the repo-meta-structure checklist
  (closed check-type vocabulary; see the file's header). IDs are stable across skill renames.
- Locate this content from a sibling skill via the plugin root:
  `${CLAUDE_PLUGIN_ROOT}/skills/memory-taxonomy/references/checklist.md`.
