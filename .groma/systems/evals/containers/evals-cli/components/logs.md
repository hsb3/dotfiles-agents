---
type: C4 Component
title: Logs
description: Parses claude, opencode and codex trial logs
status: stable
groma:
  id: logs
  parent: evals-cli
  technology: TypeScript
  code:
    - scanner: typescript
      file: src/logs.ts
---

Turns one trial log's bytes (UTF-8 with replacement) into run meta (session id, era, provenance, model usage), run events, tool calls joined to their results, excised artifacts (large write and edit contents, screenshots, content-addressed by sha256 and deduplicated within the log) and, for opencode and codex, a token and cost rollup. Lines split as Python str.splitlines() does and each physical line keeps its seq. Pure: it reads no files and writes nothing; load-runs stores what it returns.
