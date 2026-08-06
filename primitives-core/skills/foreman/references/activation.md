# Per-project activation — `.claude/atelier.local.md`

The plugin's enforcement layer is off until a project turns it on. One file controls it:
`.claude/atelier.local.md` in the project root (gitignored by convention — the harness attaches no
behavior to this file; atelier's skill and hooks read it themselves, per call, so editing it needs
no restart).

```markdown
---
effort: deep          # optional: force the effort level (Step 0)
enforce: strict       # off (default when absent) | advisory | strict
protected:            # fnmatch patterns, project-relative; * crosses /
  - Makefile
  - .github/workflows/*
  - "*.config.js"
---
```

| `enforce` | `worker-context` (SubagentStart) | `config-custody` (PreToolUse) |
|---|---|---|
| absent / `off` | silent | silent |
| `advisory` | injects the worker covenant into every subagent | logs would-deny rows to `logs/config-custody.jsonl`; never blocks |
| `strict` | injects, naming the tool-layer block | denies subagent edits to `protected:` paths, with an escalation-shaped reason |

## Design commitments

- **The main session is never restricted.** Custody is role-scoped through the documented
  `agent_id` hook payload field, present only inside subagents. The foreman owns config and git;
  no mode changes that.
- **No command matching.** Path custody is fnmatch against a list the project wrote — Step 3's
  ownership map made machine-readable. Mutating git by workers stays advisory (the injected
  covenant plus the reconciliation check in `briefs.md`), because blocking it would require
  matching Bash command strings, which is brittle by design. A project that wants a hard git
  block can add `permissions.deny` rules (for example `Bash(git push *)`) to its own
  settings.json — noting that permission rules are not role-scoped and bind the main session too.
- **Fail-open.** A missing, malformed, or unrecognized activation file means `off`. A hook error
  can never produce a deny.
- **Escape hatches.** Drop to `advisory` (or remove the key) to stop blocking everywhere; lift a
  single pattern to hand one file's ownership to a wave. The deny message itself routes the
  worker to the doctrinally correct move — escalate, never route around.
- **False-positive story.** A brief that legitimately grants config ownership hits the deny once;
  the worker reports the conflict; the foreman lifts the pattern for that wave or makes the edit
  itself. One bounced tool call is the entire cost.
- **Graduation path.** Run `advisory` first: the would-deny ledger shows exactly what `strict`
  would have blocked. Move to `strict` when the log shows no false positives.

The custody model is `[untested]` (see `provenance.md`): the mechanism is proven by fixtures and
an adversarial matrix, but no real project has run under `strict` yet.
