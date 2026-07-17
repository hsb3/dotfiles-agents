---
name: github-project-board
description: >-
  Stand up and operate a single GitHub Project (v2) board that serves timeline,
  prioritization, and day-to-day task management from one item set sliced into many
  views — create the project + fields (including ITERATION), edit single-select
  options without orphaning items, seed field values + sub-issue/blocked-by
  dependencies, and run the weekly triage cadence. Knows exactly what is scriptable
  via gh/GraphQL vs what is genuinely UI-only (views + workflows), and the field-vs-
  derived-signal discipline that keeps a board from drifting. Use when setting up a
  new project board, migrating an ad-hoc planning doc/sheet onto a board, deciding
  the field/view model, or scripting bulk board changes (triage, dependencies,
  status/iteration assignment) in any repo.
version: 0.1.0
---

# github-project-board — one project, many views

Build and run a GitHub Project (v2) as the **single source of truth** for what's being worked on,
in what order, and why. The principle: **don't make three boards. Make one project with one set of
fields, sliced into multiple *views*.** Same items, different lenses; change a field once, every
view updates.

Capability matrix verified live against the GitHub GraphQL API 2026-06-18. Re-verify with the
introspection queries in §6 if GitHub's surface has moved.

---

## 1. Capability matrix — what is scriptable (read FIRST)

The pervasive myth is that option edits and iteration fields are UI-only. **They are not.** What is
genuinely UI-only is narrow: **views and workflows.** Everything else an agent can do.

| Capability | Scriptable? | How |
|---|---|---|
| Create the project | YES | `gh project create` / `createProjectV2` |
| Create text / number / date / single-select fields | YES | `gh project field-create` / `createProjectV2Field` |
| Create an **Iteration** field | YES (GraphQL only) | `createProjectV2Field` `dataType: ITERATION` + `iterationConfiguration` |
| Generate / edit iteration buckets | YES (GraphQL only) | `updateProjectV2Field` `iterationConfiguration` — each iteration needs a `title` |
| Add / rename / reorder single-select options | YES (GraphQL only) | `updateProjectV2Field` `singleSelectOptions` — **re-pass existing ids to preserve** |
| Add items, set / clear field values | YES | `gh project item-add` / `updateProjectV2ItemFieldValue` / `clearProjectV2ItemFieldValue` |
| Sub-issues (decompose) + blocked-by (sequence) | YES | `gh issue` flags / REST `…/sub_issues` + `…/dependencies/blocked_by` |
| Project **status update** banner | YES | `createProjectV2StatusUpdate` |
| **Views** (create / layout / filter / sort / group) | **NO** | **UI only** — no create/update mutation (the `views` field is read-only) |
| **Workflows** (built-in automations) | **NO** | **UI only** — only `deleteProjectV2Workflow` exists |

The `gh project` CLI covers create / field-create / item-*, but has **no** command for editing
single-select options or creating iteration fields — those need `gh api graphql`. There is no
`gh project view`/`workflow` subcommand. The GitHub web app drives views/workflows through private
internal mutations not in the published schema, so "the website can do it" ≠ the public API can.

---

## 2. Three gotchas that will bite you

1. **`GITHUB_TOKEN` shadowing.** A `GITHUB_TOKEN` env var (common in CI and agent harnesses) takes
   precedence over the keyring token. If it lacks `project` scope, every Projects query fails
   `INSUFFICIENT_SCOPES` even though `gh auth status` shows a project-scoped keyring login. Fix:
   prefix commands with `env -u GITHUB_TOKEN gh ...` to fall back to the keyring token. A human's
   interactive shell usually has no such env var, so plain `gh` works for them — this is mostly an
   agent problem.
2. **Option edits delete what you omit.** `updateProjectV2Field` with `singleSelectOptions` replaces
   the whole option set. An existing option you DON'T re-pass (with its `id`) is **deleted**, and
   every item assigned to it is orphaned. Always read the current options first and echo back the
   ids you keep. This is also the *safe rename*: keep the id, change the name — every assigned item
   migrates. (Renaming `Todo`→`Backlog` this way preserves all existing assignments.)
3. **Iteration buckets require a `title`.** `createProjectV2Field` with `iterations:[]` makes the
   field with zero buckets; generating buckets via `updateProjectV2Field` fails unless each
   iteration object includes `title` (plus `startDate`, `duration`).

---

## 3. Field model + triage rubric

Keep single-select labels **comma-free** (the `gh` CLI splits options on commas).

