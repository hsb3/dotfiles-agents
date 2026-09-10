# Compaction prompt template

Replace each bracketed field with verified state or explicit `none`/`unknown`. Repeat
the agent and command entries as needed. Preserve exact values; no abbreviated IDs.

```text
KEEP VERBATIM
Session: [runtime/version, session id, cwd, current branch]
Verified handoff: [exact card URL/id or absolute file path, readback evidence]
Active agents: [id/name, role, cwd, branch, PR URL/status, exact brief and later steering,
  current status, result/log location, next wait/resume tool and complete arguments]
Dependent background commands: [purpose, process/session/tool handles, cwd, branch,
  current status, log/result locations, prerequisite, next wait/resume tool and arguments]
Custody/activation lifts: [main checkout, exact scope, authority, reason, restoration condition]
Owner rulings this session: [exact ruling, scope, reason; unresolved decisions remain unresolved]
Open sign-off forms: [path/URL, response file, pending items, next response check]
Exact next action: [tool/command, arguments, target handle, prerequisite and expected result]
Continue in this same session. Preserve original handles and live processes. Verify status
before resuming; do not restart, replace, or terminate dependent work to simplify the summary.

DROP
Raw tool output, file dumps, repeated explanations, and superseded plans. Preserve the
KEEP facts above even when they occur inside output being dropped. For other background
context read the verified handoff at [same exact pointer]. Never drop an unresolved ruling.
```
