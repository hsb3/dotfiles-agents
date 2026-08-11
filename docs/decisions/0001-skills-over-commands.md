---
title: "Skills over commands"
type: decision
status: Superseded
created: 2026-06-28
updated: 2026-08-10
superseded_by: decision-010
summary: Command intent folds into skills or retires; the roster carries no command type. SUPERSEDED 2026-08-10 by decision-010 — the roster now carries a command type.
---

# 0001 · Skills over commands

> **SUPERSEDED 2026-08-10 by [decision-010](decision-010%20-%20Commands-become-a-fourth-primitive-type.md).**
> The roster now carries a `command` type. What held up is the anti-duplication rule below —
> decision-010 keeps it by requiring a command to stay thin and defer to its skill rather than
> restate it. What did not hold up is the conclusion that commands therefore never migrate: this
> ADR weighed only the operator axis, where a skill already offers a slash invocation. The axis it
> missed is that a command is what you hand an *agent* to perform on your behalf, which no amount
> of skill polish substitutes for. Read this ADR for the duplication argument, not for the ban.

_Commands never migrate as commands: their intent folds into skills, or they retire._

- **Provenance:** ratified in CANON 2026-06-28; ADR backfilled 2026-07-03 per #40
- **Raised by:** strategy-desk CANON decision 3 ("Commands dropped"); vault decision
  `skills-over-commands` (2026-07-02)

## Context

The retiring `hsb3-custom-plugins` tier carried slash commands alongside skills. Commands
are a Claude-Code-only surface with no equivalent in opencode or CMA, and their content
(prompt templates) duplicates what a skill's body already carries — keeping both means two
homes for one capability and an untranslatable primitive type in the roster.

## Decision

No command survives as-is. Each existing command's intent **folds into its paired skill**
(the skill gains the invocation guidance) or the command **retires with a rationale**. The
roster carries no `command` primitive type; new capability always lands as a skill.

## Consequences

- The T-15 inventory's 16 residual commands in `hsb3-custom-plugins` must be folded/dropped
  before that repo retires (tracked in #32).
- The workbench promotion gate flags `commands/` directories as fix-ups (CANON 3), and the
  repo meta-structure checklist flags `.claude/commands/` as migration debt (CLAUDE-07 —
  the row that cites this ADR).
- Revisit only if a target tool makes commands a first-class, translatable surface.

## Affects

`primitives-core.yaml` (no command type) · repo-meta-structure `references/checklist.md`
CLAUDE-07 · workbench `scripts/promote_check.py` (commands/ note) · #32 (the fold/retire
worklist).
