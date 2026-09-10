---
name: handoff
description: Maintain the project's session-handoff so a brand-new session can pick up work cold - a file this skill writes directly (_meta/HANDOFF.md, HANDOFF.md, .claude/HANDOFF.md, or a per-project override), or an external tracker/board it signals via a freshness stamp when the project's handoff key is set to external mode. Use at session boundaries when the user says "wrap up", "update the handoff", "prepare to clear/compact", "write the handoff", or runs /handoff; use "/handoff init" to create the file in a project that lacks one (file mode only). Updates current state, in-flight work, decisions made and pending, and gotchas - or, in external mode, updates the external handoff and touches its stamp - the externalization pass that makes a session clearable.
---

# Project Handoff

Purpose: make every session **clearable** by externalizing all load-bearing state into one
file a cold session can read in under ~10k tokens. The handoff is the bridge for NEW
sessions (not resumes) - write for a reader with zero context.

This skill is the **produce** edge of atelier's handoff loop; its enforcement partners are
three co-homed hooks that read or gate on the SAME file it writes: `context-watermark`,
`handoff-freshness-guard` (blocks a manual `/compact` when the handoff is missing or stale),
and `session-handoff-surfacer` (surfaces the handoff to a fresh cold-start session). All three
check the SAME candidate paths in the SAME order this skill writes to - keeping that list in
sync is load-bearing, not cosmetic.

<!-- harness:claude-code -->
`context-watermark` nudges "run /handoff, then /clear or /compact" once context crosses the
soft/hard watermark.
<!-- /harness -->

## File location

**Precedence contract - must match the hooks exactly.** The candidate list below is the same
one, in the same order, that atelier's `handoff-freshness-guard` and
`session-handoff-surfacer` hooks check: `_meta/HANDOFF.md` → `HANDOFF.md` → `.claude/HANDOFF.md`.
Do not reorder or add a path here without changing the hooks' `CANDIDATE_PATHS` in lockstep - a
mismatch means the hooks act on a different file than this skill writes.

**Per-project override - file mode.** A project whose handoff lives somewhere else entirely
(not one of the candidates above) can say so with a `handoff:` key in the project's activation
file:

<!-- harness:claude-code -->
Use the activation skill’s selected policy in the sole native agent directory or
`.agents` for multiple agents. `ATELIER_ACTIVATION_FILE` wins. Preserve existing
handoff paths and stamps when policy placement changes.
<!-- /harness -->

```markdown
---
handoff: docs/HANDOFF.md
---
```

