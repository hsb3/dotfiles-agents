# deletion-pass

Simplifies a module to irreducible against its contract — removes or collapses every line
that cannot name the commitment it keeps, without changing observable behavior, and reports
what it learned.

## When it triggers

Use it to simplify or tighten a module against its spec, to produce a dry-run deletion
report before committing to edits, or when invoked by layer-cycle after a build or fix pass
to strip noise the prior pass introduced.

## Install

```
claude plugin install atelier@dotfiles-agents
```

Ships in the `atelier` bundle — layer-cycle invokes it, alongside
comment-hygiene, as the refine step once evaluation surfaces findings.
