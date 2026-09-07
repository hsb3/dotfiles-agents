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
- **A missing tool is a failed gate, never a skipped one.** `make manifests` exits 1 when
  `claude` is not on PATH rather than passing with a notice. The version-bump and
  vendored-drift gates differ deliberately — they exit 0 with a notice when the remote is
  unreachable, so a network blip does not block every PR (`make labels` does NOT, see the
  next bullet). A missing binary is not a blip; it is a machine that cannot run
  the check, and a gate that reports green there teaches everyone it is running.
- **`make labels` takes that further: it is red on an unreachable remote too, where the
  older network gates skip and pass.** House rule (decision-016 point 4; consistency is card
  x8nf) — a gate that
  cannot measure is red, never green, because a CI step that exits 0 having measured nothing
  is indistinguishable in the summary from one that measured and found nothing wrong. It
  still names WHICH failure it hit (unreachable host vs. `gh` failing against a host that
  answered vs. no `gh` at all), and the unreachable message says outright that it is not
  evidence of drift, so nobody goes hunting for a bad label. The cost is a re-run on a blip;
  the ruling says that is the cheaper mistake. Do not "fix" this by copying the older gates'
  skip-and-pass onto it.
- **The README-currency gate reads git history, so `drift-guards` checks out at
  `fetch-depth: 0`.** In the default depth-1 checkout every file shares one synthetic commit,
  so every unit's body and README look like the same change and the gate would pass
  vacuously; it refuses a shallow clone instead. Only that job — `entry-gate-floor` stays
  depth-1 and its test for this gate skips there, so a test asserting the live tree is
  current must never assume history exists. The gate is also anchored at decision-015's
  landing commit: 31 of 56 units were stale the day the rule landed, and the anchor keeps it
  forward-only until those are backfilled. Lifting the amnesty means deleting those lines in
  `scripts/check_readme_currency.py` — the anchor is read out of history, so renaming or
  deleting the decision doc does nothing.
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
  *containing* such a command is refused too — write that file with the Write tool. And an
  agent resumed after its worktree was removed has `pwd` and `git rev-parse --show-toplevel`
  silently re-resolve to the DISPATCHER's tree, with the guard then naming that tree as the
  one it is isolated in.

## Editing this repo

- **`git diff` appends a TAB to `+++ b/<path>` when the path contains spaces** — the
  `docs/decisions/*.md` filenames do. Split on `\t` before using the name.
- **No unguarded counts in prose or metadata** (owner rule). A count needs a gate behind it, or
  phrasing that survives growth.
- A new plugin is `plugins/<id>/` plus a hand-authored `marketplace.json` entry. The
  `pptx-themes` README keeps its Anthropic attribution section — never drop it.
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