| Field | Type | Options / format | Purpose |
|---|---|---|---|
| **Status** | single-select (built-in) | `Backlog` `Up Next` `In Progress` `In Review` `Blocked` `Done` | Kanban flow |
| **Priority** | single-select | `P0` `P1` `P2` `P3` | The triage decision |
| **Impact** | single-select | `High` `Medium` `Low` | Triage input (value) |
| **Effort** | single-select | `S` `M` `L` `XL` | Triage input (cost) |
| **Workstream** | single-select | e.g. `backend` `frontend` `data` `infra` `meta` | Group/filter; map from `workstream:*` labels |
| **Estimate** | number | points or days | Optional capacity |
| **Start** / **Target** | date | — | Roadmap bar start / end |
| **Iteration** | iteration | 1–2 wk cadence | Sprint bucket |

No formula fields exist, so **Priority is set by hand** from Impact × Effort:

| | Effort S/M | Effort L/XL |
|---|---|---|
| **Impact High** | **P0–P1** (do first) | **P1–P2** (plan / decompose) |
| **Impact Low** | **P2–P3** (fill-in) | **P3** (probably don't) |

Override for a **dated critical path** (demo / stage gate): force **P0** regardless of effort.

### Status semantics (the workflow ladder)
Backlog = captured, not ready · Up Next = triaged + ready (Definition of Ready met) · In Progress =
actively worked · In Review = PR open / awaiting review · Blocked = real `blocked-by` edge or
external gate (NOT "haven't started") · Done = closed with evidence.

---

## 4. What earns a field — derived signals vs. hand-maintained fields

Before adding any field, apply this test: **a field earns its place only if it is a JUDGMENT state
that can't be derived from a system of record AND you will filter or sort on it.** Anything
derivable (filesystem, CI, issue body, another field) should be *derived*, not hand-maintained — a
hand-kept field silently drifts the moment you forget, and "we'll remember to update it" is the
exact failure the board exists to prevent. The fix is a **derived or enforced** signal, not a
manual flag. Two recurring temptations:

- **"Has a plan / spec been written?"** — *derivable* (does the plan file/folder exist?). Don't
  hand-maintain a checkbox. **Report** it from a script, or — to make it filterable on the board —
  **sync** it from the source with a drift guard (single source + generator + a test that fails on
  drift). Never a manual checkbox.
- **"Is this fully scoped / ready?"** — this is your **Definition of Ready**, and it is *already*
  the entry gate of the Status ladder (`Backlog` → `Up Next`). Encode "scoped (+ a plan if it needs
  one)" as the written criterion for entering Up Next and enforce it at triage. Use a
  `needs-scoping` **label** only if you want to *filter the backlog* for un-scoped items — a label
  serves that better than a field.

**Rule of thumb:** Status = workflow state; Priority/Impact/Effort = the triage decision;
Iteration/Start/Target = time. Everything else should be derivable, gate-enforced, or it doesn't
belong as a hand-maintained field. A required field is a cell to fill on every triage — that cost
is real, and works against "triage is cheap and frequent."

---

## 5. Setup procedure

Replace the `<…>` placeholders. Get the project node id + field ids with the introspection in §6.

### 5a. Project + simple fields (gh CLI)
```bash
gh auth refresh -s project                  # grant Projects read+write (keyring)
gh project create --owner "@me" --title "Engineering"     # note the printed number
PN=<number>; OWNER="@me"
gh project field-create $PN --owner "$OWNER" --name "Priority"   --data-type SINGLE_SELECT --single-select-options "P0,P1,P2,P3"
gh project field-create $PN --owner "$OWNER" --name "Impact"     --data-type SINGLE_SELECT --single-select-options "High,Medium,Low"
gh project field-create $PN --owner "$OWNER" --name "Effort"     --data-type SINGLE_SELECT --single-select-options "S,M,L,XL"
gh project field-create $PN --owner "$OWNER" --name "Workstream" --data-type SINGLE_SELECT --single-select-options "backend,frontend,data,infra,meta"
gh project field-create $PN --owner "$OWNER" --name "Estimate"   --data-type NUMBER
gh project field-create $PN --owner "$OWNER" --name "Start"      --data-type DATE
gh project field-create $PN --owner "$OWNER" --name "Target"     --data-type DATE
```

