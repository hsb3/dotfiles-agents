# layer-cycle

Drives a module through create → evaluate → refine cycles until convergence or budget
exhaustion, translating findings into scoped fix briefs — the orchestrator that owns
the contract, the rubric, and the cycle budget.

## When it triggers

Use it when asked to "run the cycle", take a module through review and refinement, or
iterate a module against a contract. The evaluate step scales to the diff: a spot-check for
trivial diffs, a single adversarial reviewer for bounded ones, rubric-panel reserved for
module-scale or contested work. The refine step companions deletion-pass, dispatched as a
discrete worker brief.

## Install

```
claude plugin install atelier@dotfiles-agents
```

Ships in the atelier bundle (not standalone) — pairs with rubric-panel and deletion-pass,
both also in the bundle.
