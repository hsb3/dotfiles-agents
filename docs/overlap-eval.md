# Overlap-family eval — when two skills cover one job

_The repeatable procedure for deciding whether skills that do the same job with different
tools should consolidate, and into what shape. First run 2026-08-23 over the
project-management family (kaneo · github-project-board · planning-desk · waves ·
board-triage · handoff · task-authoring), producing DFA-275…278. Written down because the
question recurs every time a second tool lands for a job a skill already covers._

## Trigger

A suspicion that two or more skills cover the same job and differ mainly in the tool they
bind to — usually noticed as the same rule read twice, or a new tool needing a skill that
would restate an existing one.

## Procedure

1. **Inventory** (a read-only scout does this; the session judges). Per suspect skill:
   the job in one sentence; the concrete tool it is hard-bound to; the
   doctrine-vs-mechanics ratio as line counts, not vibes; the footprint (references,
   scripts, hooks, agents, MCP entries, roster `requires:`); and every existing
   cross-pointer between the suspects.
2. **Classify each pair.** Only *same job, different tool* is a real overlap family.
   *Same tool, different job* (github-project-board vs planning-desk) and
   *composes-rather-than-duplicates* (waves over delegation) are not — leave them alone.
3. **Pick the resolution by the doctrine/mechanics ratio.** All four patterns already
   ship in this repo; match, don't invent a fifth:

   | Ratio / shape | Resolution | Shipped example |
   |---|---|---|
   | Mostly mechanics (≳80%) | Keep the tool skill; shared doctrine dedupes to a pointer at its canonical home | kaneo, github-project-board |
   | Mostly doctrine | Tool-agnostic core + per-tool adapter files under a written contract | board-triage |
   | Behavior switches per project | Config key in `.claude/atelier.local.md`, read by hooks | handoff `mode: file\|external` |
   | The job is choosing the tool | Hub skill + thin per-tool skills | diagrams |

4. **Rules that bound the outcome.**
   - Pointer, never copy — one home per rule (ADR 0001's surviving core; ADR 0016 is the
     merge precedent).
   - An abstraction needs at least two live backends and duplication that has actually
     hurt; never pre-build an adapter for a tool nobody uses yet. Two backends covered by
     pointers is a fine end state — extract when the third arrives.
   - A tool-bound skill never ships where its tool can't run (the roster comment above
     the kaneo entries): prose that names absent tools makes a session improvise.
   - Tool-free doctrine is marked in the roster by omitting `requires:`.
   - A new hook-read config key inherits the frontmatter parser, which is currently
     copy-pasted per hook — budget for that duplication or fix it first.
5. **Prove it.** The cheap metric: duplicated doctrine lines removed with zero behavior
   change (each removal maps to the section that now owns the rule). The real test, when
   the change is contested: a cold-agent trial — the same tracker task run under the old
   and the consolidated skills, scored on whether the outputs match and whether the agent
   improvised a tool it didn't have.
6. **Externalize.** Findings become board cards written to the task-authoring skill's
   standard (recorded baselines, criteria that can fail, not-in-scope lists) — never an
   in-repo TODO.

## Standing dispositions (as of 2026-08-23)

- **PM trackers** (kaneo, github-project-board, planning-desk, waves): keep the tool
  skills; dedup doctrine by pointer (DFA-275…277). No generic "operate the board"
  extraction until a third tracker exists — board-triage already owns the one genuinely
  shared job (ranking).
- **Ranked backlog**: consolidated in board-triage; adapters carry the tools.
- **Diagrams**: hub + thin tool skills, deliberate — not pending consolidation.
- **Obsidian toolkit**: one product, four access surfaces — not an overlap family.

## Supersession note (2026-09-08)

The 2026-08-23 disposition above names **github-project-board** as the shipped example of
"mostly mechanics -> keep the tool skill." That skill has since been retired: its
mechanics collapsed into a `board-triage` adapter
(`primitives-core/skills/board-triage/references/adapters/github-projects.md`), which now
also carries the provisioning material (project and field creation, sub-issues, views and
workflows, the status-update mutation) recovered from the retired skill. The
"mostly mechanics -> keep the tool skill" resolution pattern still holds; **kaneo** is now
its shipped example, and `board-triage` itself demonstrates the "mostly doctrine -> adapter
per tool" row instead. The 2026-08-23 record above is left as written; this note is the
correction.
