# Repo gotchas — the traps that have already bitten

_Repo-local field knowledge. Provenance: distilled out of the session handoff 2026-08-13, where
it had accumulated over ~20 sessions. Only traps specific to THIS repo belong here. Rules that
consumers need travel with the primitive that ships them; anything about publishing is in the
`publish-to-main` skill, the contributor loop is in [`../.github/CONTRIBUTING.md`](../.github/CONTRIBUTING.md),
and the standing law is [AGENTS.md](../AGENTS.md), hot-loaded into every session._

## Reading the gates

- **`make ci`'s `✗` lines are passing tests' own output. Judge by exit code only.** Fixture runs
  print "1 primitives"; the real repo says 59. This trap produced a false "3 pre-existing
  failures" handoff claim on 2026-08-11 — re-run before inheriting any red-tree claim.
- **`make ci` is not the whole gate.** Two guards run in CI only, both because they need
  network where `make ci` is offline-and-zero-install by design. Run both by hand before
  assuming green:
  `scripts/check_version_bump.py` (changed published bytes must ship under a moved version —
  it caught `solo-skills` shipping two new skills under an unmoved 0.1.8 on 2026-08-20), and
  `scripts/check_vendored_drift.py` / `make vendored-drift` (every `origin: vendored` `base/`
  still matches its pinned upstream ref).
- **`ci.yml` fires on `pull_request` ONLY.** A direct push to `dev` gets ZERO CI, and the owner's
  waiver means `remote: Bypassed rule violations` is expected on the handful of paths it covers.
  Run `make ci` locally first — nothing else will. Code still goes through a PR.
- **CI job names are frozen.** Branch protection pins checks by NAME, so a new gate rides an
  existing job rather than adding one.
- **`flow.yaml` is load-bearing.** `make flow` fails on any unhomed top-level path; regenerate the
  rendered doc with `scripts/check_flow.py --write-doc`. The hand-maintained table below the
  generated block in `FLOW.md` is separately stale.
- **`comment-hygiene-gate` has real subjects here** (~41 findings across `evals/`,
  `externals.yaml`, workflow YAML). It firing on a commit is the gate working, not a regression.

## Method

- **A heuristic that passes its tests can still be mostly wrong — measure it against a corpus.**
  Replay over git history, and use a stdlib parser as the oracle where one exists. Proved twice:
  `comment-hygiene-gate` (replay found 79% precision) and the kaneo importer (its tests used a
  marker dialect no real `Backlog.md` ever wrote). **A gate can have zero real subjects and stay
  green** — a deliberate forward-guard must say so in its docstring.
- **DERIVE a set, never consume a recorded one.** A card or report that hands you an inventory is
  offering a hypothesis (TASK-043: recorded 27, derived 30).
- **Probe the harness instead of reasoning about it.** Headless run in a throwaway repo, prompt on
  **stdin**:
  ```sh
  printf '<prompt>' | claude -p --settings <f> --model haiku \
    --permission-mode acceptEdits --allowedTools "Agent,Bash,Read"
  ```
  For undocumented schemas, `strings ~/.local/share/claude/versions/<v>`. Issue #297's false
  conclusion came from inferring via a YAML library instead.
- **Run `git worktree list` at session start.** A stale worktree hides finished work while
  `git status` stays clean.

## Editing this repo

- **`git diff` appends a TAB to `+++ b/<path>` when the path contains spaces** — the
  `docs/decisions/*.md` filenames do. Split on `\t` before using the name.
- **No unguarded counts in prose or metadata** (owner rule). A count needs a gate behind it, or
  phrasing that survives growth.
- A new plugin is `plugins/<id>/` plus a hand-authored `marketplace.json` entry. The
  `pptx-themes` README keeps its Anthropic attribution section — never drop it.
- **Never mutate a second repo's git history.** Removing a marketplace via `/plugin` deletes its
  entries from the tracked `enabledPlugins` — correct here, worth knowing elsewhere.
