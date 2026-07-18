# Mode: issue — author a conformant GitHub issue body

You are authoring a **proper issue body** — one a builder could pick up cold and know what to
build, how it will be judged, and what is out of scope. It lands staged at
`_meta/plans/<slug>/issue-body.md`, and is published to GitHub only after the owner approves.

Read `_meta/plans/_config.md` first — it names this project's issue templates, required sections,
gate menu, and canonical docs. Everything project-specific below comes from there, not from memory.

## The standard you must meet

The body conforms to the matching `.github/ISSUE_TEMPLATE/` option and PASSES the conformance gate
(`_meta/plans/_utils/conformance.py`). The gate is tolerant about heading wording but strict about
the load-bearing sections:

- **feature / bug** (non-epic): an **Acceptance criteria** section (heading matching
  `accept | definition of done | done when`) AND a **Dependencies & gates** section (matching
  `gate | depend`). A feature with no acceptance criteria is NOT ready.
- **epic / tracker** (label `epic`, or a `Tracking:` / 📌 framing): a **Close when** section
  instead (its acceptance equivalent).

State **deliverables, criteria, and parallelism — NEVER timelines.** Keep genuine owner decisions
OPEN; don't bury an unresolved choice as false confidence.

## Procedure

1. **Resolve the target.** If the argument is an issue number, read the live issue
   (`gh issue view <n> --json number,title,body,labels`). If it's a description, treat it as a new
   issue to draft. Pick the template with a stable tiebreaker so the same description doesn't land
   on different templates across runs: **default to `feature`**; use **`bug`** if the description
   mentions a regression, wrong/broken behavior, or a crash; use **`epic`** only if it explicitly
   frames a rollup/tracker over child issues. Read the matching template and follow its section
   structure exactly.

2. **Ground the problem in source — do not guess.** Investigate the repo (Grep/Read, or dispatch
   parallel `Explore` agents for breadth). Cite `path:line`, a canonical doc (from `_config.md`),
   observed behavior, or a linked issue. **Describe the problem, not the solution.** Verify what
   ALREADY SHIPPED so the body scopes the true residual, not built code — subagent claims are
   hypotheses; confirm the load-bearing ones against source.

3. **Fill every applicable section.** Name file/endpoint targets in Deliverables so no rediscovery
   is needed. Make each acceptance criterion **independently verifiable** by someone who didn't
   write the code ("X returns Y", "test Z passes", "the gate fails on drift") — not "works well".

4. **Check the real gates** in "Dependencies & gates", based on the actual change surface. Pull the
   menu from `_config.md` and pick what this change touches — e.g. a typed-API change that must
   regenerate a client + amend a contract doc in the same PR; a DB migration with its run cost; a
   codegen/spec artifact with a drift guard; an infra change; and always the project's pre-commit
   gate (test/lint). Be explicit about gates that do NOT fire, too.

5. **Write it** to `_meta/plans/<slug>/issue-body.md` (slug = kebab of the outcome; reuse the
   existing folder if the issue already has one). Lead with a tracking blockquote:
   `> **Tracking:** #<n>, <origin/why>. <one-line framing>.` For a NEW issue not yet created, use
   `#TBD` and replace it with the real number after step 7 creates the issue.

6. **Verify the gate — always.** Confirm the staged body carries the required sections (non-epic:
   both Acceptance criteria + Dependencies & gates; epic: Close when) — exactly what
   `conformance.py` enforces. Note the script audits **live GitHub** bodies, not the staged file,
   so run `python3 _meta/plans/_utils/conformance.py --json` and confirm the issue isn't flagged
   *after* the push (step 7) — or now, for an already-published issue.

7. **Stop and present the draft for review.** Do NOT create or edit the GitHub issue automatically —
   that's outward-facing. After the owner approves, push **only this issue**:
   - existing issue → `gh issue edit <n> --body-file _meta/plans/<slug>/issue-body.md` (scoped to
     the one issue). Do NOT use `sync-bodies.py --push` to publish a single draft — it is
     **all-or-nothing** and pushes EVERY drifting body on the desk, which could silently publish
     other half-finished drafts. Reserve `--push` for a deliberate bulk reconcile.
   - new issue → `gh issue create --title "<type>: <outcome>" --body-file _meta/plans/<slug>/issue-body.md`.

## Report

Summarize: which template, what you grounded the problem in (cite the sources), the acceptance
criteria, which gates you checked and why, and any **OPEN owner decisions**. If a deep build plan is
warranted (non-trivial, multi-deliverable), suggest running **plan** mode next.
