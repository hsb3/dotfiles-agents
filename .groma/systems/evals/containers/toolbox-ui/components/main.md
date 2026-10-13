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
  draft: v1
description: Mounts the Toolbox app
---
The module `ui/index.html` loads. It mounts the Toolbox shell into the page root with Carbon styles.

## Draft relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [main](main.md) | [app](app.md) | Mounts the shell | React render |
