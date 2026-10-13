---
type: C4 System
title: evals
status: stable
groma:
  id: evals
description: Queryable PocketBase projection of the dotfiles-agents extenders and the evidence gathered about them
---
evals reads a dotfiles-agents checkout and the agent harness output, never changes them, and writes one PocketBase database: the extender inventory, the seeded doctrine (frameworks, rubrics, a jobs-to-be-done taxonomy), verdicts joining the two with their evaluation runs, and normalized harness telemetry. It renders two Markdown reports, packages the PocketBase service for deployment on Railway, and ships Toolbox, a read-only browser UI for authenticated readers. The database is a projection, never a source of truth: nothing flows back to the repository.
