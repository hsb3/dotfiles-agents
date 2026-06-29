---
name: update-project-dashboard
description: >-
  Run a project's dashboard-update pass by finding and faithfully following its
  own `_project-dashboard/AGENTS.md` playbook. Use this whenever the user asks to
  "update the dashboard", "refresh the project dashboard", "regenerate the
  dashboard", "run the dashboard update/pass", "redo the deck", "cut the audio
  brief", or runs `/update-dashboard` — even if they don't name the AGENTS.md
  file. The project's AGENTS.md is the source of truth for the exact steps,
  scripts, ordering, and gotchas; this skill is the generic harness that locates
  it, reads it in full, and executes the complete pass in order across any
  project that follows the `_project-dashboard/` pattern. If a project has no
  dashboard yet, use the companion `setup-project-dashboard` skill first.
---

# Update Project Dashboard

A project's dashboard is refreshed by running a fixed pipeline — pull live
numbers, write the judgment narrative, render the deck, cut the spoken brief, or
whatever variant that project defines. The exact commands, the order, the cwd
each script needs, the hand-authored steps, and the easy-to-miss closing moves
all live in that project's **`_project-dashboard/AGENTS.md`**.

**This skill does not hard-code any of that.** It is the generic harness: find
the playbook, read it completely, and run the pass faithfully. The AGENTS.md is
the source of truth — when it disagrees with anything below, follow the AGENTS.md.
That separation is what lets one skill drive dashboards across many projects.

## Step 1 — Locate the playbook

Find the project's dashboard instructions. From the repo root:

```bash
fd -H 'AGENTS.md' -p '_project-dashboard' . 2>/dev/null || \
  find . -path '*/_project-dashboard/AGENTS.md' -not -path '*/node_modules/*'
```

- **One match** → that's the playbook. Note its directory; most scripts must run
  from there.
- **Several matches** → pick the one for the dashboard the user means; if it's
  ambiguous, ask which project.
- **None** → the project may not have a dashboard yet, or names it differently.
  First search for a likely `dashboard`/`status` directory with an `AGENTS.md`
  or `README.md` of update steps. If there genuinely isn't one, don't invent a
  pipeline — offer to scaffold one with the **`setup-project-dashboard`** skill
  (`/setup-dashboard`), then come back and run the pass.

## Step 2 — Read it completely, then build the step list

Read the **entire** AGENTS.md before running anything — it carries location
caveats, prerequisites, and "don't do X" warnings that only make sense in full.
From it, extract:

- The **ordered list of steps** (often under a "Refreshing"/"Update" heading).
- For each step: the **exact command**, the **directory** to run it from, and
  whether it's a **script** or a **hand-authored / reasoning** step.
- **Prerequisites** (authed CLIs, built packages, browsers, voice profiles, env
  vars) and **gotchas** (re-stamp steps, fragile scrapes, cwd that resolves a
  *sibling* repo, etc.).

## Step 3 — Run the full pass, in order

**"Update the dashboard" means the complete pass — every step the playbook
lists, in its order — not just the first artifact.** The steps form a pipeline
where each feeds the next (numbers → narrative → deck → brief, or whatever the
doc defines); stopping early ships an internally inconsistent dashboard. Only do
a subset when the user explicitly scopes you (see [Scoping](#scoping)).

As you go:

- **Run each script from the directory the doc specifies.** Dashboards commonly
  live in a *planning* repo while the scripts `cd` into a sibling *code* repo —
  running from the wrong cwd silently reports the wrong project. Honor the doc's
  cwd and env-var overrides exactly.
- **Hand-authored steps need judgment, not a script.** When a step is marked
  manual/agent-authored (a narrative, a briefing, a spoken script), actually do
  the reasoning the doc asks for — read the derived data, cross-check the
  source/enablement docs it points to, write the prose, and bump any
  `authoredAt`/date field to **today's real date**. Don't skip it or paste a
  placeholder.
- **Check prerequisites before running**, and if one is missing (CLI not authed,
  package not built, browser absent), surface it and either fix it per the doc
  or pause — don't push through and emit a partial/empty artifact.
- **Dated outputs use today's actual date** (`YYYYMMDD` files, `decks/…`,
  `audio/…`). Use the real current date, not a guess.

## Step 4 — Honor the closing and verification steps

Playbooks often end with a step that's easy to drop because it looks redundant —
a re-run that re-stamps a pointer, a doctor/validate check, a snapshot. These
exist because of ordering effects (e.g. an artifact authored *after* the data
step won't be linked until the data step runs again). **Do the closing step the
doc calls for** — the pass isn't done at the last *new* artifact, it's done when
the doc's final instruction is satisfied.

## Step 5 — Report what changed

Summarize: which steps ran, which artifacts were produced or overwritten (with
paths), and — explicitly — anything you **skipped or couldn't complete** and
why (missing prereq, user-scoped subset). Faithful reporting matters more than a
clean-looking summary: if a step failed or was skipped, say so plainly rather
than implying the dashboard is fully fresh.

## Disciplines that carry across projects

These hold regardless of which project's AGENTS.md you're following:

- **The playbook outranks this skill and your memory.** Re-read it each run; it
  changes. Don't run a command from last time that the doc no longer lists.
- **Order is load-bearing.** Later steps consume earlier outputs. Don't
  parallelize or reorder unless the doc says they're independent.
- **Default to the full pass; treat partial as the exception** the user must ask
  for.
- **Manual steps are the point, not overhead** — they're where the judgment that
  a dashboard exists to convey actually gets added.
- **Wrong-cwd and stale-pointer bugs are the common failure modes.** Watch the
  directory each script runs in, and the closing re-stamp.

## Scoping

If the user scopes you to one part — "just refresh the numbers", "only redo the
deck", "re-cut the audio brief" — run only that step (plus any closing/re-stamp
step the doc ties to it), and note in your report that this was a partial pass
so the other views may now be a step behind.
