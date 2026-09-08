# agents

Two families live here. The **atelier delegation roles** (`scout`, `builder`, `reviewer`,
`code-reviewer`, `manager`) are generic: any skill can dispatch them at any layer. `scout`,
`builder`, `reviewer`, and `code-reviewer` sit on the **execution layer**, each taking one
bounded brief and reporting back; `manager` sits on the **management layer**, owning a wave
or a coupled chain and driving it with its own workers. The **strategy layer** is the session
itself (`strategist`), which is never a spawned agent.

The **bundle-specific agents** (`rig-builder`, `pb-builder`, `pb-reviewer`,
`pocketbase-security-auditor`) are the opposite: each is bound to one bundle's subject matter
and its access model, and is dispatched by that bundle's skills rather than by the delegation
router.

The model below is each role's default; the dispatcher overrides it per call when a
slice's difficulty warrants a different tier.

| Role | Default model | Dispatch override | Use for |
|---|---|---|---|
| `scout` | haiku | sonnet, for cross-file synthesis | Read-only recon — locate a definition, confirm presence/absence, inventory a scope, or reconcile evidence across files. |
| `builder` | sonnet | opus, for coupled or expensive-to-unwind slices | Scoped implementation inside an owned file list against explicit acceptance criteria. |
| `reviewer` | opus | always premium; no override | Adversarial, report-only verification that re-derives each claim from its cited source and re-runs its commands. |
| `code-reviewer` | sonnet | opus, for a large or unfamiliar change | Report-only quality pass over code already written — names over-engineering, needless abstraction, and complexity, and shows the simpler form with a before/after. Distinct from `reviewer`, which verifies correctness rather than shape. |
| `manager` | opus | always premium; no override | Owns a wave or a coupled chain end to end: briefs, sequences, and verifies its own workers, then reports one proof package upward. |
| `rig-builder` | sonnet | opus, when the artifact has no compiler and the checker must be designed | Turning a written contract into one gate command, proving it green *and* red, and reporting a measured baseline. |
| `pb-builder` | sonnet | opus, for a coupled schema-and-rules change | Scoped PocketBase backend implementation, carrying the migration, hook, and API-rule laws so a brief does not restate them. Boots its own clean-room server for every probe. |
| `pb-reviewer` | opus | always premium; no override | Adversarial verification of a PocketBase claim, re-derived from its cited source and re-run in the reviewer's own clean room. Never edits. |
| `pocketbase-security-auditor` | opus | always premium; no override | The PocketBase authorization surface — collection rules, custom routes, hooks, realtime subscriptions, relation scoping, role boundaries — audited with code evidence and live-server evidence kept apart. Never edits. |

**Never swap `builder` for `rig-builder`:** `builder` implements until the acceptance
criteria pass; `rig-builder` measures the baseline and must not fix it, because a baseline
taken after remediation is worthless.

## Install

The delegation roles ship in `atelier`; each bundle-specific agent ships in the bundle it
belongs to — `rig-builder` in `code-desk` and the three
PocketBase agents in `pocketbase`.

```
claude plugin install atelier@dotfiles-agents
claude plugin install code-desk@dotfiles-agents
claude plugin install pocketbase@dotfiles-agents
```
