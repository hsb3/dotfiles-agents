# commands

The one-shot instructions an operator types or hands to an agent. A skill is knowledge a
model reaches for; a command is a thing you ask to be *done*
([decision-010](../../backlog/decisions/decision-010%20-%20Commands-become-a-fourth-primitive-type.md)).
Each is one `.md` with frontmatter, named by its filename, and reachable as
`/<plugin>:<filename>`.

| Command | Invocation | Does |
|---|---|---|
| `activate` | `/atelier:activate` | Arms atelier in a project: creates `.claude/atelier.local.md` if missing, then reports what each hook actually resolved, naming any key that is present but silently doing nothing. |

**A command stays thin.** It loads the skill that holds the procedure and drives it; it
never restates the procedure. Two copies of a procedure is how the shipped schema drifted
from the one it was copied from, which is the failure this family was introduced under.

## Naming: never reuse a skill name from the same plugin

Skills and commands share one dispatch namespace, and a command **silently replaces** a
same-named skill — no error, no warning, `claude plugin validate --strict` passes, and
`claude plugin details` lists the name twice without comment. The skill becomes
unreachable by both `/<plugin>:<name>` and the Skill tool, and its description stops
reaching the model, so its activation trigger dies too. Collision is exact string equality
on the full `<plugin>:<name>`, so any other name is clean. `activate` is deliberately not
`activation`.

## Testing one locally

Do not sideload the assembly directly — `claude --plugin-dir plugins/<id>` loads **zero**
commands from it. The skill loader admits symlinks and the command loader does not, so
every per-file symlink under `plugins/<id>/commands/` is skipped without a warning.
Dereference first, which is also exactly what the publish workflow lifts and what an
installed user receives:

```bash
cp -RL plugins/atelier /tmp/atelier-deref
printf '/atelier:activate' | claude -p --plugin-dir /tmp/atelier-deref
```

Confirm the load rather than trusting the output — a model with `Skill` and `Bash` will
improvise a plausible answer for a command that never loaded. Add `--debug-file /tmp/x.log`
and check `Total plugin commands loaded:` is not `0`.
