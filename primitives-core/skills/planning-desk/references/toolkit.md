# Mode: govern — the toolkit (backlog grooming, drift audits, "what's next")

Seven dependency-free Python scripts live in `_meta/plans/_utils/`. Each is a generated VIEW over
`gh` + disk — never hand-maintained state — with a `--json` flag and, except for `sequence` and `deps-suggest` (pure views, always exit 0),
a non-zero exit on findings, so any one can gate a wave (in CI, a pre-push hook, or a loop). Run them from the **main working tree**
where `gh` is authed; they derive the repo from `gh` itself, so they need no per-project config.

Run a script: `python3 _meta/plans/_utils/<script>` (or `uv run …`; the `#!/usr/bin/env -S uv run`
shebang makes `./_meta/plans/_utils/<script>` work too). Add `--json` for machine output.

## The seven

| Script | What it checks | Mutates? | Exit 1 when |
| ------ | -------------- | -------- | ----------- |
| `reconcile.py` | README rows vs live issue state vs disk folders vs each `plan.md`'s Tracking | no | any drift |
| `conformance.py` | every open issue body vs its `.github/ISSUE_TEMPLATE` required sections | no | any non-conformant |
| `coverage.py` | open non-epic issues with NO plan folder (the planning backlog), tagging maybe-trivial | no | any uncovered |
| `sequence.py` | tiers ALL open issues into NOW / NEXT / BLOCKED / DEFERRED | no | never (a view) |
| `deps-suggest.py` | prose "blocked by #N" deps not yet written as native GitHub edges (advisory) | no | never (advisory) |
| `sync-bodies.py` | each folder's `issue-body.md` vs the live GitHub body | only `--push`/`--pull` | any DIFFERS |
| `evidence-audit.py` | recently-closed issues that closed with no linked PR + no evidence comment | no | any flagged |

## When to reach for which

- **"What should I work on next?"** → `sequence.py`. It emits TIERS, not a 1..N rank (there's no one
  true order). NOW = on a dated milestone, has a plan, not blocked. It reads `gate:*` labels,
  milestone due dates, native blocked-by edges, and plan-readiness (a plan folder exists).
- **"Groom / audit the backlog."** → `coverage.py` (what has no plan) + `conformance.py` (what has no
  real acceptance criteria). Together they define the planning backlog: unplanned and/or non-conformant.
- **"Is the desk honest?"** → `reconcile.py`. Run it at the start of any session that works off the
  README table (trust it before relying on it) and at the end (catch rows you left stale).
- **"Wire up dependencies."** → `deps-suggest.py` proposes edges harvested from prose; a human
  confirms each, then writes it with
  `gh api --method POST repos/<owner>/<name>/issues/{n}/dependencies/blocked_by -F issue_id=<id>`.
  `sequence.py` then reads those native edges for the BLOCKED tier.
- **"Did anything close sloppily?"** → `evidence-audit.py` (after-the-fact backstop for the
  attach-evidence-before-close convention; heuristic — treat a flag as "go look", not proof).
- **"Publish the staged bodies."** → `sync-bodies.py` (read-only by default). `--push` is
  ALL-OR-NOTHING: it pushes EVERY drifting body on the desk. To publish a single issue, use
  `gh issue edit <n> --body-file …` instead; reserve `--push` for a deliberate bulk reconcile.

## Conventions the scripts depend on

Keep new plans inside these or the parse drifts (`reconcile.py` enforces, with WARNs):

1. The folder name equals the README **Plan** cell (kebab-case, no number prefix).
2. The folder contains `plan.md`.
3. `plan.md` has a `## Tracking` section whose FIRST `#NNN` is the tracking issue (epics/relations
   come AFTER it — a WARN catches a violation).
4. The README **Issue(s)** column's first `#NNN` is that same issue.
5. The README keeps its `ACTIVE plans` and `ARCHIVED (` section markers (the seed README ships them).

Archived plans move to `_meta/_archive/<issue>-<slug>.md` and are matched by issue number, not folder
name.
