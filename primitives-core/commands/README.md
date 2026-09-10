# commands

The one-shot instructions an operator types or hands to an agent. A skill is knowledge a
model reaches for; a command is a thing you ask to be *done*
([decision-010](../../docs/decisions/decision-010%20-%20Commands-become-a-fourth-primitive-type.md)).
Each is one `.md` with frontmatter, named by its filename, and reachable as
`/<plugin>:<filename>`.

| Command | Invocation | Does |
|---|---|---|
| `prepare-compact` | `/atelier:prepare-compact` | Invokes `compact-handoff`: verify the persisted handoff and prepare a KEEP/DROP prompt before manual compaction. Its distinct name keeps the skill reachable. |
| `activate` | `/atelier:activate` | Arms atelier in a project: creates `.claude/atelier.local.md` if missing, then reports what each hook actually resolved, naming any key that is present but silently doing nothing. |
| `pr-findings` | `/code-desk:pr-findings [<n>]` | Loads `pull-request` and drives it over one PR — the current branch's open PR when no number is given. Reports each review finding as actionable or as pre-existing rot it names rather than drops. |

**A command stays thin.** It loads the skill that holds the procedure and drives it; it
never restates the procedure. Two copies of a procedure is how the shipped schema drifted
from the one it was copied from, which is the failure this family was introduced under.

## Naming: never reuse a skill name from the same plugin

Skills and commands share one dispatch namespace, and a command **silently replaces** a
same-named skill — no error, no warning, and `claude plugin validate --strict` reports no
collision. The skill becomes unreachable by both `/<plugin>:<name>` and the Skill tool: ask
for the skill by name and the command's body comes back instead.

That is worse than the skill simply being dropped. The skill still loads and its description
still advertises it, so the model is invited by the skill and lands on the command. Collision
is exact string equality on the full `<plugin>:<name>`, so any other name is clean.
`activate` is deliberately not `activation`.

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

Atelier policy selection follows configured agent directories, using `.agents` for
multiple agents; setup migrates identical policies safely and runtime reads stay read-only.
