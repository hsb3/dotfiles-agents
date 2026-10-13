---
type: C4 Actor
title: Toolbox reader
description: Authenticated browser user of the Toolbox UI
status: stable
groma:
  id: toolbox-reader
---

Signs in with an account the owner created and browses the catalog, documentation, evaluations and recorded runs, comparing a baseline run with a with-configuration run. Can read but never write.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [toolbox-reader](toolbox-reader.md) | [toolbox-ui](../systems/evals/containers/toolbox-ui/container.md) | Browses catalog and evidence | HTTPS, browser |
