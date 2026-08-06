## What happens

No skill from `foreman-kit` reaches a session, even though the plugin is enabled,
its content is materialized correctly, and its hooks are running.

Reproduced 2026-08-06 from two unrelated working directories:

```
$ cd ~/Developer && claude -p "List the exact names of every skill available to you, comma-separated, nothing else." --model haiku
dataviz, update-config, keybindings-help, simplify, fewer-permission-prompts, loop, schedule, claude-api, run, init, review, security-review

$ cd ~/Developer && claude -p "Answer with a bare list: for each of these skill names say name=yes if it is available to you via the Skill tool and name=no otherwise — foreman, waves, handoff, rubric-panel, deletion-pass, layer-cycle, dataviz." --model haiku
foreman=no
waves=no
handoff=no
rubric-panel=no
deletion-pass=no
layer-cycle=no
dataviz=yes
```

`dataviz` — a standalone one-skill plugin from this same marketplace — loads.
Every foreman-kit skill is absent. The same appears to hold for `code-desk`:
none of `board-triage`, `comms`, `planning-desk`, `dev-focus`, `project-memory`,
etc. surface either, while that plugin is also enabled. The pattern so far is
that multi-skill bundles fail and one-skill standalones work, but that is an
observation from two bundles, not a confirmed rule.

What is *not* the cause, checked:

- **Enablement** — `claude plugin list` reports `foreman-kit@dotfiles-agents` v0.7.1
  `enabled`, and `~/.claude/settings.json` has `"foreman-kit@dotfiles-agents": true`.
- **Publish/materialization** — `origin/main` carries `plugins/foreman-kit/skills/{foreman,waves,handoff,rubric-panel,deletion-pass,layer-cycle}` as real trees (mode 040000, not dangling symlinks); the marketplace clone and the 0.7.1 cache both contain all six `SKILL.md` files as real files.
- **Manifest validity** — every `.json` under the cached plugin parses, including `hooks/hooks.json` and `.claude-plugin/plugin.json` (name `foreman-kit`, version `0.7.1`).
- **Plugin load itself** — the cache dir carries live `.in_use/<pid>` markers, i.e. sessions *are* attached to the plugin, and its hooks fire.
- **Skill frontmatter shape** — all six declare `name` matching their directory; descriptions run 309–837 chars, under `dataviz`'s working 903.

One real defect found while checking, possibly unrelated to the loading failure:
`layer-cycle`'s frontmatter is **not valid YAML**. Its unquoted description
contains `Companions: rubric-panel (evaluate), deletion-pass (refine).` — the
inline `: ` makes a strict parser read a mapping key and fail:

```
$ python3 -c "import yaml;yaml.safe_load(open('.../skills/layer-cycle/SKILL.md').read().split('---')[1])"
yaml.scanner.ScannerError: mapping values are not allowed here
  in "<unicode string>", line 3, column 292
```

Claude Code's own parser evidently tolerates it — the identical file loads fine
as a project-local skill — but it should be quoted regardless, and a strict
parser anywhere in the publish path would choke on it.

## Expected

With `foreman-kit@dotfiles-agents` enabled, all six of its skills are listed as
available to a session, the same way `dataviz` is.

## Done when

- `cd ~/Developer && claude -p "..."` (the probe above) reports `foreman=yes`,
  `waves=yes`, `handoff=yes`, `rubric-panel=yes`, `deletion-pass=yes`,
  `layer-cycle=yes`.
- The same probe passes for at least one other multi-skill bundle (`code-desk`),
  confirming the fix is not foreman-kit-specific.
- `layer-cycle`'s description is quoted and
  `python3 -c "import yaml,sys;yaml.safe_load(open(p).read().split('---')[1])"`
  parses every distributed `SKILL.md` frontmatter without error — worth wiring
  into `make ci` as a gate so this class of breakage cannot ship again.

## Context

- Blocks `EVALS/lab-01-package-inventory` TASK-12 (retire the in-repo prototypes
  of `rubric-panel` / `deletion-pass` / `layer-cycle` in favour of the distributed
  copies). Deleting them today would remove three working skills and gain nothing.
- Blocks the verification step of task-29 (promote the `lab-setup` skill), since
  whatever bundle homes it inherits this problem.
- The trio shipped in #235 (kit 0.7.0); the publish pipeline it depends on was
  repaired in #237 and is confirmed working — `origin/main` content is correct,
  so this is a load-side problem, not a publish-side one.
