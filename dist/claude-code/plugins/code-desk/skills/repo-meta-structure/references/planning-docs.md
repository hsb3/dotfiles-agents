# Planning-doc frontmatter and communication-package intake

The conventions for documents on the code planning desk (`_meta/plans/`). The desk workflow
itself (authoring issue bodies, build plans, the governance toolkit) is the sibling
`planning-desk` skill; this file owns only the **document contract**: the frontmatter schema
and the intake location/types for communication packages.

## Frontmatter schema

Every planning doc in `_meta/plans/` (recursive, including `inbox/`) carries this
frontmatter. Out of scope: `README.md` (the desk index), files starting with `_` (desk
config), `_utils/` (scripts), and `issue-body.md` files. Staged `issue-body.md` files are
exempt from the frontmatter schema: a staged issue body is the raw publishable GitHub
body, kept byte-identical to the live issue (owner ruling 2026-07-02).

```yaml
---
title: ""
type: reference|spec|canon
status: draft
created: YYYY-MM-DD
purpose: ""
notes: ""
---
```

| Field | Meaning |
|---|---|
| `title` | Human title of the doc |
| `type` | One of the vocabulary below |
| `status` | Lifecycle, starting at `draft` |
| `created` | `YYYY-MM-DD` |
| `purpose` | One line: why this doc exists (the audit flags a missing `purpose`) |
| `notes` | Freeform; may be empty but the key is present |

The machine checks are rows `PLANS-01` … `PLANS-06` in [`checklist.md`](checklist.md).

## `type` vocabulary

| Value | Used for | Lands in |
|---|---|---|
| `reference` | Reference material supporting plans | `_meta/plans/` |
| `spec` | A spec / build plan | `_meta/plans/` |
| `canon` | Canonical position a plan set relies on | `_meta/plans/` |
| `proposed-issue` | Communication package: a proposed GitHub issue | `_meta/plans/inbox/` |
| `reprioritization-memo` | Communication package: a priorities re-evaluation memo | `_meta/plans/inbox/` |

The two intake values are **extensions of the same schema** — not a separate schema. A
communication package is an ordinary planning doc whose `type` marks it as inbound.

## Communication-package intake — `_meta/plans/inbox/`

Per the strategy-desk-boundary decision, the **strategy desk** (the cowork folder outside
the repo) never touches GitHub and never writes code. Its only interface to the code world
is **communication packages** — e.g. "here is a proposed issue", "priorities have been
re-evaluated; use this memo to reprioritize the board" — sent to the **code planning desk**
in formats this standard defines. The code planning desk (and the maintainer) execute; the
strategy desk proposes.

- **Location:** packages land in `_meta/plans/inbox/`.
- **Format:** the planning-doc frontmatter schema above, with `type: proposed-issue` or
  `type: reprioritization-memo`.
- **Tracking:** `_meta/` is tracked by default (ADR-0006), so the inbox is covered — packages
  survive into fresh clones and worktrees with no extra rule (checklist row
  `IGNORE-03`).
- **Not HANDOFF:** `_meta/HANDOFF.md` is *intra-desk* continuity (session → session within
  one desk/repo); communication packages are the *cross-desk* channel (strategy desk → code
  planning desk). A strategy-desk deliverable never lands as a HANDOFF update.

Rationale for folding intake into `_meta/plans/` rather than a new top-level
`_meta/communications/`: the code planning desk already owns `_meta/plans/` and is the sole
consumer; a separate directory would add taxonomy surface for one inbound flow.
