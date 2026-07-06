---
title: "Governance-home map — where project docs live"
status: active
created: 2026-07-05
---

# Where governance lives

_The single answer to "where does this document belong?" for the agent-extenders project.
Project governance spans several surfaces; this map assigns exactly **one canonical home per
artifact type** so nothing drifts or duplicates. If a doc exists in two places, the home column
below wins and the other copy is redundant. See also [`CHARTER.md`](CHARTER.md) (precedence page)._

## The rule in one line

**Decisions of record → the Strategy Desk. Execution → the Engineering Desk. State → the board.
Brainstorm → the vault. Nothing else goes in the vault.**

## The surfaces

| Surface | Path | Owns |
|---|---|---|
| **Strategy Desk** (cowork) | `~/Documents/Claude/Projects/dotfiles-agents-cowork/` | decisions of record, product/strategy design, analyses, strategy briefings — everything an engineer doesn't need to do the work |
| **Engineering Desk** (this repo, `dotfiles-agents`) | `~/Developer/dotfiles-agents/` | the code + repo-scoped ADRs, technical docs, execution (issue bodies + plans), repo-local briefings — what an engineer needs |
| **GitHub board** | project #9 (`github.com/users/hsb3/projects/9`) | work STATE (status, priority, milestone) |
| **Obsidian vault** | `hsb-2026/…/02_DEVTOOLS/` | **brainstorm / journal ONLY** (`1_Journal/`) |

## One home per artifact

| Artifact | Canonical home | Notes |
|---|---|---|
| **Decision of record** | cowork `_structure/CANON.md` + `_structure/decisions/` ADRs | CANON is the full upstream record + precedence page |
| Repo-scoped decision (binds code) | this repo `docs/decisions/` ADR | a subset of CANON, cited from code; `docs/CHARTER.md` is the repo-local summary |
| **Product / strategy design** | cowork strategy desk (`analyses/`, product-specs) | the "why" and the shape |
| **Technical architecture** | this repo `docs/` | lives with the code it describes |
| **Issue body** (the contract) + **build plan** | this repo `_meta/plans/` (→ `_meta/issues/`) | one folder per open issue; mirrors a GitHub issue |
| **Work state** | the GitHub board (project #9) | status / priority / impact / effort / workstream / milestone — never a flat file |
| **Briefing / comms package** | `_meta/briefings/<date>-<slug>/` | cowork for strategy readouts, this repo for repo-local |
| **Shipped spec / test-plan** | `_archive/` (cowork or this repo) | the running code is the realization; the spec is provenance |
| **Brainstorm / journal / raw notes** | the Obsidian vault `1_Journal/` | the vault's ONLY role |

## The two desks: Strategy Desk vs Engineering Desk

Two working desks, one governing line: **the Strategy Desk holds everything a software engineer does
NOT need open to do their work; the Engineering Desk holds what they do.**

- **Strategy Desk** (cowork, `dotfiles-agents-cowork/`) — the *why*, *whether*, and *what-shape*:
  decisions of record, product/strategy design, cross-repo & portfolio strategy, analyses.
  Source-agnostic; an engineer implementing a well-scoped issue never needs to open it.
- **Engineering Desk** (in-repo, `_meta/plans/` → `_meta/issues/`) — everything an engineer needs to
  build: the issue body (the contract), the build plan (deliverables, acceptance, gates, order, cited
  to `path:line`), and the board mapping. Source-grounded; travels with the code.

**Single-copy rule (anti-drift).** The authoritative issue body + build plan live in exactly ONE
place — the Engineering Desk. The Strategy Desk links to the issue; it never retains a parallel copy
or restates counts/acceptance/status (that is exactly what went stale on 2026-07-05). It may *draft*
intent, but once an issue is filed the repo/board is authoritative.

| Strategy Desk — engineer does NOT need it | Engineering Desk — engineer needs it |
|---|---|
| Decisions of record (ADRs) + CANON summary | Issue bodies (the contract) |
| Product / strategy design (product-specs, one-pagers) | Build plans (deliverables, acceptance, gates, order) |
| Cross-repo / portfolio strategy (dotfiles-agents <-> workbench, promotion pipeline, priorities) | Per-repo execution + the board mapping |
| Analyses / research that inform a decision | Source-grounded technical detail; what actually shipped |
| "Should we build X, and why?" | "Build X — here is exactly how, here is the gate." |

**The test.** Would an engineer need this open to implement a well-scoped issue? **No → Strategy Desk.
Yes → Engineering Desk.** (Writing *"why"/"whether"* or comparing repos → Strategy; writing an
acceptance criterion or a `path:line` citation → Engineering.)

**The handoff.** Strategy frames + decides + designs -> hands off a brief ("file an issue for X per
decision Y"), NOT a retained issue body -> the Engineering Desk authors the conformant issue body +
source-grounded plan and files it -> Strategy links to `#N`; the repo/board owns detail + state.

## Common conventions across both desks

Both desks share one way of recording decisions and a common doc-frontmatter core, so a reader or
agent crossing desks meets the same shapes.

**Decision records (ADRs) — identical format on both desks.** One file per decision,
`NNNN-kebab-title.md`, append-only, indexed (`README.md` / `decisions-log.md`):
- Status lifecycle: `Proposed -> Accepted | Rejected | Superseded-by-NNNN`.
- **Supersession** (the decision changed) vs **correction** (a premise was wrong — dated
  `> Correction (YYYY-MM-DD):` callout + strike the false line); never leave a falsified claim
  readable as current truth.
- **Strategy Desk** decisions live in `_structure/decisions/`; **repo-scoped** decisions that bind
  code also get a dotfiles `docs/decisions/` ADR cited from code. **CANON** summarizes the full set
  and is the precedence page.

**Common doc frontmatter (core).** Every durable doc on either desk opens with YAML frontmatter:
- **Required:** `title` · `type` · `status` (`draft | active | superseded by <path>`) · `created` (YYYY-MM-DD).
- **Recommended:** `summary` (one line) · `updated`.
- Desk-specific extras are fine — "to the extent reasonable," not a rigid schema. This core is the
  shared minimum, and it satisfies the repo-meta-structure PLANS frontmatter check.

## The vault rule (why this map exists)

The Obsidian vault was shared with the strategy desk as a **brainstorm-notes** scratchpad. It was
never meant to hold governance. Decisions, engineering specs, test-plans, and briefings accreted
there by accident and became an invisible third planning surface. Going forward:

- **The vault holds `1_Journal/` (brainstorm) only.** Nothing direction-setting lives there.
- A decision made anywhere (including a vault note or a chat) is not "recorded" until it lands a
  **CANON entry or an ADR**. A vault jotting is an input, never the record.
- Execution (issues, plans) lives in this repo; **numbers live in the board**, and docs point to
  it as-of a date rather than committing counts to flat files.

## Precedence (when surfaces disagree)

1. **CANON** wins on decisions; `docs/CHARTER.md` is its repo-local summary.
2. **The board** wins on work state (status, priority, milestone).
3. **This repo's `_meta/plans/`** wins on execution detail (acceptance criteria, live counts,
   what actually shipped) — it re-verifies against source and is the most current surface.
4. The vault wins on nothing — it is inputs, not records.
