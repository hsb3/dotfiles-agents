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

## Templates

`assets/templates/` carries two files you copy into the fork and fill the `{{PLACEHOLDERS}}`
in: `upstream-digest.sh` (the triage digest) and `upstream-check.yml` (the monthly workflow
that runs it and opens an `upstream-review` issue).

Both name the upstream tracking ref by its **full refname**, `refs/remotes/upstream/<branch>`.
`git rev-parse` resolves `refs/tags/<name>` and `refs/heads/<name>` before
`refs/remotes/<name>`, so a local ref called `upstream/main` in the consuming repo would
silently become the digest's endpoint. The short form is kept where it is read rather than
resolved — the range echoed into the issue body, and the prose in this skill. The local
mirror branch (`upstream-<branch>`, full tier) is a genuine local branch and stays short.

## Install

```
claude plugin install solo-skills@dotfiles-agents
```

Ships in the `solo-skills` bundle.
