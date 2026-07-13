---
name: planning-desk
description: >-
  Stand up and run a source-grounded planning desk under _meta/plans/ — the workflow for
  authoring conformant GitHub issue bodies, writing deep build plans, and driving them
  through a multi-round draft → review → fix → reconcile loop, with a bundled toolkit of
  governance scripts (conformance, coverage, reconcile, sequence, deps, sync, evidence).
  Use this whenever the user wants to file or fix a GitHub issue with real acceptance
  criteria, plan a feature or epic before building, run a planning or backlog-grooming
  session, organize work in _meta/plans/, audit issue/plan drift, or set up this planning
  system in a new repo — even if they just say "write me an issue", "plan this out",
  "groom the backlog", "what should I work on next", or "get this repo's planning organized".
  Prefer this over ad-hoc issue/plan writing: it enforces deliverables/criteria/parallelism
  (never timelines), grounds every claim in cited source, and keeps the board and the desk in sync.
---

# Planning desk

A repeatable system for turning fuzzy intent into **build-ready, source-grounded plans and
conformant GitHub issues**, kept tidy on a local `_meta/plans/` desk and governed by a small
toolkit of dependency-free scripts. It is the generalization of a battle-tested workflow; this
skill carries the workflow, the standards, and the scripts so any GitHub-backed repo can adopt it.

## The shape of the system

```
_meta/plans/                     # the desk — one folder per unit of work
  README.md                      # the live per-plan status index (ACTIVE / ARCHIVED tables)
  _config.md                     # THIS project's gates, issue-template sections, canonical docs
  _utils/                        # the governance toolkit (7 scripts, gh + disk views)
  <slug>/
    issue-body.md                # the intended GitHub issue body (staged, reviewable)
    plan.md                      # the deep build plan (deliverables, acceptance, gates, order)
```

**Two artifacts per unit of work, with distinct jobs.** The `issue-body.md` is the *contract* a
builder picks up cold — what to build, how it's judged, what's out of scope — and it conforms to
the repo's issue template. The `plan.md` is the *build detail* — what already shipped vs what's
residual, every claim cited to `path:line`, deliverables sliced into ownable units, the gates that
fire, and the safe landing order. The board tracks STATE; the desk holds DETAIL.

**The desk is git-tracked** (`_meta/` is tracked by default, ADR-0006). That
makes plans + scripts visible in a fresh clone and to cloud/worktree agents; the toolkit's
`__pycache__/` bytecode stays ignored. The scripts are generated VIEWS over `gh` + disk — never
hand-maintained state — each with `--json` and a non-zero exit on findings, so any one can gate a
wave in CI or a pre-push hook.

## Pick the mode

Figure out which of these the user is asking for and follow the matching reference. Don't load a
reference you don't need.

| If the user wants to…                                              | Mode      | Read                          |
| ------------------------------------------------------------------ | --------- | ----------------------------- |
| set up the desk in a repo that lacks one (`_meta/plans/` absent)   | **setup** | this file (Setup, below)      |
| write or fix a GitHub issue body with real acceptance criteria     | **issue** | `references/issue-body.md`    |
| produce a deep, source-grounded build plan for an issue/feature    | **plan**  | `references/plan.md`          |
| run a multi-round planning session over a batch of plans/issues    | **loop**  | `references/loop.md`          |
| groom the backlog / "what's next" / audit drift / close-hygiene    | **govern**| `references/toolkit.md`       |

