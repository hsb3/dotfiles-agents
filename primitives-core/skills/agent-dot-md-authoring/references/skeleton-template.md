# CLAUDE.md skeleton template

Copy this scaffold and fill each section from what you learned reading the repo.
Delete any section that genuinely doesn't apply — but don't delete a section just
because gathering its content is work. Empty sections are the tell that the file
was written from vibes, not from the code.

```markdown
# CLAUDE.md

This file provides guidance to agents working in this repository.

## Project Overview

<One paragraph: what the system does, who it serves, the core motion. No history,
no values.>

**Architecture:** <services + ports + entry points. e.g. "nginx :80 -> gateway
(FastAPI) :8000 -> worker pool (Celery). Entry: app/main.py.">

**Runtime:** <how a request actually flows, end to end, in 2-3 sentences.>

**Project Structure:**

```
.
├── app/                  # <purpose>
│   ├── gateway/          # <purpose — annotate nested dirs too>
│   │   └── routers/      # <purpose>
│   ├── agents/           # <purpose>
│   └── config/           # <purpose>
├── packages/             # <purpose>
├── tests/                # <purpose>
└── docs/                 # <purpose>
```
<Every line annotated. If you can't annotate it, find out why it exists or omit it.>

## Important Development Guidelines

### <The ONE critical rule>

<Bold, near the top, the only thing in this section. The rule whose neglect causes
the worst rot. e.g. "Keep README.md and CLAUDE.md in sync with every code change.">

## Commands

<Real targets, read from the Makefile / package.json / justfile. One block per
location if the repo is a monorepo.>

```bash
make check      # <what it does>
make test       # <what it does>
make build      # <what it does>
```

## Architecture

### <Subsystem 1>

<Files / key components / lifecycle / config / where its tests live. Put
topic-specific gotchas inline here.>

### <Subsystem 2>

<...>

## Development Workflow

### <TDD / build / test rule>

<The mandatory workflow rule, if any.>

### Startup modes

| Mode   | Command            | Notes                          |
| ------ | ------------------ | ------------------------------ |
| local  | `make dev`         | hot reload, :8000              |
| daemon | `make daemon`      | background, logs to ./logs     |
| docker | `docker compose up`| full stack                     |
| prod   | <deploy command>   | <notes>                        |

### Configuration

<Env vars + resolution order, listed top-to-bottom, recommended location marked.>

```
1. explicit --config argument
2. APP_CONFIG_PATH env var
3. config.yaml in cwd
4. config.yaml in project root  (** recommended **)
```

## Key Features

<One paragraph each, with a link to the detailed doc.>

- **<Feature>** — <one line>. See `docs/<feature>.md`.

## Code Style

- Linter: <tool + config>
- Line length: <n>
- Language version: <e.g. Python 3.13, Node 20>
- Quirks: <e.g. single quotes, no semicolons, intentional long lines in X>

## Documentation

<Index of the detailed docs in /docs/, one line each.>

- `docs/architecture.md` — <what>
- `docs/api-contract.md` — <what>
```
