# Adapter — GitHub Projects (v2)

Backend for the `board-triage` contract (SKILL.md §2) against a GitHub Projects (v2) board. The
whole adapter is one script that ships with this skill: `scripts/github_projects_board.py`, stdlib
only — it shells out to `gh` (`graphql` for the project surface, REST for dependency edges) rather
than holding credentials of its own.

## Prerequisite

`gh` on PATH, authenticated with `project` scope (`gh auth refresh -s project`). A `GITHUB_TOKEN`
env var — common in CI and agent harnesses — takes precedence over the keyring token, and if it
lacks `project` scope every Projects query fails `INSUFFICIENT_SCOPES` while `gh auth status` still
shows a project-scoped login. The script unsets it for every `gh` call it makes; a hand-run `gh`
needs `env -u GITHUB_TOKEN gh …`.

## Key

The **issue number**. Durable across item removal and re-add, unlike the project item id, which is
minted fresh each time an item is added; apply re-maps number → item id from a fresh pull every
run, so a stale changeset cannot write to the wrong item. Draft issues have no number and are
dropped from the snapshot.

## Export

```bash
S="${CLAUDE_PLUGIN_ROOT}/skills/board-triage/scripts"
python3 "$S/github_projects_board.py" export -o acme -n 8 --out board-snapshot.json
```

Prints `<n> items (<n> untriaged) -> board-snapshot.json`, the untriaged count only when the board
has a Priority field; without `--out` the snapshot goes to stdout and there is no count line. Add
`--owner-type org` for an org-owned board (default `user`). The snapshot's top-level `fields` block
carries the legal values for every single-select and iteration field, so triage needs no second read
command; text, number, and date fields get a format hint (`<text>`, `<number>`, `YYYY-MM-DD`) there
instead, since their legal values are not an enumerable set.

## Apply

```bash
python3 "$S/github_projects_board.py" apply -o acme -n 8 --changeset changeset.tsv            # dry-run
python3 "$S/github_projects_board.py" apply -o acme -n 8 --changeset changeset.tsv --apply    # write
python3 "$S/github_projects_board.py" apply -o acme -n 8 --changeset edges.tsv --repo acme/widgets --apply
```

Dry-run by default. One line per row on stdout (`DRY   would set #<key> priority=P1 (was None)`, `OK`
already at target, `SET` written, `FAIL` errored), with unresolvable rows printing as `SKIP` on
stderr next to the tally. Only differing cells are written, so re-runs are free; exit 1 if any row
FAILed or SKIPped, the resolvable rows still apply.
The dry run resolves every value against the live fields before previewing it, so it exits
non-zero on a row the write would reject rather than promising a change that cannot land. Blank lines and `#` comments are ignored, and a header row is dropped whether its first
column reads `key` or `issue`. `--repo` is needed only for `blocked_by` / `blocking` rows. Pass the
same `--owner-type` you exported with — the snapshot does not record it.

## Field map

| Rubric output | Board field | Values |
|---|---|---|
| Priority band | `Priority` | single-select `P0` `P1` `P2` `P3` |
| Impact | `Impact` | single-select `High` `Medium` `Low` |
| Effort | `Effort` | single-select `S` `M` `L` `XL` |
| Grouping | `Workstream` | single-select, the board's own options (e.g. `backend` `frontend` `data` `infra` `meta`) |
| Ready lane | `Status` (built-in) | `Backlog` `Up Next` `In Progress` `In Review` `Blocked` `Done` — `Up Next` is the ready lane |
| Time | `Iteration` / `Start` / `Target` | iteration title / `YYYY-MM-DD` dates |
| — | `Estimate` | number; optional capacity, not a rubric output |

Nothing in the rubric is unmapped here. Field tokens resolve case-, space-, and
underscore-insensitively against live field names (`est_effort` finds `Est Effort`); single-select
and iteration values match option **names**, case-insensitively. **These fields exist only if the
board was built with them** — against a board with no Impact field, apply prints `SKIP … no
field matches 'impact'` rather than inventing one; provision them once, below.

`blocked_by` / `blocking` are not project cells at all: they route to the REST
issue-dependencies endpoint and need `--repo`. Labels, Milestone, and Assignees are
issue-native and not settable through the project API — they are absent from the `fields` block
and from each item's `fields` grid, and apply names the refusing dataType. Each item still
carries its `labels`, `milestone`, and `parent` as plain read-only context.

