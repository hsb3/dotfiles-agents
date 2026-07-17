---
name: handoff
description: Maintain the project's session-handoff file so a brand-new session can pick up work cold. Use at session boundaries when the user says "wrap up", "update the handoff", "prepare to clear/compact", "write the handoff", or runs /handoff; use "/handoff init" to create the file in a project that lacks one. Updates _meta/HANDOFF.md (or HANDOFF.md / .claude/HANDOFF.md) with current state, in-flight work, decisions made and pending, and gotchas - the externalization pass that makes a session clearable.
---

# Project Handoff

Purpose: make every session **clearable** by externalizing all load-bearing state into one
file a cold session can read in under ~10k tokens. The handoff is the bridge for NEW
sessions (not resumes) - write for a reader with zero context.

## File location

**Default: a gitignored `_meta/` working desk.** On `/handoff init`, if the project has no
handoff: create `_meta/` (`mkdir -p _meta`), ensure `_meta/` is in `.gitignore` (append it
if missing), and write `_meta/HANDOFF.md`. Gitignored-by-default is deliberate: the handoff
must stay BLUNT (candid gotchas, undecided questions, operational state) without becoming
an audience-facing document, without PR churn, and without tripping repo lint/format CI.

**Exception - commit a root `HANDOFF.md` instead** when the project is worked from more
than one checkout: cloud sessions, multiple machines, collaborators, or fleets of agents
operating on fresh clones. A gitignored file is machine-local and will be ABSENT exactly
at the cold-start moment in those setups. If unsure, ask the user once at init.

**Existing handoffs:** never relocate one; update it where it lives (`_meta/HANDOFF.md`,
root `HANDOFF.md`, or `.claude/HANDOFF.md`).

**Worktree gotcha:** gitignored dirs do not appear in git worktrees. Subagents working in
worktrees must read/write the handoff via the MAIN checkout's absolute path.

## Default invocation - the update pass

1. Read the existing handoff in full.
2. Diff it against THIS session's reality:
   - what shipped / changed (with PR & issue refs, absolute dates)
   - decisions made, each with its one-line WHY (decisions without whys rot)
   - what is in flight (agents, open PRs, unfinished reconciliations)
   - gotchas discovered the hard way (the things that will bite the next session)
   - what sits in the owner's court (reviews, decisions, manual steps)
3. Edit surgically - update sections in place, do not rewrite the file. Convert relative
   dates ("today", "yesterday") to absolute (YYYY-MM-DD).
4. Keep the file a TIGHT BRIDGE, not a diary (target ~150 lines; hard ceiling ~200). The
   dominant failure mode is a growing chronological wave-log of dated session entries -
   each session appends another multi-paragraph block and the bridge rots into a journal.
   When that creeps in, distill in THIS order so nothing load-bearing is lost:
   a. PROMOTE the durable gotchas/decisions buried in the dated entries up into the
      conventions/gotchas section - they outlive the narrative that introduced them.
   b. COLLAPSE the chronological narrative to a one-line-per-era pointer; the blow-by-blow
      already lives in merged PRs + issues + ADRs + git history (where the prior full
      version of the handoff also remains, so the prune is non-destructive).
   c. DELETE superseded guidance outright.
   Resist appending a fresh dated section every session - fold this session's deliverables
   into a short "recent deliveries" list and let older ones age into the pointer.
5. Update auto-memory too if a durable user-preference or feedback fact emerged this
   session (one fact per file; pointer line in MEMORY.md).
6. Finish by answering, in your reply: **"what do I still know that isn't written down?"**
   If anything, write it first. Then state plainly whether the session is now clearable,
   or what keeps it un-clearable (e.g., background agents still running).

## `/handoff init` - when no handoff exists

Survey the repo first (README, CLAUDE.md, git log, issue board if available). Create the
gitignored `_meta/` desk per "File location" above (or the committed root file if the
multi-checkout exception applies), then write the handoff from this skeleton, filling
every section with real content or deleting it:

```markdown
# HANDOFF - read this first when starting a session in <project>

_Cold-start onboarding. Last updated: YYYY-MM-DD. Keep updated at session boundaries (/handoff)._

## 1. What this is (2-4 lines: the product/goal, and any sibling repos that matter)
## 2. Current state (what works, what is deployed, where)
## 3. In flight / next up (issue + PR refs)
## 4. Decisions made (date - decision - one-line why)
## 5. Pending decisions (the owner's court)
## 6. Conventions & gotchas (the things that bite; exact commands)
## 7. Map (key docs, dashboards, boards, related repos)
```

## Rules

- No secrets in the handoff, ever (it may be committed or shared).
- If the handoff is COMMITTED/tracked (the standard tracks `_meta/` by default, ADR-0006, so
  `_meta/HANDOFF.md` is in-tree), exempt its path from the repo's prose
  formatter so handoff prose (em-dashes, long lines, no-table markdown) can't fail the format
  CI and block merges - e.g. add it to `.prettierignore`. Gotcha: a tracked `_meta/HANDOFF.md`
  is IN the formatter's scope, so it must be
  listed in the formatter's OWN ignore file (which prettier reads after `.gitignore`, so it wins).
- Target cost: ~1-2k tokens of writing per boundary. If an update takes much longer, the
  file has rotted - distill it as part of the pass.
- The handoff records ONLY what a fresh session cannot derive from the repo itself (state,
  intent, decisions, gotchas). **CLAUDE.md / AGENTS.md is HOT-LOADED into every session**, so
  any convention copied from it is pure wasted context that loads twice. Run a de-dup audit
  each pass: a gotcha earns a place in the handoff only if CLAUDE.md doesn't already carry
  it; replace anything duplicated (SDLC rules, wire conventions, doc map, worktree model)
  with a one-line pointer ("see CLAUDE.md"). README too - link, don't restate.
