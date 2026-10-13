---
type: C4 Component
title: Documentation View
description: Stored instructions, references and files of an extender
status: draft
groma:
  id: documentation-view
  parent: toolbox-ui
  technology: React, Carbon
  draft: v1
---

The Documentation area: the extender search list, and for the chosen extender (or `?extender=<id>`) its entry file, source facts with a safe "Visit source" link, a link to its assessments, its body and its files by role and relpath, each opening its content.

## Draft relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [documentation-view](documentation-view.md) | [api](api.md) | Reads extenders and files | function call |
