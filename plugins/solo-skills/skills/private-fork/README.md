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

Everything in `assets/templates/` is copied into the fork and has its `{{PLACEHOLDERS}}`
filled: the two divergence ledgers (`FORK_CHANGES.md` light tier, `fork-customizations.md`
full tier), the review log, the digest script, and the monthly workflow that runs it.

**Every upstream ref they resolve is spelled in full**, `refs/remotes/upstream/<branch>` —
in the scripts, in the workflow, and in the copy-paste commands under `references/`.
`git rev-parse` resolves `refs/tags/<name>` and `refs/heads/<name>` before
`refs/remotes/<name>`, and a bare `refs/remotes/upstream/main` that does not exist falls
through to `refs/heads/refs/remotes/upstream/main`, so a local ref of either name in the
consuming fork silently redirects a merge or a digest. It bites hardest on the mirror
advance (`git merge --ff-only`), because the mirror is the digest's own watermark baseline:
corrupt it and the next digest reports a correct-looking range over the wrong history.

Short forms are kept only where a ref is *read* rather than resolved — the range echoed
into the issue body, the tables naming the remote layout. Two things that look short are
not defects: the local mirror branch `upstream-<branch>` and the topic-branch prefix
`fork/<topic>` are both genuine local branches.

## Install

```
claude plugin install solo-skills@dotfiles-agents
```

Ships in the `solo-skills` bundle.