### 5b. Edit built-in Status options (GraphQL — append-safe)
Re-pass every kept option WITH its id (preserves assignments + renames safely); add new ones
without an id; list order = display order. Colors: `GRAY BLUE GREEN YELLOW ORANGE RED PINK PURPLE`.
`name`, `color`, `description` are required per option (`description` may be `""`).
```bash
gh api graphql -f query='mutation($f:ID!){ updateProjectV2Field(input:{ fieldId:$f, singleSelectOptions:[
  {id:"<TODO_ID>",       name:"Backlog",     color:GRAY,   description:"Captured; not triaged"},
  {                      name:"Up Next",     color:BLUE,   description:"Triaged; ready (DoR met)"},
  {id:"<INPROGRESS_ID>", name:"In Progress", color:YELLOW, description:"Actively being worked"},
  {                      name:"In Review",   color:ORANGE, description:"PR open / awaiting review"},
  {                      name:"Blocked",     color:RED,    description:"Open blocked-by or external gate"},
  {id:"<DONE_ID>",       name:"Done",        color:PURPLE, description:"Closed with evidence"}
]}){ projectV2Field{ ... on ProjectV2SingleSelectField { options{ id name } } } } }' -f f="<STATUS_FIELD_ID>"
```

### 5c. Iteration field (GraphQL — gh CLI can't)
```bash
# create (zero buckets):
gh api graphql -f query='mutation($p:ID!){ createProjectV2Field(input:{ projectId:$p,
  dataType: ITERATION, name:"Iteration",
  iterationConfiguration:{ startDate:"2026-06-15", duration:14, iterations:[] } }){
  projectV2Field{ ... on ProjectV2IterationField { id } } } }' -f p="<PROJECT_NODE_ID>"
# generate buckets (title REQUIRED per iteration):
gh api graphql -f query='mutation($f:ID!){ updateProjectV2Field(input:{ fieldId:$f,
  iterationConfiguration:{ startDate:"2026-06-15", duration:14, iterations:[
    {title:"Sprint 1", startDate:"2026-06-15", duration:14},
    {title:"Sprint 2", startDate:"2026-06-29", duration:14}
  ] } }){ projectV2Field{ ... on ProjectV2IterationField { configuration{ iterations{ title } } } } } }' -f f="<ITERATION_FIELD_ID>"
```

### 5d. Seed items + values
```bash
gh project item-add $PN --owner "$OWNER" --url https://github.com/you/repo/issues/42
# single-select value:
gh api graphql -f query='mutation($p:ID!,$i:ID!,$f:ID!,$o:String!){ updateProjectV2ItemFieldValue(
  input:{ projectId:$p, itemId:$i, fieldId:$f, value:{ singleSelectOptionId:$o } }){ projectV2Item{ id } } }' \
  -f p="<PROJECT_NODE_ID>" -f i="<ITEM_ID>" -f f="<FIELD_ID>" -f o="<OPTION_ID>"
# other value shapes: value:{ iterationId:"…" } · value:{ date:"2026-06-15" } · value:{ number:3 } · value:{ text:"…" }
```
Build an issue-number → item-id map first: `gh project item-list $PN --owner $OWNER --format json --limit 400`.
Mutations are idempotent — safe to re-run.

### 5e. Dependencies (native relationships, not a field)
```bash
gh api -X POST repos/OWNER/REPO/issues/<blocked>/dependencies/blocked_by -F issue_id=<blocker NUMERIC id>
# verify: GET the same path → [{number,id},…].  (issue_id is the blocker's numeric .id, NOT its #number)
```
Decompose epics with sub-issues; sequence with blocked-by. No Gantt arrows in native Projects —
sub-issues + blocked-by in the sidebar + a Dependencies table are the substitute.

---

## 6. Introspection (read ids; re-verify capabilities)
```bash
# project node id by number:
gh api graphql -f query='{ user(login:"<OWNER>"){ projectV2(number:<PN>){ id } } }'
# fields + single-select option ids:
gh api graphql -f query='{ node(id:"<PROJECT_NODE_ID>"){ ... on ProjectV2 { fields(first:50){ nodes{
  ... on ProjectV2FieldCommon{ id name } ... on ProjectV2SingleSelectField{ id name options{ id name } } } } } } }'
# re-verify scriptability (which mutations exist):
gh api graphql -f query='{ __type(name:"Mutation"){ fields{ name } } }' --jq '.data.__type.fields[].name | select(test("ProjectV2"))'
```

---

## 7. Views (UI-only) + Workflows (UI-only)

Build with **+ New view**; set layout; paste the filter (issue-search query language). A starter set:

| View | Layout | Filter | Group / Sort |
|---|---|---|---|
| Now / critical path | Board | `priority:P0` | by Status |
| Roadmap | Roadmap | `-status:Done` | dates Start→Target, group by Milestone |
| Dependencies | Table | `is:open` | show sub-issues; surface Blocked |
| Prioritization | Table | `no:Priority` then `-status:Done` | sort Impact↓, Effort↑ |
| By Epic | Board | `is:open` | column = Parent issue |
| Working board | Board | `iteration:@current` | by Status |