## Provisioning

### Project

Once, before anything else: create the project and note the printed number as `PN`.

```bash
gh project create --owner "@me" --title "Engineering"
```

### Fields

Once per board, only for what it does not already carry. Keep single-select labels **comma-free**
— the `gh` CLI splits `--single-select-options` on commas.

```bash
PN=<project-number>; OWNER="@me"
gh project field-create $PN --owner "$OWNER" --name "Priority"   --data-type SINGLE_SELECT --single-select-options "P0,P1,P2,P3"
gh project field-create $PN --owner "$OWNER" --name "Impact"     --data-type SINGLE_SELECT --single-select-options "High,Medium,Low"
gh project field-create $PN --owner "$OWNER" --name "Effort"     --data-type SINGLE_SELECT --single-select-options "S,M,L,XL"
gh project field-create $PN --owner "$OWNER" --name "Workstream" --data-type SINGLE_SELECT --single-select-options "backend,frontend,data,infra,meta"
gh project field-create $PN --owner "$OWNER" --name "Estimate"   --data-type NUMBER
gh project field-create $PN --owner "$OWNER" --name "Start"      --data-type DATE
gh project field-create $PN --owner "$OWNER" --name "Target"     --data-type DATE
```

`Status` is built in, and the `gh` CLI cannot edit an existing field's options — that is GraphQL.
**`updateProjectV2Field` replaces the whole option set: an option you do not re-pass with its `id`
is deleted and every item assigned to it is orphaned.** Read the current options first, echo back
the ids you keep, omit `id` only on genuinely new ones; that is also the safe *rename* — keep the
id, change the name, every assignment follows. `name`, `color`, `description` are required per
option (`description` may be `""`), list order is display order, colors are
`GRAY BLUE GREEN YELLOW ORANGE RED PINK PURPLE`.

```bash
gh api graphql -f query='mutation($f:ID!){ updateProjectV2Field(input:{ fieldId:$f, singleSelectOptions:[
  {id:"<TODO_ID>",       name:"Backlog",     color:GRAY,   description:"Captured; not triaged"},
  {                      name:"Up Next",     color:BLUE,   description:"Triaged; ready"},
  {id:"<INPROGRESS_ID>", name:"In Progress", color:YELLOW, description:"Actively being worked"},
  {                      name:"In Review",   color:ORANGE, description:"PR open / awaiting review"},
  {                      name:"Blocked",     color:RED,    description:"Open blocked-by or external gate"},
  {id:"<DONE_ID>",       name:"Done",        color:PURPLE, description:"Closed with evidence"}
]}){ projectV2Field{ ... on ProjectV2SingleSelectField { options{ id name } } } } }' -f f="<STATUS_FIELD_ID>"
```

An ITERATION field is GraphQL-only too: create it with zero buckets, then generate them. **Each
iteration object requires a `title`** (plus `startDate`, `duration`) or the update fails.

```bash
gh api graphql -f query='mutation($p:ID!){ createProjectV2Field(input:{ projectId:$p,
  dataType: ITERATION, name:"Iteration", iterationConfiguration:{
    startDate:"2026-06-15", duration:14, iterations:[] } }){
  projectV2Field{ ... on ProjectV2IterationField { id } } } }' -f p="<PROJECT_NODE_ID>"
gh api graphql -f query='mutation($f:ID!){ updateProjectV2Field(input:{ fieldId:$f,
  iterationConfiguration:{ startDate:"2026-06-15", duration:14, iterations:[
    {title:"Sprint 1", startDate:"2026-06-15", duration:14},
    {title:"Sprint 2", startDate:"2026-06-29", duration:14} ] } }){
  projectV2Field{ ... on ProjectV2IterationField { configuration{ iterations{ title } } } } } }' -f f="<ITERATION_FIELD_ID>"
```

Placeholder ids come from introspection: project node id, then fields with their option ids.

