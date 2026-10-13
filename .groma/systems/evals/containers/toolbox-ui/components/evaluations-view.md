---
type: C4 Component
title: Evaluations View
description: Current assessments and job coverage
status: draft
groma:
  id: evaluations-view
  parent: toolbox-ui
  technology: React, Carbon
  draft: v1
---

The Evaluations area: assessments (optionally for one extender) with their framework, element, extender, verdict, assessor, evidence and eval run linking to its campaign, and the current job coverage associations.

## Draft relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [evaluations-view](evaluations-view.md) | [api](api.md) | Reads assessments and coverage | function call |
