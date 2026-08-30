# Agent Instructions for this repo

## Task interface

`make ci` is canonical and is what CI runs on every PR into `dev`. `make help` lists the rest.

## Source-of-truth rules

- **`primitives-core/` is the only place a primitive is edited**, and it is self-authored only
  (ADR 0015) — third-party items are recorded by reference in `externals.yaml`, never copied in.
- **Root `plugins/<id>/` are hand-authored thin symlink assemblies** over it (ADR 0017):
  `plugin.json`/`hooks.json`/bundle READMEs are regular files, everything else symlinked;
  `.claude-plugin/marketplace.json` lists them; `make symlinks` lints.
- **Nothing generated is tracked** (ADR 0017) — generate at install/run time instead. A tracked
  artifact needing a regen step is a design smell. Generators that remain (`gen_opencode.py`)
  stay deterministic: stable ordering, no clocks, no random.
- **`primitives-core.yaml` (the roster) is the provenance manifest** — the drift guard reads it,
  not a directory listing. Schema in `primitives-core/README.md`; `origin: sourced` requires
  non-null `upstream` + `ref`. Plugin membership is NOT a roster field — membership is the
  symlink assemblies.
- **Atelier's doctrine prose is shared with its opencode port** and must land in both repos in
  the same wave — the transform, the one-sided artifacts, and why no CI here can catch the
  drift are in [`docs/atelier-parity.md`](docs/atelier-parity.md).
- **Tests are stdlib-only** (`python3 -m unittest`) — zero install is an invariant. Fixtures live
  in `tests/` tempdirs, never under `primitives-core/` (the roster guard flags orphans).

## Governance

Contributor SOP: [`.github/CONTRIBUTING.md`](.github/CONTRIBUTING.md). Traps this repo has
already hit — how to read `make ci`, which gates are CI-only, what `flow.yaml` breaks:
[`docs/gotchas.md`](docs/gotchas.md).

Branch off `dev`, PR into `dev`. Merging your own PR into `dev` is granted: the owner's
standing grant (2026-08-20) covers the whole loop — branch, commit, push, open PR, run CI,
merge, delete the branch. That grant is conditional on CI. Watch the checks to green and report
before calling a merge done; never merge red, and never bypass a required check.

Never commit to the default branch. `main` is publish-only (CI,
`.github/workflows/publish.yml`), is never merged into directly, and is never checked out
locally — a PreToolUse hook blocks it. Publishing goes through the sanctioned workflow dispatch
(the `publish-to-main` skill), which the merge grant does not replace. Read the published
surface with `git show origin/main:<path>`, or `git worktree add ../dotfiles-agents-main
origin/main` (remove the worktree after).

Keep changes surgical and match existing style. Get the owner's approval before major
information-architecture changes (moving/renaming top-level structures, reshaping the roster).

GitHub issues are bug intake only; planned work lives on the Kaneo board (see "Task tracking").

### Branch hygiene

Merge or abandon a branch **within the session that opened it** — parked work is invisible to
later sessions and dies with the branch. Delete after merge (`--delete-branch`, or a separate
`git push origin --delete` if the tree is dirty, since the flag switches branches). Before
deleting any branch, `git rev-list --count origin/dev..<branch>`; nonzero means diff each
changed file against `dev` before calling the work superseded. `dev-legacy` is a deliberate
pre-restructure archive — never delete it.

## Task tracking

The tracker is the **Kaneo board** (project `DFA` / "dotfiles-agents", workspace `hsb3`) — a
live board, not files in this tree. Work it through the `kaneo` plugin's skill: the claim
ritual, the level rules, and how decisions get recorded are that skill's law, not this page's.

**The session handoff is a board task too**: the one labeled `HANDOFF` in the `Document` lane
(DFA-233). Read it at session start; at session end rewrite its **description** in place under
the `handoff` skill's content rules. **No handoff file is tracked in this tree, and there is no
handoff branch — never create either.**

