# rubric-panel

Scores one or more code artifacts against an anchored rubric using a persona-diverse judge
panel — produces dimension scores plus findings classified as defect, noise, spec-hole, or
undeclared-commitment.

## When it triggers

Use it when asked to evaluate, score, judge, or compare solutions or modules, or when
invoked by layer-cycle as its evaluate step. Judges run read-only against a supplied rubric
and contract; each finding must cite concrete code.

## Install

```
claude plugin install foreman-kit@dotfiles-agents
```

Ships in the foreman-kit bundle (not standalone) — layer-cycle invokes it as the evaluate
step, ahead of deletion-pass's refine step.
