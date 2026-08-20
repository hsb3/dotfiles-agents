---
name: pocketbase-best-practices
description: PocketBase design and review guidance — collection schema, API rules and access control, auth flows, SDK usage, query performance, realtime subscriptions, file handling, deployment, and server-side extending. Use when designing a PocketBase schema, writing or auditing API rules, setting up auth, diagnosing slow or N+1 queries, or reviewing a PocketBase backend before it ships.
---

# PocketBase Best Practices

A curated rule set for PocketBase design decisions, composed over a vendored upstream body
of 63 prioritized rules across 9 categories.

## How to use this skill

1. **Start at `base/SKILL.md`** — it carries the full category table and the one-line
   quick reference for every rule id (`coll-*`, `rules-*`, `auth-*`, `sdk-*`, `query-*`,
   `realtime-*`, `file-*`, `deploy-*`, `ext-*`).
2. **Load the individual rule** from `base/rules/<rule-id>.md` for the incorrect/correct
   code pair. Load only the rules the task touches — there are 65 rule files.
3. **Load `base/references/<topic>.md`** for the longer-form treatment of a whole area.
4. **Check "Field notes" below before acting on a rule** — where our verified findings
   differ from or extend the base, this file wins.

## Scope: design, not operation

This skill answers *"is this backend built right"*. It does not drive a running instance.
For mode detection, bootstrap, collection/record CRUD, auth calls, backups, migration
generation, and Go hooks, use the `pocketbase` skill shipped alongside this one in the same
plugin.

Rough split:

| Question | Skill |
|---|---|
| Should this be an auth collection or a base collection? | this one |
| What API rule expresses "owner or admin"? | this one |
| Why is this list endpoint slow? | this one |
| Create the collection / run the migration / take a backup | `pocketbase` |
| Wire a Go hook or a custom route | `pocketbase` |

## Field notes

`references/field-notes.md` carries findings from real PocketBase projects that the vendored
rules do not cover, or cover less precisely. **Where a field note disagrees with `base/`, the
field note wins** — those came from running instances, the base came from documentation.
Each is tagged PROVEN (observed live, with the observation quoted), REPORTED (settled knowledge
from a project that hit it), or INFERRED (from docs, unexercised).

Read it before acting on a base rule in these areas — it is where the expensive surprises are:

| Area | The kind of thing it corrects |
|---|---|
| Access control | Rules that look correct and are public; denial returns 200-empty or 404, never 403 |
| Filters | Filters are unparameterized strings; hidden fields silently never match |
| Hooks | Hooks run before migrations; request-scoped hooks skip programmatic writes; read-then-write races |
| Schema | Field types cannot change in place; views reject UNION and non-unique ids |
| Auth | `upsert` on a superuser invalidates every live session; the stock auth collection allows open signup |
| Files | A fetch wrapper that always JSON-stringifies destroys uploads silently |
| Operations | `serve` errors exit 0; the logs API is ~3 seconds behind |

The single most repeated finding across projects: **custom routes bypass collection rules
entirely.** Rules protect collection endpoints, not your API surface.

## Version skew

The vendored base targets PocketBase v0.36 and later, pinned at a April 2026 upstream commit.
PocketBase moves fast and the base is not re-pinned automatically. When a rule contradicts the
behavior of the version actually in front of you, trust the running instance, verify the
difference, and record it under "Field notes" rather than editing `base/`.

## Found an error?

`base/` is vendored verbatim and must never be hand-edited — an edit there registers as
upstream drift and fails the provenance gate. Corrections go in "Field notes" above, with the
evidence that established them. A correction that belongs upstream should also be reported to
the upstream project named in this skill's README.
