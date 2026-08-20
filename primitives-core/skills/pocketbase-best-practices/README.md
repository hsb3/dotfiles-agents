# pocketbase-best-practices

PocketBase design and review guidance: 63 prioritized rules across collection design, API
rules, auth, SDK usage, query performance, realtime, file handling, deployment, and
server-side extending.

## When it triggers

Designing a PocketBase schema, writing or auditing API rules, setting up auth flows,
diagnosing slow or N+1 queries, or reviewing a backend before it ships. For driving a running
instance instead, use the `pocketbase` skill in the same plugin.

## What it is

- **Authored layer** (`SKILL.md`) — routing between this skill and the operational one, plus
  **field notes**: verified findings that extend or override the vendored rules, each carrying
  the evidence that established it. Where the layer and the base disagree, the layer wins.
- **Vendored base** (`base/`) — the upstream rule set, taken **verbatim**: `base/SKILL.md`
  (category table and quick reference), 65 files in `base/rules/`, and long-form
  `base/references/`.

## Attribution

The `base/` directory is the **`pocketbase-best-practices` skill** from the
`pocketbase-skills` project, vendored verbatim:

- Source: <https://github.com/greendesertsnow/pocketbase-skills>, path
  `skills/pocketbase-best-practices`
- Pinned ref: `c573263e84a2066d0564f428dd8160e74fc54226`
- License: MIT — see `LICENSE`, retained unchanged.

The original files are kept in place and unmodified to satisfy the attribution obligation.

Do not edit `base/` — update the pin instead (a new ref, re-vendored verbatim). A hand-edit
there registers as `diverged` against the pinned ref and fails the vendored-drift gate.
Corrections belong in the authored layer's "Field notes", and upstream-worthy ones should be
reported to the upstream project.

## Install

```
claude plugin install pocketbase@dotfiles-agents
```
