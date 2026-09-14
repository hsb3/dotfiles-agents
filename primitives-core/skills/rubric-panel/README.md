# rubric-panel

Scores one or more code artifacts against an anchored rubric using a persona-diverse judge
panel — produces dimension scores plus findings classified as defect, noise, spec-hole, or
undeclared-commitment.

## When it triggers

Use it when asked to score an implementation, rate a single module against a rubric, or judge
competing solutions to the same spec, or when invoked by layer-cycle as its evaluate step. For
choosing between technologies, frameworks, or vendors, use `tech-eval-research` instead. Judges
run read-only against a supplied rubric and contract; each finding must cite concrete code.

## Install

```
claude plugin install atelier@dotfiles-agents
```

Ships in the `atelier` bundle — layer-cycle's evaluate step reaches for it on module-scale or
contested work, its reserved case rather than the every-cycle default, ahead of the
deletion-pass refine step.

## Codex

Uses the same workflow with generated project roles and native worker routing. See the
[Codex distribution procedures](../delegation/references/dispatch-knobs.md#codex-distribution)
for setup, ownership-safe refresh, role names, and completion handling.
