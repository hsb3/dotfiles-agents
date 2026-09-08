# owner-signoff

Present a batch of decisions, approvals, or questions to the project owner as a local HTML
form in their browser instead of a wall of chat questions. The owner answers inline at
their own pace — every recommendation preselected, so agreeing with everything is one
click — and the answers land in a JSON file the session picks up the moment they submit.
Answers convert into the project's own tracker (a board issue, a GitHub issue, or a
decision record) — this skill has no tracker of its own.

## When it triggers

Use it when multiple items need the owner's input at once (sign-offs, dispositions,
priorities, open questions), when the owner asks "what do you need from me", or when they
want a summary/quiz they can react to. The skill ships a spec-driven form builder (write
a small YAML/JSON file, it validates and renders the HTML) and a one-shot localhost
server (binds 127.0.0.1 only, accepts exactly one submit, then exits), plus a download
fallback for much-later submits.

## Project override — where batch dirs live

Each sign-off gets its own dated batch dir under a batch root that defaults to
`_meta/signoff/` (so `_meta/signoff/2026-09-07-plugin-restructure/`). A project that keeps
them somewhere else says so once, with a `signoff:` key in the project-local activation
file `.claude/owner-signoff.local.md`:

```markdown
---
signoff: docs/signoff
---
```

The value is project-relative. Absent, blank, or resolving outside the project root leaves
the default in force — the override never turns the skill off. Nothing has to guess: run
`python3 <skill-dir>/scripts/build_signoff.py --batch-root` from the project root and it
prints the resolved root without building anything. This is the same project-local
frontmatter-key shape the `handoff` skill's `handoff:` key uses, so a project that already
carries one reads the other on sight.

**The server's port deliberately has no key.** `serve_signoff.py <batch-dir> [port]` already
takes the port as an optional positional argument and walks forward to the next free port
when the default (8737) is busy, so a stated preference already has somewhere to go and a
collision resolves itself. A second override mechanism for it would configure a value that
is per-run rather than per-project.

## Install

Ships inside the `solo-skills` bundle:

```
claude plugin install solo-skills@dotfiles-agents
```

Needs only `python3` (stdlib); YAML specs additionally need PyYAML, JSON specs never do.
