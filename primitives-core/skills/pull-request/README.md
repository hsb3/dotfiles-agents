# pull-request

A green check is not a finished PR. Automated reviewers post their findings on a surface
the check status never reflects, so a merge taken on `gh pr checks` alone can ship over
unread comments. This reads all three surfaces — inline review comments, review and
summary bodies, gate status — sorts each finding into actionable or pre-existing, and
makes you name the deferred set instead of quietly dropping it.

## When it triggers

Right after opening a PR and watching CI go green; when asked to "check the PR comments",
"address the review feedback", "what did the review bots say", or "is this PR ready to
merge". The `/pr-findings` command drives it against a PR number, or against the current
branch's PR when given none — the open one, since a branch whose PR already merged would
otherwise hand you its stale threads.

## Install

```
claude plugin install code-desk@dotfiles-agents
claude plugin install solo-skills@dotfiles-agents
```

`code-desk` also carries the `/pr-findings` command that drives it; the `solo-skills`
bundle ships the skill alone.
