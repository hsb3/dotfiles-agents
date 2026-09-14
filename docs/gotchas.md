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
- **`make ci` is not the whole gate.** Several guards run in CI only, because `make ci` is
  offline-and-zero-install by design and each needs something it cannot have. Run them all
  by hand before assuming green:
  `scripts/check_version_bump.py` (needs network; changed published bytes must ship under a
  moved version — it caught `solo-skills` shipping two new skills under an unmoved 0.1.8 on
  2026-08-20), `scripts/check_removals.py` (needs network; a unit published on `origin/main`
  and absent here must be declared by the commit that removed it — the deletion case the
  version-bump gate says outright it does not cover), `scripts/check_vendored_drift.py` /
  `make vendored-drift` (needs network;
  every `origin: vendored` `base/` still matches its pinned upstream ref),
  `scripts/check_manifests.py` / `make manifests` (needs the `claude` binary; runs
  `claude plugin validate --strict` over the marketplace and every assembly), and
  `scripts/check_labels.py` / `make labels` (needs `gh` + network; the repo's GitHub label
  set is a closed vocabulary per decision-016, and an extra or missing label is red).
  They all ride the `drift guards` CI job rather than getting their own, because branch
  protection pins required checks by job NAME.
- **`claude plugin validate --strict` cannot see through a symlink assembly, so the gate
  validates a dereferenced copy.** From CLI 2.1.240 the validator warns "N entries here are
  symlinks and were not read ... validate the real paths separately", and `--strict` makes
  that fatal — which fails every bundle in this repo by construction, since ADR 0017 makes
  every `plugins/<id>/` a symlink tree. `check_manifests.py` therefore `cp -RL`s into a
  tempdir (the same shape `publish.yml` builds `main` from) and validates that. Bonus: what
  gets checked is then exactly what a consumer installs.
- **The Claude Code CLI is PINNED in both workflows, and that pin is load-bearing.** An
  unpinned `npm install -g` installs `latest`. On 2026-08-22 that alone took `drift guards`
  from green to red with no repo change: local machines run 2.1.231 (the `stable` tag,
  silent about symlinks), CI installed 2.1.240 (which warns). Any gate shelling out to a
  vendored binary inherits that binary's release cadence — pin it, and bump deliberately.
- **A gate that cannot measure is red, never green** (decision-016 point 4) — a missing
  binary and an unreachable remote both exit 1, in every CI-only gate alike, with a message
  naming which failure it hit and acquitting the thing it could not measure.
- **The README-currency gate reads git history, so `drift-guards` checks out at
  `fetch-depth: 0`.** In the default depth-1 checkout every file shares one synthetic commit,
  so every unit's body and README look like the same change and the gate would pass
  vacuously; it refuses a shallow clone instead. Only that job — `entry-gate-floor` stays
  depth-1 and its test for this gate skips there, so a test asserting the live tree is
  current must never assume history exists. The decision-015 amnesty that once anchored the
  gate to the ruling's landing commit is gone (backfilled 2026-09-08): every unit with a
  tracked body is evaluated over all of history, so any body change lands red unless that
  unit's README moves with it. `skipped` in the clean line now means only a unit with no
  tracked body — in practice, one whose files are not committed yet.
- **`ci.yml` fires on `pull_request` ONLY.** A direct push to `dev` gets ZERO CI, and the owner's
  waiver means `remote: Bypassed rule violations` is expected on the handful of paths it covers.
  Run `make ci` locally first — nothing else will. Code still goes through a PR.
- **The fallback runner is same-repo PRs only.** `ci.yml`'s `runs-on` sends a job to the
  self-hosted `docker-fallback` runner only when `USE_FALLBACK_RUNNER=true` AND the PR's head
  repo is this repo; a fork PR stays on `ubuntu-latest`, because a self-hosted job runs the
  PR's code on the owner's Mac. That clause guards only our own routing: `pull_request` runs
  the PR's copy of the workflow, so a fork can hardcode the labels. While a fallback runner is
  live, approve no fork run whose diff touches `.github/`.
- **CI job names are frozen.** Branch protection pins checks by NAME, so a new gate rides an
  existing job rather than adding one.
- **`flow.yaml` is load-bearing.** `make flow` fails on any unhomed top-level path; regenerate the
  rendered doc with `scripts/check_flow.py --write-doc`. The hand-maintained table below the
  generated block in `FLOW.md` is separately stale.
- **`comment-hygiene-gate` has real subjects here** (~41 findings across `evals/`,
  `externals.yaml`, workflow YAML). It firing on a commit is the gate working, not a regression.

## Method

