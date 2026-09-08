# rubric-panel

Scores one or more code artifacts against an anchored rubric using a persona-diverse judge
panel — produces dimension scores plus findings classified as defect, noise, spec-hole, or
undeclared-commitment.

## When it triggers

Use it when asked to evaluate, score, judge, or compare competing implementations of the same
spec, or when invoked by layer-cycle as its evaluate step. For choosing between technologies,
frameworks, or vendors, use `tech-eval-research` instead. Judges run read-only against a
supplied rubric and contract; each finding must cite concrete code.

## Install

```
claude plugin install atelier@dotfiles-agents
claude plugin install solo-skills@dotfiles-agents
```

Ships in the `atelier` and `solo-skills` bundles — layer-cycle invokes it as the evaluate
step, ahead of deletion-pass's refine step.
