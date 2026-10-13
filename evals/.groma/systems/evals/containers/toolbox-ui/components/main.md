---
type: C4 Component
title: UI entry
status: stable
groma:
  id: main
  parent: toolbox-ui
  code:
    - scanner: react
      file: ui/src/main.tsx
    - scanner: typescript
      file: ui/src/main.tsx
description: Mounts the Toolbox app
---
The module `ui/index.html` loads. It mounts the Toolbox shell into the page root with Carbon styles.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [ui/src/main.tsx](../../../../../../ui/src/main.tsx) | [ui/src/app.tsx](../../../../../../ui/src/app.tsx) | Mounts the shell | React render |

## Derived relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [ui/src/main.tsx](../../../../../../ui/src/main.tsx) | [ui/src/app.tsx](../../../../../../ui/src/app.tsx) | Renders imported component: App | typescript |