If the desk doesn't exist yet (`_meta/plans/` is absent) and the user asks for issue/plan/loop work,
do **setup first** (it's quick), then proceed — a one-line "I'm scaffolding the desk first" is enough.

Two standing standards underpin the modes above — read `references/entry-forms-and-milestones.md`
when the question is **what shape a unit of work takes to enter a queue** (the backlog-entry form for
a use case entering a project backlog, and the bench-entry form for a candidate entering an incubator —
one shared field core, two applications) or **what gate/milestone vocabulary a board should speak** (the
shared `P<n> — <promise>` milestone set + `gate:<promise>` labels). Issue authoring cites the
backlog-entry form; board setup cites the milestone set.

## First, always: orient

1. **Confirm `gh` is authed and the repo is GitHub-backed.** `gh repo view --json nameWithOwner`.
   The whole toolkit and both authoring modes assume issues live on GitHub. If there's no GitHub
   remote, say so — the desk's *plan.md* discipline still helps, but the issue/governance half won't.
2. **Check for the desk.** Is there a `_meta/plans/` with a `README.md` and `_utils/`? If yes, read
   `_meta/plans/_config.md` to learn this project's gates + issue-template sections before authoring.
   If no, you're in **setup**.
3. **Run from the main working tree.** The desk's `_utils/` scripts read live `gh` state and the
   plan folders on disk; run them where `gh` is authed (the main checkout), not a bare worktree.

## Setup — scaffold the desk into a new repo

The goal: drop the folder, the README, and the toolkit in; then teach the desk *this project's*
specifics by writing `_config.md`. Do it in this order.

1. **Create the structure.** `mkdir -p _meta/plans/_utils`. Copy the seven scripts + `_repo.py`
   from this skill's `scripts/_utils/` into `_meta/plans/_utils/`. Copy `assets/plans-README.md`
   to `_meta/plans/README.md` (it carries the `ACTIVE plans` / `ARCHIVED (` section markers that
   `reconcile.py` parses — keep them). These scripts are dependency-free stdlib + `gh`; no install.

2. **Check the `.gitignore` so the desk is tracked.** Under ADR-0006 `_meta/` is tracked by
   default — no negation machinery. If the target repo already tracks `_meta/` (or doesn't
   ignore it), the desk is tracked with no change; just keep the toolkit's bytecode out with a
   `__pycache__/` rule if the repo lacks a global one:
   ```gitignore
   _meta/plans/_utils/__pycache__/
   ```
   If the repo currently ignores `_meta/` (a broad `_meta/*`/`_meta/` line), replace that broad
   ignore with the track-by-default stanza rather than adding negations — the `operations/` pair
   plus the cache rule:
   ```gitignore
   _meta/operations/*
   !_meta/operations/.gitkeep
   _meta/plans/_utils/__pycache__/
   ```
   Flipping a formerly-ignored `_meta/` newly tracks whatever was sitting there: run a secrets
   scan of the newly-tracked content before committing (ADR-0006's pre-flip guard). Confirm the
   desk is tracked with `git check-ignore -v _meta/plans/README.md` (should print nothing).

3. **Detect this project's gates + templates, then write `_config.md`.** This is the step that
   makes the desk portable. Investigate, don't assume:
   - **Issue templates:** read `.github/ISSUE_TEMPLATE/*.md`. Note each template's required
     sections (the conformance gate keys on an *acceptance-criteria* section + a *dependencies/gates*
     section for non-epics, a *close-when* section for epics). If the repo has **no** templates,
     offer to seed them from `assets/ISSUE_TEMPLATE/` (generic feature/bug/epic) — the conformance
     gate needs *some* template structure to check against.
   - **Gate menu:** find the project's real gates — the commands a change must pass and the
     source-of-truth artifacts it must keep in sync. Grep the `Makefile`, `package.json` scripts,
     `pyproject.toml`, CI workflows (`.github/workflows/`), and any `CONTRIBUTING`/agent-guide for:
     test command, lint/format, type-gen or codegen with a drift guard, migrations, a canonical
     contract/schema/charter doc that must be amended in the same PR as a surface change. List the
     real ones; don't invent gates the project doesn't have.
   - **Canonical docs to cite:** the spine docs a plan should ground itself in (charter, API
     contract, schema, architecture, ADRs).
   Fill `assets/_config.template.md` with what you found and write it to `_meta/plans/_config.md`.
   Where you couldn't determine something, write a `TODO(owner):` line rather than a guess.

4. **Confirm the toolkit runs.** From the main tree: `python3 _meta/plans/_utils/conformance.py`
   (audits live issue bodies) and `python3 _meta/plans/_utils/reconcile.py` (an empty desk
   reconciles clean). A clean run proves `gh` access + the scripts are wired.

5. **Report** what you scaffolded, what `_config.md` captured (especially any `TODO(owner):`
   gaps), and how to use it: "`planning-desk` issue mode to file an issue, plan mode to plan one,
   loop mode to run a planning session." Offer to author the first plan as a worked example.

## The non-negotiables (every mode)

These are why the system produces good work rather than plausible-looking work. Carry them into
whatever mode you're in:

- **Ground every load-bearing claim in cited `path:line` source — never a stale checklist.** The
  backlog is mostly partly-shipped; an issue's framing and line numbers are routinely wrong. State
  the *true residual*, not what the issue says remains. Verify what already shipped against source.
- **Subagent findings are hypotheses.** When you fan out Explore/research agents for breadth (do —
  it's faster), re-derive any claim that would change a plan's core recommendation against the
  actual source before it lands. Right-citation/wrong-mechanism is the classic failure.
- **Deliverables, acceptance criteria, parallelism — NEVER timelines.** No week-by-week schedules.
  Acceptance criteria must be *independently verifiable* by someone who didn't write the code
  ("grep returns zero hits", "test X passes", "the gate fails on drift") — not "works well".
- **Keep genuine owner decisions OPEN.** Surface them as numbered questions each with a recommended
  default; don't bury an unresolved choice as false confidence.
- **Outward-facing actions get confirmation.** Drafting/staging a body or plan on the desk is free;
  creating or editing a live GitHub issue is publishing — present the draft, let the owner approve,
  then push only the one issue.
- **ASCII-only inside markdown table cells.** Em-dash / middle-dot / arrows / non-breaking chars
  inside a table cell trip many repos' prettier/markdown format checks; no literal `|` in cells.

## The toolkit at a glance

Seven scripts in `_utils/`, each a read-only view (except `sync-bodies.py --push/--pull`), each with
`--json` and a gating exit code. Full detail + when to run each: `references/toolkit.md`.

| Script              | Answers                                                                  |
| ------------------- | ------------------------------------------------------------------------ |
| `conformance.py`    | does every open issue body carry its template's required sections?       |
| `coverage.py`       | which open non-epic issues have NO plan folder? (the planning backlog)   |
| `reconcile.py`      | do the README rows agree with live issue state and the folders on disk?  |
| `sequence.py`       | what's the work order? tiers open issues NOW / NEXT / BLOCKED / DEFERRED  |
| `deps-suggest.py`   | which prose "blocked by #N" deps aren't yet native GitHub edges?          |
| `sync-bodies.py`    | does each staged issue-body.md match its live GitHub issue body?          |
| `evidence-audit.py` | which recently-closed issues closed with no PR/evidence? (close backstop) |