That path, when it resolves inside the project root, is authoritative for both hooks and for
this skill - it wins over any standard candidate, and the standard search never runs as a
fallback (a stated-but-not-yet-created override means "no handoff", not "check the
candidates"). Leave the key absent, or unset, or pointing outside the project root, and
nothing changes: the standard candidate search above still governs. When an override is
active, write and update the handoff there instead of at a candidate path. The same value
can be spelled as a mapping, `{mode: file, path: docs/HANDOFF.md}` - identical to the scalar
form, just explicit.

**Per-project override - external mode.** A project whose handoff is not a file at all - a
tracker task, a Linear issue, a wiki page - has nothing here for this skill to write, but
still needs the freshness guard and the cold-start surfacer to know the handoff exists. Say
so with the mapping form:

<!-- harness:claude-code -->
```markdown
---
handoff:
  mode: external
  stamp: .claude/handoff.stamp
  location: Board task ABC-123
---
```
<!-- /harness -->

`stamp` is a project-relative path this skill touches (`touch <stamp>`), never writes content
to - it is a freshness signal standing in for a file that does not exist. `location` is free
text pointing at where the real handoff lives; it is never path-resolved and never read from
disk. **The session's obligation is different from file mode: update the external handoff
first, then touch the stamp - do not write a HANDOFF.md anywhere.** Gitignore the stamp; it
carries no content worth tracking, only an mtime. `/handoff init` and the "gitignored `_meta/`
working desk" default below are file-mode guidance only - external mode has no file to
initialize, since the handoff already exists on the board before atelier is ever pointed at it.

**Default: a gitignored `_meta/` working desk (file mode).** On `/handoff init`, if the project has no
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

### Opt-in concurrent sessions

When the existing external `handoff:` mapping declares `scope: session`, use separate native
cards and certificates. The configured `location` remains the lead-owned project bridge;
never rewrite it from a concurrent session. Legacy configurations without this scope keep
the update pass below.

Launch each dedicated runtime with a fresh `ATELIER_WRITER_ID`, including every independent
resume. Generate it once for that launch with `python3 -c 'import uuid; print(uuid.uuid4())'`.
For Codex, pass the same value in the process environment and
`-c 'shell_environment_policy.set.ATELIER_WRITER_ID="<fresh value>"'`.
Clients attached to one runtime/session are the same writer. Independent attached-client
identity is unsupported. Claude Code session mode is unsupported until native transport is
proved; do not substitute a shared stamp or guessed native ID.

1. Read the bridge and your own or explicitly named predecessor card. Run the helper's
   `discover --project <project> --root <checkout> --related <work-card>` command. It scans
   every open handoff and its relationships before displaying a page, retaining unknown
   relevance and flagging possible overlapping work. Repeat the same command with the
   returned `--offset` and `--page-size` until `remaining` is zero. Read relevant and unknown
   bodies; reconcile conflicts explicitly. Discovery is a scan, not a lock on other writers.
2. Write the updated body to a temporary file. Include repository identity, branch/worktree,
   related work, predecessor, decisions and unresolved work. Wait for all independent tools
   and writers to finish before certification; never run the final tool in parallel.
3. Use the native hook's `ATELIER_HANDOFF_BINDING` and `ATELIER_TOOL_CALL_ID`, injected into
   the current shell call. Never select a latest binding from disk or override these values.
   Run `python3 <handoff-helper> persist --project
   <project> --body-file <body-file> --title <meaningful-title> --label <area-label> --label
   <type-label> --related <work-card>` as the final tool. Add `--predecessor <card>` for a new
   incarnation. The helper invalidates, checks hook/tool identity, finds or creates your native
   card, writes and reads back its body, then certifies only the current transaction.
   The checkout must have an `origin` remote; metadata and work/predecessor relations are
   verified alongside the body. Kata trims surrounding body whitespace; interior text must
   match exactly. Per-tool transaction files are local disposable state, never board records.

<!-- harness:claude-code -->
The helper is `<atelier-hooks>/_lib/session_handoff.py`. Native Codex Bash hooks inject
the current transaction through `updatedInput`; an unregistered hook cannot certify.
<!-- /harness -->
4. Any helper, invalidation, readback or publication failure means stop compaction. Every
   native tool, including a read-only one, invalidates certification. Manual compaction checks
   the latest completed native transaction and consumes its certificate once; automatic
   compaction remains nonblocking. Missing identity or runtime evidence never falls back.
5. Never delete, purge, or close handoff cards automatically. Close only after successor
   acknowledgement or verified completion reconciled into the lead bridge. Keep unknown or
   abandoned sessions visible for lead review. A sibling's stale certificate does not block yours.

Session certificates and binding files are local ignored runtime state derived from the
configured stamp under the current worktree. They are never inherited from the main checkout
or another machine. A replacement process owns a new card; its predecessor preserves continuity.

### Legacy project scope

1. Read the existing handoff in full.
2. Diff it against THIS session's reality:
   - what shipped / changed (with PR & issue refs, absolute dates)
   - decisions made, each with its one-line WHY (decisions without whys rot)
   - what is in flight (agents, open PRs, unfinished reconciliations)
   - gotchas discovered the hard way (the things that will bite the next session)
   - what sits in the owner's court (reviews, decisions, manual steps)
3. Edit surgically - update sections in place, do not rewrite the handoff wholesale. Convert
   relative dates ("today", "yesterday") to absolute (YYYY-MM-DD).
4. (File mode; a board/tracker item follows its own tracker's conventions instead.) Keep the
   file a TIGHT BRIDGE, not a diary (target ~150 lines; hard ceiling ~200). The
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
7. **External mode only:** the pass isn't done until the stamp is touched, and the order
   matters - update the external handoff itself first (the board task, the tracker item;
   this skill has no file to write there), THEN run `touch <stamp>` last. An untouched stamp
   is what makes `handoff-freshness-guard` block the next manual `/compact` even though the
   board is current - the guard can only see the stamp's age, never the board's content.

## `/handoff init` - when no handoff exists

<!-- harness:claude-code -->
Survey the repo first (README, CLAUDE.md, git log, issue board if available).
<!-- /harness -->

Create the gitignored `_meta/` desk per "File location" above (or the committed root file if
the multi-checkout exception applies), then write the handoff from this skeleton, filling
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
  handoff has rotted - distill it as part of the pass.
- The handoff records ONLY what a fresh session cannot derive from the repo itself (state,
  intent, decisions, gotchas). Run a de-dup audit each pass against **whichever durable docs
  this project actually has** - never against a fixed filename. A gotcha earns a place in the
  handoff only if no durable doc already carries it; replace anything duplicated (SDLC rules,
  wire conventions, doc map, worktree model) with a one-line pointer naming the file and
  section ("see README § Logs").

  <!-- harness:claude-code -->
  Here that is README, `CLAUDE.md`, reference pages; if `CLAUDE.md` is absent the audit still
  runs, on what is there. `CLAUDE.md`, where it exists, is **HOT-LOADED into every session**,
  so duplicating it is wasted context that loads twice - but a README fact restated here is
  the same debt, just paid on read instead of on load.
  <!-- /harness -->


<!-- harness:claude-code -->
## Codex lifecycle

Read routing from the selected activation file exactly as above. In external mode, update the
external handoff first and touch its configured local stamp last. Trusted Codex PreCompact
hooks interrupt manual compaction when that stamp or file is missing or stale; automatic
compaction only warns. A new Codex session receives the file excerpt or external pointer
through SessionStart. Use the native `/hooks` screen to check trust if either signal is
missing; a configured activation file alone does not prove the hook ran.
<!-- /harness -->
