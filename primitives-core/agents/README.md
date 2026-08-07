# agents

The delegation roles the atelier skills dispatch for scoped work. `scout`, `builder`,
and `reviewer` sit on the **execution layer**: each takes one bounded brief and reports
back. `manager` sits on the **management layer**, owning a wave or a coupled chain and
driving it with its own workers. The **strategy layer** is the session itself
(`strategist`), which is never a spawned agent.

The model below is each role's default; the dispatcher overrides it per call when a
slice's difficulty warrants a different tier.

| Role | Default model | Dispatch override | Use for |
|---|---|---|---|
| `scout` | haiku | sonnet, for cross-file synthesis | Read-only recon — locate a definition, confirm presence/absence, inventory a scope, or reconcile evidence across files. |
| `builder` | sonnet | opus, for coupled or expensive-to-unwind slices | Scoped implementation inside an owned file list against explicit acceptance criteria. |
| `reviewer` | opus | always premium; no override | Adversarial, report-only verification that re-derives each claim from its cited source and re-runs its commands. |
| `manager` | opus | always premium; no override | Owns a wave or a coupled chain end to end: briefs, sequences, and verifies its own workers, then reports one proof package upward. |

## Install

```
claude plugin install atelier@dotfiles-agents
```