```bash
gh api graphql -f query='{ user(login:"<OWNER>"){ projectV2(number:<PN>){ id } } }'
gh api graphql -f query='{ node(id:"<PROJECT_NODE_ID>"){ ... on ProjectV2 { fields(first:50){ nodes{
  ... on ProjectV2FieldCommon{ id name } ... on ProjectV2SingleSelectField{ id name options{ id name } } } } } } }'
```

## Seeding items

`export`/`apply` operate on items already in the project — they don't add new ones. Add existing
issues once the project and fields exist:

```bash
gh project item-add $PN --owner "$OWNER" --url https://github.com/acme/widgets/issues/42
gh project item-list $PN --owner "$OWNER" --format json --limit 400   # inspect what's already added
```

## Sub-issues

Decomposing an epic is REST, not a project field — same shape as the `blocked_by` call above,
keyed on the child's **numeric** issue id:

```bash
gh api -X POST repos/acme/widgets/issues/<parent>/sub_issues -F sub_issue_id=<child numeric id>
```

No Gantt arrows in native Projects: sub-issues plus `blocked_by` in the issue sidebar, and a
Dependencies view (below), are the substitute.

## Views (UI-only) + workflows (UI-only)

No mutation creates or edits either — build these once by hand, in **+ New view** and project
⋯ → **Workflows**. A starter set:

| View | Layout | Filter | Group / Sort |
|---|---|---|---|
| Now / critical path | Board | `priority:P0` | by Status |
| Roadmap | Roadmap | `-status:Done` | dates Start→Target, group by Milestone |
| Dependencies | Table | `is:open` | show sub-issues; surface Blocked |
| Prioritization | Table | `no:Priority` then `-status:Done` | sort Impact↓, Effort↑ |
| By Epic | Board | `is:open` | column = Parent issue |
| Working board | Board | `iteration:@current` | by Status |

Workflow toggles (project ⋯ → Workflows, no code): item added → `Backlog`; item reopened → `In
Progress`; item closed → `Done`; PR merged → `Done`; auto-add `is:issue is:open`; auto-archive
`status:Done` closed > 2 wks. Cross-repo or label-driven automation instead uses a GitHub Action
with `actions/add-to-project`.

## Status update banner

A project-level status update (the project's overview page, not a per-item field):

```bash
gh api graphql -f query='mutation($p:ID!,$b:String!){ createProjectV2StatusUpdate(input:{
  projectId:$p, body:$b, status:ON_TRACK }){ statusUpdate{ id } } }' \
  -f p="<PROJECT_NODE_ID>" -f b="<markdown>"
```

`status` ∈ `INACTIVE ON_TRACK AT_RISK OFF_TRACK COMPLETE`. This is a board write — confirm
before sending. Pass the body as the `$b` variable rather than inlining it: a status update is
markdown, and inlining it into the query string breaks on the first quote.

## Notes verified against a live board

- **Capability, verified live against the GitHub GraphQL API 2026-06-18:** everything above is
  scriptable, including the two things widely believed to be UI-only (single-select option edits,
  iteration fields). Genuinely UI-only is narrow — **views and workflows**: no create/update
  mutation exists for a view, and the only workflow mutation is `deleteProjectV2Workflow`. Triage
  touches neither. Re-verify by listing the mutations GitHub actually publishes:
  `gh api graphql -f query='{__type(name:"Mutation"){fields{name}}}'` with
  `--jq '.data.__type.fields[].name | select(test("ProjectV2"))'`.
- **Status ladder semantics**, which the Ready-lane row rests on: `Backlog` = captured, not ready ·
  `Up Next` = triaged and ready · `In Progress` = actively worked · `In Review` = PR open, awaiting
  review · `Blocked` = a real `blocked_by` edge or external gate, **not** "haven't started" ·
  `Done` = closed with evidence.
- `blocked_by` takes the blocker's **numeric issue id**, not its `#number`. A changeset row carries
  the number and the script resolves it (`gh api repos/<repo>/issues/<n> --jq .id`); a hand-run
  `gh api -X POST repos/<repo>/issues/<n>/dependencies/blocked_by -F issue_id=<id>` needs the id.
- `no:Priority` is the board-UI filter for untriaged items — the set the export count names.
- `CLOSED` and `MERGED` both map to `state: "done"`; any state the API grows later falls back to
  `"open"`, since an item wrongly marked done vanishes from triage silently.
