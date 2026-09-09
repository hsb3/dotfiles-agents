# comment-hygiene

Strips history and commentary out of source comments before work lands — harvests the
reasoning onto its tracker item first, then keeps only what a reader would break something
without.

## When it triggers

Use it before a PR or a milestone commit, when a file's comments read as narrative rather
than as facts about the system, or when invoked by layer-cycle's refine phase. Writing
scratch commentary while building is expected; this is the cleanup step that runs before the
work lands, not a ban on thinking in comments.

## Install

```
claude plugin install atelier@dotfiles-agents
```

Ships in the atelier bundle, where layer-cycle invokes it as part of the refine phase.
