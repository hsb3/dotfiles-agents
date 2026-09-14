# Rig cookbook — one gate command per stack

Every rig collapses to one command. The layers below it are always the same four, in
this order, because each one's failures are cheapest to read when the earlier ones have
already passed:

**types → lint → format → tests**

Structure and portability checks join the front of that list when the artifact needs
them. Put the cheapest, most-specific check first: a contract violation should be
reported as a contract violation, not as a downstream test failure.

Wrap it in a Makefile with a `help` target so the repo's structure is discoverable by
typing `make`.

```makefile
.DEFAULT_GOAL := help
.PHONY: help check fmt

help: ## List targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
	  | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-8s\033[0m %s\n", $$1, $$2}'

check: types lint format test ## The gate — CI, pre-commit hook, and definition of done

fmt: ## Apply formatting and safe fixes. Run freely.
```

---

## Python

Installed on this machine: uv 0.11.17, ruff 0.16.0, ty 0.0.35, pytest 9.1.1.

| Layer | Command |
|---|---|
| Types | `uv run ty check` — or mypy `--strict` if the project needs its maturity |
| Lint | `uv run ruff check .` |
| Format | `uv run ruff format --check .` |
| Tests | `uv run pytest --cov=<pkg> --cov-fail-under=85` |

Start ruff's `select` wide (`E W F I N UP B C4 SIM RET PTH S RUF`) and remove only what
a spec clause forces. Each removal gets a one-line comment naming that clause.

Two traps worth pinning in the contract. Coverage counts **in-process** execution only,
so a suite that drives the CLI by spawning subprocesses will never clear the bar —
the entry point has to be callable in-process. And `uv run` prepends its venv to `PATH`,
so a bare `python3` inside a test resolves to the venv's interpreter, not the system one.

## TypeScript

Installed: bun 1.3.14, node 26.5.0. `tsc`, `eslint` and `prettier` come from the
project's own `package.json`, not the machine.

| Layer | Command |
|---|---|
| Types | `tsc --noEmit` |
| Lint | `eslint .` |
| Format | `prettier --check .` |
| Tests | `bun test --coverage` |

The strict flags that actually catch things, beyond `strict` itself:
`noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`,
`noPropertyAccessFromIndexSignature`, `noImplicitOverride`,
`noFallthroughCasesInSwitch`, `verbatimModuleSyntax`. For lint, typescript-eslint's
`strict-type-checked` + `stylistic-type-checked` presets — the type-aware ones. Untyped
lint misses most of what you wanted a linter for.

Pin the TypeScript version explicitly; typescript-eslint trails new majors, and
discovering that mid-build costs an afternoon.

## Go

`go` is installed; `golangci-lint` and `gofumpt` are not — declare them as `go.mod` tool
directives so the version travels with the repo.

| Layer | Command |
|---|---|
| Types | the compiler, always on |
| Lint | `go tool golangci-lint run ./...` |
| Format | `gofumpt -l` (stricter gofmt) |
| Tests | `go test -coverprofile=...` then a threshold check on `go tool cover -func` |

Beyond the standard set, the extras that earn their place: `bodyclose`, `contextcheck`,
`errorlint`, `gocritic`, `gosec`, `nilerr`, `perfsprint`, `prealloc`, `revive`,
`unconvert`, `unparam`. Relax `gosec`/`errcheck`/`prealloc`/`unparam` for test files
only. Go has no coverage-threshold flag, so the threshold is a few lines of shell — write
them, don't skip the bar.

## Rust

Installed: cargo 1.96.0, rustc 1.96.0.

| Layer | Command |
|---|---|
| Types | `cargo check --all-targets` |
| Lint | `cargo clippy --all-targets -- -D warnings` |
| Format | `cargo fmt --check` |
| Tests | `cargo test` |

`-D warnings` is the whole point; clippy without it is a suggestion box. Add
`unsafe_code = "forbid"` in `[lints.rust]` unless the crate genuinely needs it.

---

## When the artifact has no compiler

Prose, documentation, agent skills, config, data files, schemas. The answer to
"what can a machine check here" is never "nothing" — it is that **you have to write the
checker**, because the guarantees a compiler would have given you are exactly the ones
nobody is giving you.

Write one stdlib-only script, deterministic, exit 0 clean and exit 1 with *every*
violation printed (not the first — a checker that stops at the first finding turns
remediation into N round trips).

What to check, roughly in order of how often it catches something real:

| Check | Why it earns its place |
|---|---|
| **Portability** | absolute paths, personal names, credentials, machine-local tool references — the class that blocks publication and is invisible on the author's own machine |
| **Structural contract** | frontmatter parses and carries the required keys; required files exist |
| **Link and pointer resolution** | every relative path mentioned resolves; nothing orphaned (on disk, unreachable) and nothing dangling (named, absent) |
| **Budgets** | line ceilings per file class; the ceiling is what stops an entry point from becoming a manual |
| **Embedded-language structure** | fenced code blocks parse; diagram blocks declare a known type; examples byte-compile |
| **Clean tree** | no `__pycache__`, `.DS_Store`, cache dirs inside the shipped artifact |

Two things that make such a checker trustworthy rather than decorative:

- **Vendor the downstream rules verbatim.** If the artifact is destined for a repo that
  has its own gate, copy that gate's rules in rather than inventing parallel ones, and
  say in a comment where they came from. Then passing locally means passing there, and
  the two cannot drift.
- **Lint the checker with the same gate it enforces.** A checker exempt from its own
  standard is advice.

---

## Proving the gate

Before anyone builds against it:

1. **Green** on the tree as it stands, or with a known baseline of failures you have
   recorded.
2. **Red** on purpose. Break one rule per gate step — insert a type error, an unformatted
   line, an absolute path, a dangling link — and confirm each is caught *by the step you
   expected*, with a message that names the file and line. A step that catches nothing is
   either misconfigured or checking something you already get for free.
3. Delete the sabotage.

Record in the contract that this was done. "The gate works" is a claim, and an unproven
gate is the most expensive kind of decoration, because it buys confidence without
providing any.

## Wiring it up

`lefthook` (2.1.10, installed) runs the gate on staged paths; `just` (1.57.0) is an
alternative runner if the repo already uses it. Keep the hook calling `make check` rather
than re-listing the steps — one definition, one place to change it.
