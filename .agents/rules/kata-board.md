# kata board conventions (project dotfiles-agents)

The board is the tracker (see AGENTS.md "Task tracking"). This file covers how it is **organized**.

## Shape: every open card has one root

Walk parent links up from any open card and you reach exactly one of these:

| root | role | priority |
|---|---|---|
| a **wave milestone** (`Wave N: <theme>`) | scheduled work, in launch order | wave order: next wave 1, the one after 2 |
| **Feature backlog** | new capability that no wave has pulled in yet | 3 |
| **Hygiene backlog** | conventions, docs truth, tooling nits, CI shape, pending decisions | 3 |
| **Session Handoff** (`4w08`), **WAVE PLAN** (`4dvk`) | standing documents; they hold no work cards | 0 / 1 |

- An existing epic moves as a unit: it goes under a root and keeps its children. A card sits
  directly under a root only when no epic fits.
- **Scheduling means re-parenting.** Pull a card into a wave by moving it under that wave's
  milestone. Push it back to a backlog, with a comment giving the reason, when it slips.
- Parents are containment only. Real prerequisites use `--blocks`/`--blocked-by`.
- A wave milestone closes when every child is closed or re-parented, and dev is green and
  published. A backlog stays open as a container.
- A new card is filed under its root at creation (`--parent`). Never leave one orphaned.

## Labels

The vocabulary is [`decision-023`](../../docs/decisions/decisions-023-kata-labels-are-the-triage-system-and-title-prefixes-are-not.md),
declared machine-readably in `primitives-core/skills/board-triage/scripts/core-labels.txt`. That
record is the copy to change. Day to day:

- Every open card carries exactly one `area:*` and exactly one `type:*`. Milestones and
  backlogs also carry `epic`.
- Titles carry **no prefix of any kind**. Grouping lives in labels and parents, where a query can
  reach it.
- A new area is added only for a genuine new domain, never for a single card.
- Board labels do NOT propagate to GitHub, and GitHub's closed set (decision-016) is a
  subset of the core. `make labels` proves it.

## Grooming bias

- Close whatever is done, superseded or stale. A card that matters can be filed again. Closing
  a GitHub mirror card also means closing its GitHub issue by hand.
- Never edit a mirror's title, body, labels or comments, because the sync owns them. Parent and
  priority are board-side, but the sync can reset priority when the issue changes.
- `make board-health` must read clean after a grooming pass.
