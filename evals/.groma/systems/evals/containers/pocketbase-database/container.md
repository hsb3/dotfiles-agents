---
type: C4 Container
title: PocketBase database
description: The 17 collections, users and artifact blobs
status: stable
groma:
  id: pocketbase-database
  parent: evals
  technology: SQLite with file storage
---

The extender inventory, seeded doctrine, eval runs and responses, assessments, curation and harness telemetry (runs, artifacts, run events, tool calls), the `coverage_gaps` view and the `users` auth collection, with protected artifact blobs in file storage. The deployed instance holds verdicts and provenance that cannot be regenerated, so the schema changes only additively.
