# private-fork

Stand up and operate a private fork (private mirror) of an upstream open-source repo:
mirror + remotes setup, a delete-vs-disable rubric for unwanted upstream content, a
divergence ledger, and the recurring upstream review/merge cycle.

## When it triggers

Use it when you want to "set up a private fork", "mirror an upstream repo", "sync/merge
upstream", or "run an upstream review"; when deciding delete-vs-disable for unwanted upstream
content or weighing merge tax; or when working in a repo that already has an `upstream`
remote and a divergence file (`FORK_CHANGES.md` / `fork-customizations.md`). Not for an
ordinary contribute-back GitHub fork whose changes are destined for upstream PRs.

## Install

```
claude plugin install private-fork@dotfiles-agents
```

Also ships as a member of the `code-desk` bundle.
