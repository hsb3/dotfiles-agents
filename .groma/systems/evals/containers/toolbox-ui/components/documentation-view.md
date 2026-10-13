---
type: C4 Component
title: Documentation View
description: Stored instructions, references and files of an extender
status: stable
groma:
  id: documentation-view
  parent: toolbox-ui
  technology: React, Carbon
  draft: v1
  code:
    - scanner: react
      file: ui/src/documentation-view.tsx
    - scanner: typescript
      file: ui/src/documentation-view.tsx
---

The Documentation area: the extender search list, and for the chosen extender (or `?extender=<id>`) its entry file, source facts with a safe "Visit source" link, a link to its assessments, its body and its files by role and relpath, each opening its content.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [ui/src/documentation-view.tsx](../../../../../../ui/src/documentation-view.tsx) | [ui/src/api.tsx](../../../../../../ui/src/api.tsx) | Reads extenders and files | function call |

## Derived relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [ui/src/documentation-view.tsx](../../../../../../ui/src/documentation-view.tsx) | [ui/src/api.tsx](../../../../../../ui/src/api.tsx) | Calls imported functions: hashHref, orUnavailable, safeUrl, useSearch; Renders imported components: ExtenderList, PagedList, RecordRegion, SearchForm | typescript |
