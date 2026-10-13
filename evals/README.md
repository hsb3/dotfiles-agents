# evals

The owner's command-line tool for a queryable PocketBase projection of the dotfiles-agents extenders and the evidence gathered about them, plus Toolbox, a read-only browser UI. `SPEC.md` is the statement of requirements.

```sh
bun install
bun src/cli.ts --help                     # every subcommand and its flags
bunx tsc --noEmit && bun run build:ui && bun test   # the gate
bun src/cli.ts fixture                    # a disposable seeded PocketBase serving Toolbox
```

Loaders (`ingest`, `load-eval-run`, `load-verdicts`, `load-curation`, `load-runs`) and `report` connect with `PB_URL` (default `http://127.0.0.1:8090`), `PB_ADMIN_EMAIL` and `PB_ADMIN_PASSWORD`; `--parse-only` needs no credentials. `evals package --source-root <checkout> --out <dir>` builds the deploy directory for Railway; deploying it is the owner's step.

Architecture lives in `.groma/` (groma.md), committed work in `.backlog/` (backlog.md).
