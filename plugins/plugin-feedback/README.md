# plugin-feedback

A session that hits a defect in a plugin it is using usually works around it and moves on,
because filing the report is friction and nobody said reports were welcome. This plugin
removes both halves of that: reminder hooks say reports are welcome, and a reporter script
files one to a fixed shape so an agent never free-hands `gh issue create`.

Install it alongside whatever else you run from this marketplace. It ships on its own
rather than folded into every other plugin on purpose: Claude Code deduplicates a hook
handler only across settings-file layers, never across plugins, so a copy in each plugin
would fire the same nudge once per installed plugin.

```
claude plugin install plugin-feedback@dotfiles-agents
```

## What it does

| Hook | Fires | Says |
|---|---|---|
| [`plugin-feedback-session`](hooks/plugin-feedback-session/README.md) | session start, cold only (`startup`/`clear`) | the primary session may file either a bug or a feature request |
| [`plugin-feedback-worker`](hooks/plugin-feedback-worker/README.md) | every subagent start | a worker may file a bug directly, but drafts a feature request for its dispatcher |

Both hooks inject a short pointer, not the template. The template lives in the reporter,
`hooks/plugin-feedback-session/report_issue.py`, which both hooks name by absolute path.

## The tier rule

A **bug** may be filed by anyone, worker included, because the bar is objective: *observed
behavior contradicts the plugin's own stated contract*. Checking it needs no judgment, only
the plugin's README.

A **feature request** needs a why tied to a limitation actually hit, which is a judgment
call a worker inside one slice is not positioned to make. So a worker runs the reporter with
`--draft`, prints the body, and hands it to its dispatcher to review and file.

## Filing one

```sh
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/plugin-feedback-session/report_issue.py" bug \
  --plugin atelier --plugin-version 0.8.0 \
  --summary "worker covenant never injected under strict" \
  --symptom "No additionalContext arrives at subagent start." \
  --repro "Set enforce: strict, dispatch any subagent." \
  --contract "Its README states strict injects the covenant plus the tool-layer clause."
```

Add `--draft` to print the report instead of filing it. `feature` swaps `--contract` for
`--limitation`. Everything else (project, date, severity, workaround, suggested fix) has a
default or is optional; `--help` lists them.

## Configuration

| Env var | Default | Meaning |
|---|---|---|
| `PLUGIN_FEEDBACK_REPO` | the reporting plugin's manifest `repository` | Where issues are filed, as `owner/name` |
| `PLUGIN_FEEDBACK_LABEL_BUG` | `type:fix` | Label applied to a bug |
| `PLUGIN_FEEDBACK_LABEL_FEATURE` | `type:feature` | Label applied to a feature request |
| `PLUGIN_FEEDBACK_DISABLED` | unset | Any non-empty value stands both reminders down |

No repo is hardcoded. With neither the variable nor a manifest `repository` resolvable, the
reporter refuses and names the variable rather than guessing a target.

## Honest scope

It does not triage, deduplicate, or search for an existing report before filing, and it does
not judge whether a report is worth filing. It has no opinion on the receiving repo's
workflow beyond one label. It cannot make a session notice a defect it did not notice; it
only makes reporting one cheap once it has.