- **Same-size source mutation + stale bytecode = a mutant sweep that lies.** CPython validates
  `.pyc` files on mtime **and size**, so flipping `return 1` to `return 0` (identical length)
  and reverting inside the same mtime second leaves the stale bytecode valid. The tests then
  keep reporting the mutant's result against provably correct source. Observed 2026-08-22
  while mutation-testing `check_manifests.py`: the first full sweep was untrustworthy and had
  to be redone. **Clear `__pycache__` between mutants.** Also: put the restore in a `finally` —
  a sweep script that crashes before restoring leaves the tree sabotaged, and a commit taken in
  that window ships the mutation.
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
- **Concurrent sessions on one branch are detected from a local ledger, not from a pushed
  `coord/<date>` branch.** The 2026-07-27 field convention was a live `coord/<date>` branch of
  empty marker commits, and it is **rejected here**: nothing in this repo mints a `coord/*`
  branch. Pushing a marker at every session start wants network and push rights before any work
  is planned, writes to shared repo state from a hook, leaves a branch per day to sweep, and only
  ever helps a session that remembered to push. What ships instead is `branch-activity-surfacer`,
  a `SessionStart` hook that records `(repo, branch, tip SHA, session id, ts)` and — before
  writing its own row — warns when a prior row for the same repo and branch came from a different
  session, naming the move `old -> new` with the commits, their authors, and the merged PR when
  `gh` can find one.
  **Naming:** the coordination surface is a ledger stream, so its name is that stream,
  `branch-activity.jsonl` under `${XDG_DATA_HOME:-~/.local/share}/agent-logs/claude-code/atelier/`;
  the repo key is `git rev-parse --git-common-dir`, which makes a main checkout and its linked
  worktrees one repo rather than several.
  **Pruning:** the ledger is append-only and disposable. Reads are capped to the last
  `BRANCH_ACTIVITY_MAX_BYTES` of the file and the peer warning ages out after
  `BRANCH_ACTIVITY_PEER_TTL_SECONDS`, so nothing has to be swept and deleting the file costs one
  missed warning per repo and branch that had a move pending, never more.
  **The ceiling:** the ledger is per-machine, so "a session is live *right now* on the other Mac"
  is not detected. The tip-move half still is — it is derived from git rather than from the
  ledger, so a merge made anywhere surfaces as soon as this checkout has the commit.
- **A worktree-isolated agent's cross-tree write is refused LOUDLY, but a relative path is
  not refused at all.** Probed on Claude Code 2.1.263 (2026-09-07) from a nested worktree,
  `CLAUDE_PROJECT_DIR` empty. An Edit or Write at an absolute path under the dispatcher's
  worktree — or under the main checkout — dies with `This agent is isolated in the worktree
  <path>. Edit the worktree copy of this file instead of the shared-checkout path.`, and
  nothing is written on either side. Read across the boundary is allowed. **The trap is the
  relative `file_path`**: it resolves against the agent's OWN worktree, so it succeeds while
  the dispatcher sees nothing at the path it expected — which is what two builders reported
  as an edit that "returned success and applied nothing". Neither repo-owned hook can produce
  that (`tests/test_nested_worktree_edits.py` pins both as allow-or-visible-deny). Two more
  edges of the same guard: a `git` command it cannot statically prove stays in-tree is refused
  whole (`too complex to verify`), and it reads the command TEXT, so a heredoc merely
  *containing* such a command is refused too — write that file with the Write tool.
- **Rule (2026-09-08): remove a worker's worktree only after its last message; once removed,
  never resume that worker again.** A resumed orphan's `pwd` and `git rev-parse
  --show-toplevel` silently re-resolve to the DISPATCHER's tree, with no error, and the guard
  then names that tree as the one the agent is isolated in — so an obedient agent would write
  there. Two facts drive the rule: **(a)** removal is not always a deliberate operator act — an
  unchanged worker worktree is auto-removed by the harness on completion, so the orphan state
  can arrive without anyone choosing it; **(b)** the resumed agent is not merely disoriented,
  it is aimed at the dispatcher's own tree and branch. Reproduced twice: 2026-09-07 (probe,
  PR #484) and 2026-09-08 (live, this repo). Owner ruling 2026-09-08: this is reasonable
  default harness behavior, not a defect — do not file it upstream. The practical defense is
  committing to your own branch as you go: a worker's committed work survives its worktree
  being removed; uncommitted work does not.

## Editing this repo

- **`git diff` appends a TAB to `+++ b/<path>` when the path contains spaces** — the
  `docs/decisions/*.md` filenames do. Split on `\t` before using the name.
- **No unguarded counts in prose or metadata** (owner rule). A count needs a gate behind it, or
  phrasing that survives growth.
- A new plugin is `plugins/<id>/` plus a hand-authored `marketplace.json` entry. The
  replacement of a vendored component must preserve its historical provenance record;
  see `docs/presentations-replacement.md` for the PPTX replacement and approval boundary.
- **A plugin's `description` is the only free-text field a user ever sees.** Measured
  2026-08-22: `claude plugin details <name>` prints name, version, description verbatim,
  component inventory, and token cost — nothing else. `homepage` and `repository` are
  recognized by the validator and rendered **nowhere**, and `changelog` is not a recognized
  field at all (the validator warns that Claude Code ignores it). That is why the release
  link lives in the description rather than in a field that looks purpose-built for it.
  Plugin descriptions cost no always-on context: a plugin with no skills or agents reports
  `Always-on: ~0 tok`.
- **`plugin.json` files are not uniformly encoded.** Some are `ensure_ascii=True` canonical
  (em dash as `—`), some are `ensure_ascii=False` (literal `—`). A JSON round-trip with
  one fixed setting reformats half of them and buries the real change in noise. Edit the
  target lines, or round-trip each file with its own existing setting.
- **Never mutate a second repo's git history.** Removing a marketplace via `/plugin` deletes its
  entries from the tracked `enabledPlugins` — correct here, worth knowing elsewhere.
