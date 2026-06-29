---
name: setup-project-dashboard
description: >-
  Scaffold a `_project-dashboard/` status-dashboard folder into a project that
  doesn't have one yet, from the bundled reference template, then adapt it to the
  project. Use when the user asks to "set up a project dashboard", "create a
  dashboard for this project", "scaffold the dashboard folder", "add a project
  dashboard", "initialize the dashboard pipeline", or runs `/setup-dashboard` —
  and when `update-project-dashboard` finds no existing `_project-dashboard/`.
  Produces the folder + AGENTS.md playbook + starter scripts (numbers → narrative
  → deck → audio brief), which the companion `update-project-dashboard` skill
  then runs. This is the one-time bootstrap; the refresh is a separate skill.
---

# Set Up Project Dashboard

This bootstraps the `_project-dashboard/` pattern into a new project: a static
HTML status board tied to real project data, refreshed through a four-view
pipeline (numbers → narrative → deck → spoken brief), all driven by a
project-local `AGENTS.md` playbook. It copies a proven reference implementation,
then helps adapt it to *this* project.

**This is an adapt-first scaffold, not a drop-in.** The bundled scripts carry a
reference project's doc-scrape patterns, repo slug, and theme. They will *not*
report the right numbers until you point them at this project's repo and docs.
Your job is to lay the template down and then walk the user through the
project-specific knobs — don't pretend the copied dashboard is live yet.

## Step 1 — Check the data source and gather repo intel

The dashboard reports **real data from GitHub**, so before scaffolding, confirm
the prerequisite that makes it worth doing: a GitHub repo with an **issues
board**. Quick check — `gh auth status` (authenticated?) and `gh issue list -L 1`
/ `gh api repos/:owner/:repo/milestones -q length` against the repo this
dashboard will report on.

- **No repo / no issues** → say so. The dashboard would have nothing to show;
  setting up an issues board comes first.
- **Issues but no milestones** → fine, proceed — note that the milestone grid
  will be empty until milestones exist; velocity and throughput still work.
- **Gather the label taxonomy (reusable intel).** Run
  `gh label list --repo OWNER/REPO --limit 100` and note the salient labels —
  the ones worth surfacing as tags/filters (e.g. `bug`, `enhancement`,
  `blocked`, a `priority:`/`severity:` family). This is **one-time** intel: in
  Step 4 you bake the chosen set into the dashboard so every later refresh
  reuses it — no re-discovery. (If you skip this, the dashboard auto-falls-back
  to the board's most common labels, so it still shows useful chips.)
- Also flag the optional tooling now so the user knows what the later steps
  need: `jq` (numbers), Node + a slide renderer + Chromium (deck), and a
  `speak_gemini` voice profile (audio). The deck and audio views are skippable;
  the numbers view is the core.

## Step 2 — Confirm there isn't one already, and pick the location

- Search first so you don't clobber: `fd -H 'AGENTS.md' -p '_project-dashboard' .`.
  If a `_project-dashboard/` already exists, **stop** — this is a setup tool, not
  a re-init. Point the user at `update-project-dashboard` / `/update-dashboard`
  instead.
- Decide where it lives. Keep the directory name **`_project-dashboard`** so the
  refresh skill can find it. Default to the repo root (`./_project-dashboard`).
  If this is a code repo with a separate planning/docs area (or the user keeps a
  sibling planning repo), ask whether it should live there instead — dashboards
  often live in a *planning* repo and read from a sibling *code* repo.

## Step 3 — Copy the bundled template

The template ships with this skill. Resolve it from the skill's base directory
(the path printed when this skill loaded — call it `$BASE`), following symlinks,
then copy the whole tree:

```bash
# $BASE = this skill's base directory (shown on load). Handles symlinked-skill
# and enabled-plugin layouts:
TEMPLATE="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$(realpath "$BASE/SKILL.md")")/../.." && pwd)}"
TEMPLATE="$TEMPLATE/assets/template/_project-dashboard"
ls "$TEMPLATE"            # sanity-check it resolved before copying
cp -R "$TEMPLATE" <destination>/_project-dashboard
```

The tree includes `AGENTS.md`, `gen-dashboard.sh`, `gen-deck.mjs`, `brief.sh`,
`narrative.js`, `DAILY_AUDIO_BRIEF.md`, `project-dashboard.html`, and empty
`archive/ audio/ decks/` dirs. Make the shell scripts executable:
`chmod +x <destination>/_project-dashboard/*.sh`.

## Step 4 — Adapt to this project (the real work)

Open the copied files and resolve every `ADAPT:` marker. Work with the user on
the project-specific knobs — start from the copied **`AGENTS.md`**, which
documents each one:

- **Repo + paths** — replace `OWNER/REPO` (and `OWNER/PLANNING-REPO`) with the
  real GitHub slug(s); set the code-repo path / `DASHBOARD_CODE_REPO` env var so
  `gen-dashboard.sh` runs `gh` against the right repo. If the dashboard lives in
  a planning repo, this is the seam that makes scripts `cd` into the code repo —
  get it right or the dashboard reports the wrong repo's issues.
- **`PROJECT_NAME`** — in the HTML title/headings and deck.
- **Label tags (`TAG_LABELS`)** — in `project-dashboard.html`, set `TAG_LABELS`
  (and `TAG_PREFIXES`/`SEMANTIC_TAGS`) to the salient labels you gathered in
  Step 1, so the board's tags/filters match this project's taxonomy rather than
  the reference project's. This is the reusable intel landing in a durable spot.
  Leaving the default is OK — the dashboard auto-falls-back to the most common
  labels — but baking in the real set makes the chips intentional.
- **Doc scrape targets** — the grep/glyph patterns in `gen-dashboard.sh` assume
  the reference project's docs (story lists, blueprint/checklist sections,
  milestones). Re-point them at this project's docs, or remove the scrapes you
  don't have and let the dashboard run on GitHub signals alone.
- **Milestones / deck labels** — the theme labels and ordering in `gen-deck.mjs`
  assume a specific milestone set; adjust or neutralize.
- **Theme** — `project-dashboard.html` carries reference design tokens; re-mirror
  this project's design system or keep the neutral default.
- **Voice profile** — `brief.sh` names a `speak_gemini` profile; confirm it
  exists or pick the project's.

Don't try to make every scrape perfect in one shot. Get the repo wiring correct
(so GitHub signals are real), neutralize scrapes that don't apply, and leave
clear `ADAPT:` notes for the rest.

## Step 5 — Re-verify prerequisites, then hand off

Close the loop on the gaps you flagged in Step 1: an authed `gh` + `jq` for
numbers; `node` + the deck renderer (and Chromium for PDF) for the deck; the
`speak_gemini` voice profile for audio. Install/build what's needed for the views
the user wants, or note the gaps — don't claim it's ready if a prereq is absent.

Finish by telling the user the scaffold is in place and the first real refresh
runs via **`update-project-dashboard`** / **`/update-dashboard`** — and that the
first pass is where the numbers, narrative, deck, and brief actually get
produced. Report what you created and which `ADAPT:` items still need their
attention.
