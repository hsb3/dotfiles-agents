---
title: SOP — code-agent session continuity
status: active
created: 2026-07-01
---

# SOP — code-agent session continuity

*How work survives across agent sessions: all load-bearing state lives in a durable handoff file,
so any new session — same agent, a different agent, or a fresh clone — can pick up cold. Explicitly
harness-neutral: this replaces reliance on any one harness's memory, compaction, or resume feature.*

Delivered by the **`handoff`** extender.

## The core principle

**Every session must be clearable.** The test, before ending or clearing any session: *"What do I
know that isn't written down?"* — the answer must be **"nothing."** Anything load-bearing that lives
only in the context window is lost the moment the session ends. A coding-agent harness's built-in
memory or auto-compaction is a convenience, **not** the bridge — it is machine-local, agent-specific,
and absent exactly at a cold start on another machine or with another tool. **The file is the
bridge.** Because it is a file, it works identically under Claude Code, opencode, or any agent.

## The artifact

A single **handoff file**, written for a reader with **zero context**:

- **Default: `_meta/HANDOFF.md`, gitignored.** Keeps it blunt — candid gotchas, undecided questions,
  operational state — without becoming audience-facing or tripping repo lint/format CI.
- **Exception: a committed root `HANDOFF.md`** when the project is worked from more than one
  checkout — multiple machines, cloud sessions, collaborators, or fleets of agents on fresh clones. A
  gitignored file is machine-local and will be *absent* precisely at those cold starts. Decide once,
  at setup.
- **Never relocate an existing handoff** — update it where it already lives.
- **Worktree gotcha:** gitignored dirs don't appear in git worktrees; an agent in a worktree must
  read/write the handoff via the main checkout's absolute path.

## Section protocol

Keep it to what a cold reader needs, stable sections up top:

0. **Orientation** — what the repo is, sibling repos, where the canonical docs live.
1. **Current standing + top priority** — where things are, the one thing that matters now.
2. **Last delivered** — what shipped this session, each with PR/issue/commit refs and absolute dates.
3. **Where to start** — the readiness model; the next action.
4. **Conventions & gotchas** — the things that will bite the next session.
5. **Incident log** — notable failures and their resolutions.

Plus, inline: **decisions made, each with its one-line WHY** (decisions without whys rot), and
**what sits in the owner's court** (reviews, approvals, manual steps).

## The two moments

- **On session start** — read the handoff *before* acting. It is the bridge from prior sessions and
  overrides guesses about project state. If none exists and the project clearly has ongoing
  multi-session work, create one.
- **At boundaries** — when work merges, a task completes, or the session is about to be cleared: run
  the **externalization pass**. Read the handoff in full, diff it against this session's reality
  (what shipped, decisions + whys, what's in flight, gotchas, what's in the owner's court), and edit
  **surgically** — update sections in place; don't rewrite. Convert relative dates to absolute.

## The clear/keep decision

When deciding whether to clear or continue a session, answer by naming the **in-flight,
non-externalized state** — running agents, half-reconciled merges, undecided calls — never by
context-window percentage alone. None → clear freely. Mid-flight → keep, or externalize first, then
clear. A window that's mostly logs of finished work → externalize, then clear.

## Harness portability

The handoff is plain markdown at a known path — no dependency on a specific agent's memory or
session model. Any harness that can read a file can pick up the work. The `handoff` extender renders
into every target harness, so the update pass and the pickup discipline are identical under Claude
Code, opencode, or any agent.
