---
type: C4 Component
title: Evaluations View
description: Current assessments and job coverage
status: stable
groma:
  id: evaluations-view
  parent: toolbox-ui
  technology: React, Carbon
  code:
    - scanner: react
      file: ui/src/evaluations-view.tsx
    - scanner: typescript
      file: ui/src/evaluations-view.tsx
---

The Evaluations area: the current assessments, for one extender when the route carries `?extender=<id>`, by created, each as `<framework> · <element> · extender <name> · <verdict>; <assessor>; <evidence>; eval run <id>` with the eval run linking to its campaign in Performance; and the current job coverage associations as `Current job association: <job id> · <job name> · eval run <id> · <status> · <disposition>; <rationale>`. A missing value reads `<thing> unavailable`; record text renders as text.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [ui/src/evaluations-view.tsx](../../../../../../ui/src/evaluations-view.tsx) | [ui/src/api.tsx](../../../../../../ui/src/api.tsx) | Reads assessments and coverage | function call |

## Derived relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [ui/src/evaluations-view.tsx](../../../../../../ui/src/evaluations-view.tsx) | [ui/src/api.tsx](../../../../../../ui/src/api.tsx) | Calls imported functions: assessmentsQuery, expandedName, hashHref, orUnavailable; Renders imported component: PagedList | typescript |
