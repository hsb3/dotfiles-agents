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
- **A shipped primitive that hardcodes a consuming repo's convention gets an override**, and there
  is one convention for how — an env var with a shell-expanded default for a hook, a
  `.claude/<id>.local.md` frontmatter key for a skill, detection for anything derivable from the
  tree. Both shipped mechanisms and the rule for choosing between them are in
  [`docs/override-convention.md`](docs/override-convention.md); do not invent a third.
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

### GitHub issues and kata cards

**GitHub issues are the external intake and the public record. kata cards drive the work.**
`kata sync github` is enabled and is **import-only** — one way, GitHub into kata (verified
2026-09-08: three cards created here with sync on produced no issues; the `sync github once`
payload has one direction key, `import`). Four consequences, and none of them is a bug:

1. **Never create a GitHub issue from a kata card.** kata forbids it outright; pushing every
   card outward doubles the bookkeeping for no reader. A card that did not come from GitHub
   simply has no mirror, and 40+ of ours do not.
2. **An imported mirror is the epic; native children are the work.** Decompose the mirror with
   `--parent <mirror>`, one child per focused PR, and work the children. A one-PR mirror is
   worked directly.
3. **Never rewrite a mirror's body, title, labels or comments** — the sync OWNS them and
   re-applies GitHub's version whenever that issue next changes. Acceptance criteria go in the
   children. This is why the session handoff is a native card and not a mirror.
4. **A kata close never closes the GitHub issue, and `Closes #N` is inert here** — GitHub
   auto-closes only from the default branch, and `main` is written solely by the publish
   workflow, which names no issue. So the mirror is closed **by hand** when its work lands
   (standing ruling 2026-08-24), and `make board-reconcile` is the sweep that catches the ones
   that got missed. See "Curation rhythm" step 5.

Historical note, because it misled a session on 2026-09-08: **Kaneo's sync was bidirectional** —
a board task minted an issue within seconds — and doctrine written for it survived the
2026-09-02 migration to kata. Anything asserting that the board mints or two-way-mirrors GitHub
issues is Kaneo-era residue, not current behavior.

### Branch hygiene

Merge or abandon a branch **within the session that opened it** — parked work is invisible to
later sessions and dies with the branch. Delete after merge (`--delete-branch`, or a separate
`git push origin --delete` if the tree is dirty, since the flag switches branches). Before
deleting any branch, `git rev-list --count origin/dev..<branch>`; nonzero means diff each
changed file against `dev` before calling the work superseded. `dev-legacy` is a deliberate
pre-restructure archive — never delete it.

## Task tracking

The tracker is the **kata board** (project `dotfiles-agents`, bound by `.kata.toml`, served by
the hosted daemon) — a live board, not files in this tree. The kata block below is the law for
working it. The Kaneo board (project DFA) that preceded it was archived on 2026-09-02 after every
open task was carried over; a migrated issue carries the old number in `kaneo_task_number`
metadata (`kata list --meta kaneo_task_number=<N>`), and the `kaneo-status:up-next` label marks
what sat in the owner's queue at cutover.

**The session handoff is a board issue too**: `4w08` (title "Session Handoff", label
`handoff`). It is a **native** card with no GitHub mirror, deliberately — it replaced mirror
card `8xyk` on 2026-09-08 because the sync owns a mirror's body and reverted the handoff
whenever GitHub #329 changed (demonstrated live: closing that issue wiped the card's body and
priority, and closed the card). `8xyk` and #329 are both closed; do not resurrect either.
Read it at session start; at session end rewrite its
**body** in place under the `handoff` skill's content rules. **No handoff file is tracked in this
tree, and there is no handoff branch — never create either.**

`handoff-freshness-guard` knows this via the `handoff: {mode: external, …}` block in
`.claude/atelier.local.md` (tracked since 2026-09-07 by owner ruling, so worktree workers and both Macs share it; the stamp stays ignored): it stats `.claude/handoff.stamp` instead
of searching for a handoff file. **Update the board issue first, touch the stamp last** — the
guard reads the stamp's age, never the board's content, so an early touch certifies a handoff
that has not happened. No stamp yet in a fresh clone means the first manual `/compact` is
refused until `/handoff` runs, which is the intended answer. Needs atelier ≥ 0.15.0.

Never create a `backlog.md`, a `TODO` file, or any other in-repo task list — file it on the
board.

**Curation rhythm** (7hws, 2026-09-07; health + reconcile steps added 2026-09-08). At session
start, in order:

1. `kata_doctor.py` — wiring (binary, daemon, binding, `KATA_AUTHOR`, shim, duplicate server;
   every warn is wiring debt to fix).
2. `audit_issues.py --project dotfiles-agents` — definition and dependency hygiene over open
   issues.