Project → ⋯ → **Workflows** (toggles, no code): Item added → `Backlog`; Item reopened → `In
Progress`; Item closed → `Done`; PR merged → `Done`; Auto-add `is:issue is:open`; Auto-archive
`status:Done` closed > 2 wks. For cross-repo / label-driven automation, use a GitHub Action with
`actions/add-to-project`.

> **Tip:** since views + workflows are the only manual steps, an effective hand-off is to script
> everything else, then hand the owner a short click-by-click guide (e.g. a deck-builder deck or a
> markdown checklist) for just those two.

**Filter cheatsheet:** `status:"In Progress"` · `status:"Up Next","In Progress"` (OR) ·
`-status:Done` · `no:Priority` (untriaged) · `iteration:@current` (also `@previous`/`@next`) ·
`is:open`/`is:issue`/`is:pr` · `assignee:@me` · `label:bug`.

---

## 8. Operating cadence
- **Daily:** open the focus view; pull top P0/P1 from Up Next → In Progress.
- **Per sprint (1–2 wks):** run the Prioritization exercise (set Impact/Effort/Priority on
  `no:Priority`; promote ready P0/P1 → Up Next + assign the Iteration); glance at Roadmap.
- **Weekly:** check Dependencies for items whose blocker just closed; unblock / re-sequence.
- **Cut over:** once the board is seeded, retire any parallel status table — the board is truth.

---

## 9. Collaboration loop — export → analyze → apply

When the analyst can't read the board compactly (e.g. a chat/agent harness where listing
items returns full issue bodies and overflows the context), **split the work across the seam
where auth lives.** The local side (human or repo agent, with `gh`) does the I/O; the analyst
does the judgment over a clean snapshot; every change lands as a reviewable diff. (The three
scripts ship in this skill's `scripts/` dir — in an installed Claude Code plugin that is
`${CLAUDE_PLUGIN_ROOT}/skills/github-project-board/scripts/`; outside the harness, resolve
`scripts/` relative to wherever this skill is installed.)

Three artifacts, three contracts:

1. **Snapshot** — `scripts/board-export.py` emits compact JSON: `project`, `fields` (with option
   + iteration ids), and `items[{number, item_id, title, state, labels[], milestone, parent,
   fields{}}]`. `fields{}` is a **complete grid of every operating field** (single-select / text /
   number / date / iteration), `null` when unset — so blanks are visible for triage. **No issue
   bodies** — labels/milestone/parent carry the signal; deep context comes from the repo's
   plan/spec files, not the board.
2. **Changeset** — the analyst emits a **TSV diff**, one row per cell to change (NOT the whole
   board): `issue<TAB>field<TAB>value`. Keyed on **issue number** (human-readable, stable across
   item re-adds); `value` is the **option name** for single-selects; an **empty value clears**
   the field; the pseudo-fields `blocked_by` / `blocking` route to the native dependencies
   endpoint (`value` = blocker issue number, needs `--repo`).
3. **Apply** — `scripts/board-apply.py` re-pulls a fresh snapshot, resolves each changeset
   `field` token against the board's **live fields** (any current/future field; non-settable
   built-ins like Labels/Milestone are skipped), writes **only cells that differ** from current,
   is **dry-run by default**, idempotent (re-runs are free), and exits non-zero on any failure.

To see the valid field names + option values a changeset may use, run
`scripts/board-fields.py -o <owner> -n <number>` (the enum reference; details in §6).

```bash
S="${CLAUDE_PLUGIN_ROOT}/skills/github-project-board/scripts"   # this skill's scripts dir
# 1. local side exports (GITHUB_TOKEN is unset inside the scripts to dodge the shadowing gotcha)
python3 "$S/board-export.py" -o hsb3 -n 8 --out board-snapshot.json
# 2. analyst reads board-snapshot.json, writes changeset.tsv (issue / field / value)
# 3. local side previews, then applies
python3 "$S/board-apply.py" -o hsb3 -n 8 --changeset changeset.tsv            # dry-run diff
python3 "$S/board-apply.py" -o hsb3 -n 8 --changeset changeset.tsv --apply    # write
python3 "$S/board-apply.py" -o hsb3 -n 8 --changeset edges.tsv --repo <owner>/acme-platform --apply
```

**Why issue-number keys, not item-ids:** item-ids change if an item is removed and re-added;
the issue number is the durable handle, and `board-apply` re-maps number→item-id from a fresh
pull every run, so a stale changeset never writes to the wrong item.

**Generalizes:** the same loop drives triage (Impact/Effort/Priority), status moves, iteration
and date assignment, and dependency edges — anything that's one cell per row. This is the weekly
cadence (§8) made concrete: export Monday → diff → apply.
