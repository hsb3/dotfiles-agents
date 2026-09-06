# github-project-board

Stand up and operate a single GitHub Project (v2) board that serves timeline,
prioritization, and day-to-day task management from one item set sliced into many views —
create the project and fields (including iteration), edit single-select options without
orphaning items, seed field values plus sub-issue/blocked-by dependencies, and run the
weekly triage cadence.

## When it triggers

Use it when setting up a new project board, migrating an ad-hoc planning doc or spreadsheet
onto a board, deciding the field/view model, or scripting bulk board changes (triage,
dependencies, status/iteration assignment) in any repo. Knows what's scriptable via the
GitHub CLI/GraphQL versus what's genuinely UI-only (views and workflows), and the
field-vs-derived-signal discipline that keeps a board from drifting.

## Install

```
claude plugin install solo-skills@dotfiles-agents
```

Ships in the `solo-skills` bundle.
