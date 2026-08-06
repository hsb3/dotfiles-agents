# agents

Four delegation roles dispatched by the atelier skills for scoped work: a
read-only scout for recon, a builder for scoped implementation, an adversarial
reviewer for verification, and a lead that drives coupled chains too dependent to
flatten into parallel briefs. The model below is each role's default — the dispatcher
overrides it per call when a slice's difficulty warrants a different tier.

| Role | Default model | Dispatch override | Use for |
|---|---|---|---|
| `scout` | haiku | sonnet, for cross-file synthesis | Read-only recon — locate a definition, confirm presence/absence, inventory a scope, or reconcile evidence across files. |
| `builder` | sonnet | opus, for coupled or expensive-to-unwind slices | Scoped implementation inside an owned file list against explicit acceptance criteria. |
| `reviewer` | opus | always premium; no override | Adversarial, report-only verification that re-derives each claim from its cited source and re-runs its commands. |
| `lead` | opus | always premium; no override | The foreman's proxy for a coupled, dependent chain that can't be flattened into parallel briefs. |

## Install

```
claude plugin install atelier@dotfiles-agents
```
