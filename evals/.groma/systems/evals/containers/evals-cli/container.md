---
type: C4 Container
title: evals CLI
status: stable
groma:
  id: evals-cli
  parent: evals
  technology: TypeScript on Bun
description: The owner's command-line tool that projects extenders and evidence into PocketBase
---
The `evals` binary (`bun src/cli.ts`). Its subcommands project a dotfiles-agents checkout into PocketBase (`ingest`), load evaluation provenance, verdicts and curation (`load-eval-run`, `load-verdicts`, `load-curation`), compare verdict files offline (`compare-verdicts`), load harness ledgers and logs (`load-runs`), render two Markdown reports (`report`), build a deploy package (`package`) and run a disposable local instance (`fixture`). Every loader reads and validates all input first, plans against the database, then writes, and a re-run on unchanged input plans no writes. It talks to PocketBase only through the official JS SDK as a superuser.
