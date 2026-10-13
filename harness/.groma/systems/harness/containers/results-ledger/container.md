---
type: C4 Container
title: Ledger (results.jsonl)
description: Append-only results.jsonl, one row per trial
status: stable
groma:
  id: results-ledger
  parent: harness
  technology: JSONL file
---

The ledger at `--results` (default `<pkg>/results.jsonl`, shipped empty and tracked in git). One JSON object per trial with exactly 29 fields, serialized as Python `json.dumps(row, sort_keys=True)` writes them, appended as a single write right after its trial and never rewritten. The resume key `<campaign>|<harness>|<model>|<candidate>|<case>|<config>|<trial>` is read back from it, and the report aggregates it.
