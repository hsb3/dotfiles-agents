---
type: C4 Component
title: Ledger
description: Writes and reads the append-only results ledger
status: stable
groma:
  id: ledger
  parent: agent-harness-cli
  technology: TypeScript
  code:
    - scanner: typescript
      file: src/ledger.ts
---

Serializes a row the way Python's `json.dumps(row, sort_keys=True)` does (keys sorted by code point at every depth, `", "` and `": "` separators, DEL and every non-ASCII UTF-16 unit escaped as lowercase `\uXXXX`, numbers as JavaScript prints them), appends it with a single write, creating the file and its directory on first use, and reads rows back for the resume keys and the report, silently skipping lines that are not JSON objects with the key fields. A row missing `campaign` reads as the empty campaign.

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [ledger](ledger.md) | [results-ledger](../../results-ledger/container.md) | Appends and reads rows | JSONL |
