---
id: decision-031
title: "_meta/ is tracked by default; targeted ignores only"
type: decision
status: accepted
created: 2026-07-13
summary: Consumer repositories track _meta by default and ignore only operations content, caches, and OS litter.
---

> **Scope clarification (2026-09-12):** [decision-008](decisions-008-repo-structure-future-state-backlog-absorbs-docs-hooks-removed.md) superseded this rule only for this repository, which removed `_meta/`. This reusable consumer policy remains active in the repo-meta templates and checklist.

# Decision 031 · `_meta/` is tracked by default; targeted ignores only

_The working desk tracks like the rest of the repo; ignoring is the exception, reserved for secrets (`operations/`), tool caches, and OS litter._

- **Provenance:** owner directive 2026-07-12 (#99); owner ruled option 2 on 2026-07-13.
- **Raised by:** #99 · `_meta/plans/meta-gitignore-policy/plan.md`

## Context

Broad `_meta/*` ignores with negations hide durable work, make gitignore ordering fragile, and re-admit litter. Three options were compared: status quo, tracked-by-default with targeted ignores, and moving operations outside `_meta/`.

## Decision

**Track `_meta/` by default; ignore only what must never publish:**

- `_meta/operations/*` holds secrets and live operations material, with `.gitkeep` negated so the directory survives a clone.
- Tool caches and OS litter remain covered by global cache and `.DS_Store` rules.

`operations/` remains inside `_meta/`; durable desk content is clone-survivable, while deliberately local scratch belongs in `operations/` or outside the repository.

## Consequences

- The broad-ignore and negation machinery is removed.
- Ignore checks prove tracked-by-default behavior and the operations/cache/litter exceptions.
- Consumers repeat a secrets scan before adopting the rule.

## Affects

`_meta/` consumers · repo-meta-structure templates and checklist · mise-en-place scaffold · planning desk.