3. `board_health.py` — does the board still *discriminate*? **This step now runs itself.** The
   `.claude/hooks/board-health/` SessionStart hook prints the verdict into session context at
   every `startup`/`resume`/`clear`, warn-only and exit 0 always, so a finding never blocks a
   session. `make board-health` runs the same measurement on demand and goes non-zero when a
   pass is due (make reports the script's own exit as its own error, the way `make labels`
   does; run `board_health.py` directly for the exact 0 clean / 1 findings / 2 could-not-measure
   code). `PROJECT=<name>` points it at another board. Both read the in-tree copy of the script
   and pass
   `--vocabulary primitives-core/skills/board-triage/scripts/core-labels.txt`, the core label
   set of decision-023 — without a declaration the `vocabulary-fossils` check is SKIPped every
   run, because a board's own label history is not a declaration. A verdict line saying it
   **could not measure** is not a clean board: it names which failure it hit (no `kata` binary,
   unreachable daemon, missing declaration) and nothing was checked. Read the hook's line; run
   step 4 only when it reports findings.
4. The board-triage kata adapter, **only if step 3 exited non-zero**. Re-run step 3 after to
   confirm the pass took.
5. `make board-reconcile` — GitHub issues against the board (see below).

Steps 1–2 ship in the kata plugin
(`~/.claude/plugins/cache/kata-oversight/kata/<version>/skills/kata-audit/scripts/`).
Findings to fix: `title-long`, `no-acceptance`, `prose-dep` (add the edge, or reword if it is
not a real prerequisite), `no-priority` (the frozen kaneo children under `my1a` may stay blank).
Ignore `unlinked-ref` until kata-oversight `z6gb` filters its noise (closed cards named in prose,
epics naming their own children).

**Steps 2 and 3 are not redundant.** `audit_issues.py` reads one card and asks whether its
fields are *populated*; `board_health.py` reads the whole board and asks whether those fields
still *discriminate*. On 2026-09-08 the audit reported `no-priority: 0` and `body-thin: 0` on a
board where 34 of 55 open items sat in one priority band, 16 carried no label, and the area
grouping lived only in title prefixes. A per-card check cannot see a distribution. Run both.

**Board conventions.** The vocabulary is not restated here — it is
[`decision-023`](docs/decisions/decision-023%20-%20kata-labels-are-the-triage-system-and-title-prefixes-are-not.md),
declared machine-readably in `primitives-core/skills/board-triage/scripts/core-labels.txt`, and
that record is the copy to change. What it means day to day: every open card carries exactly one
`area:*` and exactly one `type:*`, titles carry **no prefix of any kind** (the grouping lives in
labels, where a query can reach it), and this project adds areas on top of the core rather than
instead of it — add one only when a genuine new domain appears, never for a single card. Board
labels do NOT propagate to GitHub, and GitHub's own closed set (decision-016) is a *subset* of
the core: the board-only names never reach the repo. `make labels` proves it.

**Step 5 — the GitHub reconcile** (owner ruling 2026-09-08). `scripts/reconcile_github.py`
classifies every open GitHub issue against the board and is dry-run by default; `APPLY=1 make
board-reconcile` executes.

| class | meaning | action |
|---|---|---|
| `tracked` | its card is open | nothing |
| `stale-mirror` | its card is **closed** | close the issue with a pointer to the card — the script does this |
| `untracked` | no card at all | inbound intake: file it on the board by hand, then rerun |

It never creates cards: intake needs judgment, and the card may already exist unlinked (#488 was
already on the board as `wvkc`, byte-identical, missing only the `github_issue` metadata — stamp
the link rather than filing a duplicate). Not a `make ci` gate; it reads the live hosted board,
which CI cannot reach.

Why it has to exist: the sync mints an issue on card creation but propagates no close, so the
drift grows by one every time a card closes. Before the first run (2026-09-08) 13 of 27 open
issues were finished work. It also defuses a live hazard —
`kata sync github enable` resets the sync cursor and re-applies GitHub state onto the board,
**reopening every closed card whose mirror is still open**
(`.claude/memory/kata-sync-enable-resets-cursor.md`).

**`audit_issues.py` is the definition bar for this board; planning-desk's `conformance.py` is
advisory** (owner ruling 2026-09-08, `bxer`). They disagree because they check different things:
kata-audit reads a card's substance (a title that fits, acceptance text present, a prose dependency
that should be a real edge, a priority), while conformance checks for named markdown HEADINGS —
`Acceptance criteria` and `Dependencies & gates`, or `Close when` on an epic. A card can be fully
buildable and still fail conformance for want of a heading, so conformance gates nothing here; use
it when briefing a wave, where the headings are what a worker reads.

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
