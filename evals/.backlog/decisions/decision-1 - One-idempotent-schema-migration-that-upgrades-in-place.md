---
id: decision-1
title: One idempotent schema migration that upgrades in place
date: '2026-10-13 03:15'
status: accepted
---
## Context

The deployed database was built through the REST API by the previous tooling, holds all 17 collections without the three v1 additions, and has none of this repository's migrations recorded. The same migrations must also build an empty database and change nothing on a migrated one. PocketBase's generated snapshot migrations recreate collections from a full JSON export, which would not keep the legacy field ids.

## Decision

A single hand-written JavaScript migration (`pb_migrations/1767225600_evals_v1_schema.js`) declares the Appendix A schema as data. For each collection, in dependency order, it creates the collection when it is missing; otherwise it looks fields up by name and only adds a missing field (inserted after its Appendix A predecessor), appends missing select values, and adds indexes missing by name. Access rules, the `users` rules and `rateLimits.enabled` are compared first, and a collection or the settings are saved only when something differs, so a re-run leaves even the `updated` timestamps alone. The down migration does nothing. Tests parse Appendix A from SPEC.md itself rather than keep a second copy of the schema.

## Consequences

Existing field ids, options and select values survive the upgrade; nothing is renamed or dropped. A future additive change is a new migration in the same style. The migration never tightens or rewrites an option that differs on the live instance; such drift would have to be fixed by a deliberate later migration.
