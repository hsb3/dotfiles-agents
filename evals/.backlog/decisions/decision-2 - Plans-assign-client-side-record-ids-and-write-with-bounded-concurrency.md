---
id: decision-2
title: Plans assign client-side record ids and write with bounded concurrency
date: '2026-10-13 03:20'
status: accepted
---
## Context

Every loader computes its complete plan before writing (phase 2), and a dry run must count children of parents that do not exist yet (files of a new extender, events of a new run). Relations in PocketBase hold record ids, which a parent only has once it is created. A full ingest (about 83 extenders and 500 files) and a 216-run load with logs must finish within a minute against a local server, and PocketBase's batch API is off by default (the migrations only turn rate limiting on).

## Decision

`diff` in `src/store.ts` gives every planned create a fresh 15-character `[a-z0-9]` id, which PocketBase accepts from a superuser, and exposes the natural-key → id map of existing and planned records; children are planned against those ids, so the whole plan is known before any write. Comparison uses one field-kind table for all collections (text-like, number, bool, json, multi, file) implementing the idempotence rules. `applyPlans` writes collection by collection in plan order, creates then updates and retires then deletes, with at most 8 requests in flight per step; the first failure stops further requests and is reported with the collection, natural key and PocketBase's message. The SDK's auto-cancellation is turned off so concurrent requests are not cancelled.

## Consequences

Dry runs and real runs share the same plan. A re-run after a partial failure converges because created records are found again by natural key. The field-kind table must grow with any additive schema change, beside the migration.
