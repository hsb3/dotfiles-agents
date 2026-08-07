# plugin-feedback-worker

Gives every dispatched worker the tier rule for reporting a defect in a plugin **from this
marketplace**, so the rule arrives with the worker instead of depending on the dispatching
session restating it in each brief. A worker MAY file a bug directly — the bar is objective,
*observed behavior contradicts the plugin's own stated contract*. A worker MUST NOT file a
feature request: the why has to be tied to a real limitation, which is its dispatcher's
judgment call, so the worker drafts one with `--draft` and hands it up.

A defect in a plugin from another marketplace does not go through this reporter at all: it
files into the marketplace it shipped from, so that report belongs in that project's own
tracker.

Its companion is `plugin-feedback-session`, which tells the primary session it may file
either kind, and which carries the reporter both hooks point at.

## When it fires

Every subagent start (`SubagentStart`). No cold-start gate: the event carries no `source`,
and every dispatch is a fresh worker that was told nothing.

## Configuration

| Env var | Default | Meaning |
|---|---|---|
| `PLUGIN_FEEDBACK_DISABLED` | unset | Any non-empty value stands the reminder down |
| `CLAUDE_PLUGIN_ROOT` | set by Claude Code | Anchor for the reporter path; falls back to a sibling-derived one |

Stateless: no ledger, no state file, writes nothing anywhere, and fails open on every
error path.

## Install

```
claude plugin install plugin-feedback@dotfiles-agents
```
