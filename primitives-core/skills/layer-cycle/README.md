# layer-cycle

Drives a module through create → evaluate → refine cycles until convergence or budget
exhaustion, translating panel findings into scoped fix briefs — the orchestrator that owns
the contract, the rubric, and the cycle budget.

## When it triggers

Use it when asked to "run the cycle", take a module through review and refinement, or
iterate a module against a contract. It companions rubric-panel for the evaluate step and
deletion-pass for the refine step, dispatching each as a discrete worker brief.

## Install

```
claude plugin install foreman-kit@dotfiles-agents
```

Ships in the foreman-kit bundle (not standalone) — pairs with rubric-panel and deletion-pass,
both also in the bundle.
