---
type: C4 Component
title: Ledger
description: Writes and reads the append-only results ledger
status: draft
groma:
  id: ledger
  parent: agent-harness-cli
  technology: TypeScript
  draft: v1
---

Serializes a row the way Python's `json.dumps(row, sort_keys=True)` does (sorted keys, `", "` and `": "` separators, `\uXXXX` escapes), appends it with a single write, creating the file and its directory on first use, and reads rows back for resume keys and the report, silently skipping lines that are not valid rows.

## Draft relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [ledger](ledger.md) | [results-ledger](../../results-ledger/container.md) | Appends and reads rows | JSONL |
