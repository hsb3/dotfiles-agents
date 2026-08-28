# Migrate-at-scale playbook (architecture C, named)

A **migrate-at-scale** job is architecture C — flat fan-out — applied to one recurring shape: the
same mechanical transform repeated across many sites (files, modules, callsites, repos). It is
common enough, and different enough in its failure modes from a generic parallel build, to name
and dispatch directly rather than re-derive each time.

**Trigger for this playbook, not a generic C fan-out:** the job is one transform pattern applied
to N independent locations — a rename, an API-signature change, a dependency swap, a codemod. If
each site instead needs a *different* judgment call, this is not migrate-at-scale; see "When NOT
to fan out" below.

**Why this shape earns the collapse.** Being architecture C, it runs without a management layer,
which the layer model treats as the exception. A frozen transform spec satisfies the collapse
conditions unusually cleanly: the site inventory makes the work-list final, identical transforms
make the slices independent in outcome, each worker returns a grep-zero line rather than material,
and the reconciliation is a diff of the inventory against reported files. When the site count is
large enough that the worker reports themselves must be cross-read, or odd sites need adjudicating
mid-wave, put one `manager` over the fan-out and take back one package.

## 1. Discover and slice the site inventory

Before writing a single brief, produce the **site inventory**: an explicit, enumerated list of
every file/module/callsite the migration touches, not an estimate. Use `scout` agents (haiku
default) for the sweep — this is read-only, high-volume, low-judgment work, exactly what scouts
are for:

- Grep/AST-search for the old pattern across the whole tree; do not sample.
- Group hits by natural ownership boundary — usually one file, sometimes one directory or one
  module — so each group can become a disjoint-file-scope worker slice.
- Flag **odd sites** the scout can't classify confidently: multi-pattern files, generated code,
  vendored copies, dynamic call sites the grep can't see through. These stay with the strategist —
  see §3.

The inventory is a deliverable, not scratch: keep it as a checked-in list or task set the
reconciliation pass can diff against later. **No silent caps** — if the sweep is bounded (a
top-N sample, a subset of repos), that bound is stated in the inventory itself, not discovered
during reconciliation.

## 2. Brief the workers — mechanical-transform template

Each worker gets a **disjoint file-ownership slice** from the inventory (one file, or a small
same-shape cluster) and the *same* transform spec. Because the transform is mechanical and
identical per site, this is where cheap models earn their keep — default every worker to
`builder`; "the transform needs judgment" is exactly the signal that a site doesn't belong in
this fan-out (§4).

<!-- harness:claude-code -->
Because the model is chosen per dispatch here, there is rarely a case for `model: opus` on a
migration slice — and where one site genuinely needs judgment, an opus-tier `builder` is the
alternative to keeping it with the strategist (§4).
<!-- /harness -->

Brief shape (fill every section — same discipline as the architecture-D manager brief):

```
You are a BUILDER doing a scoped, mechanical migration slice. Zero chat context — everything
you need is below.

## Transform spec (identical for every worker this wave — do not vary it)
- Old pattern: <exact pattern / API / import / idiom being replaced>
- New pattern: <exact replacement>
- Worked example: <one before/after pair from a real site in this repo>

## Your slice
- Files you own: <exact list from the site inventory — disjoint from every other worker>
- Out of scope: everything else (report, don't touch)

## Per-site definition of done
1. Every occurrence of the old pattern in your files is replaced with the new pattern.
2. `rg -n '<old-pattern>' <your files>` returns zero matches.
3. <any local test/lint/build command that must still pass after the edit>
4. No file outside your slice is touched.

## Evidence format (your handoff note)
- Files changed, and the grep-zero output for your slice.
- Anything that didn't fit the transform spec exactly (odd site) — report it, do not improvise
  a variant transform. Flag it for the strategist instead of guessing.
- Commands you ran, with actual output.

## Stop conditions
- A site doesn't match the transform spec as written — stop, report, don't invent a variant.
- The local test/lint command fails after your edit and a reasonable retry — stop and report.
```

## 3. What the strategy layer keeps

These never move to a worker, whatever the site count:

- **The transform spec itself** — writing and freezing the exact old→new pattern before dispatch.
  A spec that drifts mid-wave (worker A guesses one variant, worker B another) is the single
  biggest source of migrate-at-scale rework.
- **The site inventory** — ownership of the enumerated list, its completeness, and its stated
  bounds.
- **Judgment calls on odd sites** — anything a scout flagged as ambiguous, or a worker reported
  as not matching the spec. Resolve these directly or split them into their own single-site
  brief with a spec amendment; never let a worker silently improvise a variant to make an odd
  site fit.

## 4. Reconciliation pass — one serial agent, budgeted up front

Parallel mechanical edits at scale leave a specific drift signature: budget one serial `scout` or
`builder` pass (per the C-architecture reconciliation step) to check for it directly rather than
trusting worker self-reports:

- **Stale imports** — the old pattern removed from call sites but its import/require left behind
  (or vice versa: new pattern used without its import added).
- **Missed sites** — anything in the original sweep that no worker's grep-zero covers; diff the
  site inventory against the union of worker-reported files.
- **Mixed idioms** — two workers landing on subtly different renderings of the same "new pattern"
  because the spec had a gap the odd-site process didn't catch.

## 5. Verification gates before calling it done

- **Grep-zero for the old pattern, repo-wide** — not per-slice. `rg -n '<old-pattern>'` across
  the whole tree, not just the union of worker-owned files; a repo-wide zero is what catches a
  site the inventory missed entirely.
- **Full test suite** — a per-site test passing is not sufficient signal; the migration can break
  a caller outside any single worker's slice.
- **No silent site-list caps** — if any site was dropped or deferred (odd site never resolved,
  a repo excluded from the sweep, a directory skipped for time), that is stated explicitly in the
  final report and carried to the backlog. A migration that quietly covers 90% of sites and
  reports "done" is the exact failure this gate exists to catch.

## When NOT to fan out

Migrate-at-scale is a poor fit. Fall back to architecture A (direct) or D (manager-driven) when:

- **Few sites.** Below the point where slicing, briefing, and reconciling costs less than doing
  it directly, just do it (architecture A's floor applies here too).
- **Coupled sites.** If site 2's transform depends on how site 1 landed (a shared type threading
  through both, an ordering constraint), this is a dependent chain, not disjoint slices — use
  architecture D and let one `manager` drive it.
- **Per-site judgment.** If applying the transform correctly requires different reasoning at
  each site (not just a different literal value, but a different *decision*), workers will
  either improvise inconsistent variants or escalate constantly, defeating the point of cheap
  mechanical dispatch. Route this to architecture D, or split into a small judgment-heavy subset
  (kept by the strategist or a manager) plus a genuinely mechanical remainder fanned out
  separately.
