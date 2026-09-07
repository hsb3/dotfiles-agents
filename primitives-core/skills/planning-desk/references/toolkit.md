# Mode: govern — the toolkit (backlog grooming, drift audits, wave gating)

Three dependency-free analysis scripts live in `_meta/plans/_utils/`, over one tracker adapter.
Each is a generated VIEW over the tracker snapshot + disk — never hand-maintained state — with a
`--json` flag and a non-zero exit on findings, so any one can gate a wave (in CI, a pre-push hook,
or a loop). Run them from the **main working tree**, where the tracker CLI is configured.

Run one: `python3 _meta/plans/_utils/<script>` (the `#!/usr/bin/env -S uv run` shebang makes
`./_meta/plans/_utils/<script>` work too). Add `--json` for machine output.

## Export -> analyze -> apply

The backend never leaks into the analysis scripts. One adapter reads and writes the tracker; the
three scripts only ever see a snapshot.

1. **Export.** `adapters/<name>.py export` writes a snapshot JSON — the open items, their bodies,
   labels, kinds, and links, in the backend-neutral shape.
2. **Analyze.** `tracker.py` resolves which snapshot the scripts read: `--snapshot FILE` for a
   snapshot already on disk, or `--adapter` / `--project` to have it exported first. The three
   scripts take those same flags, so a wave can analyze one frozen snapshot repeatedly.
3. **Apply.** A script that proposes a change emits a **changeset TSV**; `adapters/<name>.py apply`
   writes it back. Apply is **dry-run by default** — read the plan, then re-run to commit it.

The contract for the snapshot and the changeset — the extension point for a second backend — is
`adapters/contract.md`. The shipped backend and its field map: `adapters/kata.md`.

## The three

| Script | What it checks | Mutates? | Exit 1 when |
| ------ | -------------- | -------- | ----------- |
| `conformance.py` | every open item body carries acceptance criteria + a dependencies/gates section (an epic: a close-when section) | no | any non-conformant |
| `coverage.py` | open non-epic items with NO plan folder (the planning backlog) | no (`--changeset FILE` only writes a proposal) | any uncovered |
| `reconcile.py` | README rows vs live tracker state vs disk folders vs each `plan.md`'s Tracking | no | any drift |

## When to reach for which

- **"Groom / audit the backlog."** → `coverage.py` (what has no plan) + `conformance.py` (what has
  no real acceptance criteria). Together they define the planning backlog: unplanned and/or
  non-conformant. `coverage.py --changeset FILE` turns its findings into an apply-ready changeset
  proposing a `needs-plan` label on each uncovered item — review the file, then apply it.
- **"Is the desk honest?"** → `reconcile.py`. Run it at the start of any session that works off the
  README table (trust it before relying on it) and at the end (catch rows you left stale).
- **"What should I work on next?"** → not here. Readiness is computed by the tracker itself
  (dependency edges, schedules, gates), and prioritization is the `board-triage` skill's job.

## Conventions the scripts depend on

Keep new plans inside these or the parse drifts (`reconcile.py` enforces, with WARNs):

1. The folder name equals the README **Plan** cell (kebab-case, no number prefix).
2. The folder contains `plan.md`, and nothing else is required of it.
3. `plan.md` has a `## Tracking` section whose FIRST ref known to the snapshot is the tracking
   item (epics and relations come AFTER it — a WARN catches a violation).
4. The README ref column's first known ref is that same item.
5. The README keeps its `ACTIVE plans` and `ARCHIVED (` section markers (the seed README ships
   them).

Archived plans move to `_meta/_archive/<ref>-<slug>.md` and are matched by tracker ref, not folder
name.
