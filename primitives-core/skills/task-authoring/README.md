# task-authoring

Write tracked work items a cold agent can actually execute. The executor has none of the
author's context, so this skill turns implicit judgment into explicit contract: scannable
`area: outcome` titles, acceptance criteria that could actually fail against today's
baseline, thresholds instead of judgment words, approval gates with a named mechanism, and
one owner per file set. The payoff is tasks that run without a round trip back to whoever
wrote them.

## When it triggers

Creating or rewriting any tracker item — a Kata issue, a GitHub issue, an
OpenSpec change — or reviewing an existing task for executability before handing it to
an agent.

## Install

```
claude plugin install mise-en-place@dotfiles-agents
```

Ships inside `mise-en-place`, whose planning desk delegates the item-body form to it rather
than restating it. The doctrine itself is tracker-agnostic and needs no configuration.