`handoff-freshness-guard` knows this via the `handoff: {mode: external, …}` block in
`.claude/atelier.local.md` (gitignored, per-project): it stats `.claude/handoff.stamp` instead
of searching for a handoff file. **Update the board task first, touch the stamp last** — the
guard reads the stamp's age, never the board's content, so an early touch certifies a handoff
that has not happened. No stamp yet in a fresh clone means the first manual `/compact` is
refused until `/handoff` runs, which is the intended answer. Needs atelier ≥ 0.15.0.

Config is the five `KANEO_*` values in `.claude/settings.local.json` (gitignored — they carry a
credential); missing or wrong, ask the owner rather than guessing. Never create a
`backlog.md`, a `TODO` file, or any other in-repo task list — file it on the board.

<!-- BEGIN KATA (managed by `kata init --with-agents`) -->
Kata is the system of record for intent.

- Never `kata delete` or `kata purge` without explicit user authorization.

~~~dot
digraph kata {
  rankdir=TB; node [shape=box];

  arrive   [shape=diamond label="Work arrives"];
  search   [label="Search first; reuse an open issue\nor create one"];
  route    [shape=diamond label="Work it, or delegate it?"];

  subgraph cluster_work {
    label="Working a kata-tracked issue";
    claim  [label="On claim or start, mark it actively tracked:\nkata meta set <ref> work.attention ok\nIn-flight work becomes visible to coordinators\nand dashboards from the moment it is grabbed."];
    branch [label="If the work happens on a dedicated branch, stamp it once:\nkata meta set <ref> work.branch <branch>\nor bind at creation:\nkata create ... --meta work.branch=<branch> --idempotency-key <key>"];
    live   [label="Keep your live state truthful on the issue:\nkata meta set <ref> work.attention stuck|needs-human|ok\nwith a one-line kata meta set <ref> work.attention_msg \"<why>\"\nRaise stuck when you cannot proceed, needs-human when you want\ninput or review (you may keep working), and clear back to ok\nwhen unblocked."];
    claim -> branch -> live;
  }

  subgraph cluster_delegate {
    label="Delegating work as separate issues (fan-out/join)";
    fanout [label="Create each delegated child with\n--parent <epic-or-coordinating-issue>,\n--meta work.branch=..., and an idempotency key;\ncapture refs from --json (.issue.short_id).\nAdd dependency links only for actual prerequisites."];
    join   [label="Join with kata wait <refs> --until attention --any\nMatches needs-human or stuck; a close also completes the wait,\nand the reported reason distinguishes which. Use --timeout so a\nwrapper can tell timeout from satisfaction."];
    coord  [label="As coordinator you read work.* —\nyou never write it on issues you delegated."];
    fanout -> join -> coord;
  }

  done     [shape=diamond label="Verified complete?"];
  close    [label="kata close <ref> --done\nwith a message and evidence"];
  review   [label="kata label add <ref> needs-review\nplus a comment on what remains"];
  park     [shape=diamond label="Park it?"];
  schedule [label="kata schedule <ref> <date-or-time>\nsets scheduled_on; clear with -"];
  someday  [label="kata meta set <ref> someday true --json-value\nclear with kata meta unset <ref> someday"];

  arrive -> search -> route;
  route -> claim   [label="work it"];
  route -> fanout  [label="delegate it"];
  route -> park    [label="record only"];
  live  -> done;
  coord -> done;
  done -> close    [label="yes"];
  done -> park     [label="no, stopping"];
  park -> schedule [label="start date known"];
  park -> someday  [label="no date"];
  park -> review   [label="no"];

  always [shape=note label="Always: one writer per key. work.* on closed issues is meaningless —\nnever write it there, ignore it when reading. Never end a session with\nthe signal stale: before stopping, either close the issue or set the\nattention pair to reflect the hand-off."];

  relationships [shape=note label="Relationships: Parent links express containment and roll-up only;\nthey do not gate readiness, and a parent cannot close with open children.\nUse --blocks <dependent> / --blocked-by <prerequisite>\nonly for real prerequisites; those links gate kata ready.\nUse --related <ref> for context only.\nkata wait observes state; it does not require a dependency edge."];

  gate [shape=note label="A future scheduled_on or someday=true keeps an issue\nout of ready and next. kata deadline <ref> <date-or-time>\nsets deadline_on, which never gates either."];
}
~~~
<!-- END KATA -->
