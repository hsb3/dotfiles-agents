# evals — product spec (v1)

`evals` is the owner's command-line tool for a queryable PocketBase projection of the agent extenders (skills, agents, hooks, commands, MCP servers, plugins) that the dotfiles-agents repository ships or curates, and of the evidence gathered about them. It reads a dotfiles-agents checkout and the agent harness's output files, never changes them, and writes one PocketBase database: the extender inventory (frontmatter, files, packaging, provenance); the "doctrine" (named frameworks, rubrics and a jobs-to-be-done taxonomy) seeded from data files in this repository; verdicts joining the two, each linked to the evaluation run that produced it; and normalized harness telemetry (runs, events, tool calls, artifacts). It renders two markdown reports, packages the PocketBase service for deployment (schema and access rules as migrations, a catalog route, the UI), and ships **Toolbox**, a read-only browser UI for authenticated users to browse the catalog, documentation, evaluations and recorded runs. The database is a projection, never a source of truth: nothing flows back to the repository. The deployed instance (PocketBase 0.40.3 on Railway) holds verdicts and provenance that cannot be regenerated, so the schema stays wire-compatible with it and changes only additively.

## Stack

TypeScript on Bun 1.4. Package `evals`, binary `evals` (`package.json` `"bin": {"evals": "src/cli.ts"}`), run as `bun src/cli.ts`. Dependencies, pinned exactly (each published more than 3 days ago, as Bun's `minimumReleaseAge` requires); no others:

| Package | Version | Use |
|---|---|---|
| `pocketbase` | 0.28.1 | the official JS SDK, the only PocketBase client of the CLI and the UI |
| `react`, `react-dom` | 19.1.1 | UI |
| `@carbon/react` | 1.116.0 | UI components and styles |
| `@carbon/charts`, `@carbon/charts-react` | 1.27.19 | UI comparison charts |
| dev: `typescript` | 5.9.2 | |
| dev: `@types/bun` | 1.4.2 | |
| dev: `vite` | 7.1.5 | UI build |
| dev: `sass` | 1.92.1 | Carbon styles |
| dev: `@types/react`, `@types/react-dom` | 19.1.12, 19.1.9 | |

YAML is parsed with `Bun.YAML.parse`. The PocketBase schema, access rules and settings are PocketBase JavaScript migrations in `pb_migrations/`, the catalog route a PocketBase JS hook in `pb_hooks/`; nothing is applied by hand. The UI lives in `ui/` (Vite root, `index.html` titled "Toolbox", output `ui/dist`); Carbon's Sass references fonts as `~@ibm/plex/...`, which needs a Vite `resolve.alias` to the installed `@ibm/plex` package. Seed data lives in `data/*.json` (Appendix B).

Gate (Definition of Done item 1): `bunx tsc --noEmit && bun run build:ui && bun test`, where `build:ui` is `vite build ui` and `tsc` covers `src/`, the tests and `ui/src/`. Tests needing PocketBase start a disposable server from `$PB_BINARY`, else `pocketbase` on `PATH` (0.40.5 locally; the deployed pin is 0.40.3), on a free loopback port with a temporary data directory and this repository's migrations and hooks; they report as skipped when no binary exists. No test reaches the network or a real dotfiles-agents checkout: tests use a synthetic source tree (at least one roster entry of each type, a skill with `references/` and `scripts/`, an agent whose `tools` is a YAML block sequence, a skill whose `description` is a folded block scalar, a hook with `hook.py`, `config.json` and a `.sh` file, an id present in both roster and externals, a standalone and a bundle plugin whose assemblies include `hooks/_lib`, `commands/` and `.mcp.json` links, and a workflows table with non-ASCII guidance), synthetic ledgers and logs, and the exact vectors of Appendix C.

## Behaviour

| Command | Does | Output | Exit |
|---|---|---|---|
| `evals ingest --source-root <dir>` | Projects the checkout (see "The projection"): seeded frameworks, elements and sources; extenders and files from the roster and externals; distributions; frontmatter dimensions; `mechanical-v1` assessments; then retires vanished extenders. | plan block, one line per retired extender, warnings | 0; 1 on failure |
| `evals load-eval-run <manifest>...` | Loads evaluation provenance into eval_runs and eval_responses; optionally stamps `eval_run` on one assessor's assessments. | plan block | 0; 1 |
| `evals load-verdicts <file>... [--extenders a,b] [--complete]` | Loads verdict files into assessments for any assessor but `mechanical-v1`. | plan block | 0; 1 |
| `evals compare-verdicts --left <file>... --right <file>...` | Offline agreement between two sets of verdict files. | disagreement lines, agreement line | 0; 1 when nothing overlaps or on bad input |
| `evals load-curation <file>` | Loads job_coverage and relationships rows. | plan block | 0; 1 |
| `evals load-runs --ledger <path> [--runs-dir <dir>] [--campaign <label>] [--candidate <id>]` | Loads harness ledger rows and their logs into runs → artifacts → run_events → tool_calls. | linkage warnings, plan block | 0; 1 |
| `evals report --out <dir> [--fixtures <dir>]` | Renders `coverage-matrix.md` and `analysis.md` into `<dir>` (created if missing) from the database, or from JSON dumps. | one `wrote` line per file | 0; 1 |
| `evals package --source-root <dir> --out <dir> [--ui-build <dir>]` | Builds a new deploy directory. Never deploys. | `packaged <out>` | 0; 1, also when `--out` exists |
| `evals fixture [--pocketbase <bin>] [--source-root <dir>]` | Runs a disposable loopback PocketBase, built from a fresh package and seeded with synthetic data, until interrupted. | `URL=`, `EMAIL=`, `PASSWORD=` lines | 0 on Ctrl-C; 1 if it cannot start |

Every loader (`ingest`, `load-*`) also takes `--parse-only` or `--dry-run` (not both). `--help` on any command prints its usage and exits 0.

### Rules every command follows

- **Phases.** A writing command (1) reads and validates all of its input without the database, (2) reads the database state inside its scope and computes the complete plan, (3) writes. `--parse-only` stops after (1), never connects, and prints `[parse-only] planned records (no DB connection):` followed by `  <collection>: <n>` count lines and the warnings. `--dry-run` stops after (2) and writes nothing. All validation problems are collected and printed before exiting 1, and then nothing is written. A write failing in (3) stops the command with exit 1, naming the collection, the record's natural key and PocketBase's message; a re-run converges.
- **Idempotence.** A re-run on unchanged input plans `0 create / 0 update` in every collection. A record is unchanged when every field the loader sends equals the stored value: text, select and relation values treat missing, null and `""` as equal; numbers compare numerically, booleans strictly; multi-value selects and relations as ordered lists; json values canonically (sorted keys, after the json coercion rule). A field a loader does not send is never compared or written.
- **Scope.** A scoped run reads, diffs and writes only records inside its scope; records outside it keep every field, `updated` included.
- **Retire, never delete.** No command deletes an extender, assessment, eval run, eval response, job_coverage row, relationship, run, run event, tool call or artifact (assessments and files cascade from extenders, so a delete would lose judged verdicts). The one delete is `ingest` removing `files` rows of a live roster extender whose file has left the tree.
- **Plan block.** `[dry-run] plan (create / update / unchanged):` (after writing: `applied (create / update / unchanged):`), then one line per collection in write order, `  <collection> <c> create / <u> update / <n> unchanged`, extended with ` / <d> delete` for `files` and ` / <r> retire` for `extenders`, then `  no writes made` after a dry run.
- **Connection.** `PB_URL` (default `http://127.0.0.1:8090`), superuser credentials `PB_ADMIN_EMAIL` and `PB_ADMIN_PASSWORD` (missing → exit 1 naming the variables; the password is never printed or written anywhere). One authentication per invocation. With rate limiting on, PocketBase allows 2 authentication requests per 3 s per client and answers `429` beyond that, so a `429` on authentication is retried after 1.5 s, up to 3 times; superuser requests are otherwise not rate limited.
- **Json coercion.** PocketBase stores a *string* sent to a `json` field as the parsed value when its untrimmed first character is one of `{ [ " - 0-9 t f n` and the whole string is valid JSON: `"7853\n"` → `7853`, `"[1, 2]"` → `[1,2]`, `"\"x\""` → `"x"`, `"{\"a\":1} "` → `{"a":1}`; otherwise it stores the string: `"     266"`, `"abc"`, `" {\"a\":1}"`, `""` (verified on 0.40.5). Every command applies the same rule to every json value before sending and comparing; without it re-runs never converge.
- **Read-only inputs.** Nothing is written under `--source-root` or `--runs-dir`, beside `--ledger`, or beside any input file.
- **Errors and usage.** Errors go to stderr as `evals <command>: <what>` with exit 1. No subcommand, an unknown subcommand, an unknown flag or a missing required flag prints usage to stderr and exits 1: an unrecognised flag never falls through to a run.
- Lengths, limits and truncation count Unicode code points.

## Inputs from a dotfiles-agents checkout (`--source-root`)

Paths are relative to `--source-root`. `ingest` requires `primitives-core.yaml`, `externals.yaml` and `.claude-plugin/marketplace.json` (missing → exit 1).

**`primitives-core.yaml`**, the roster: YAML whose `primitives:` list holds flat entries: `id`, `type` (skill, agent, hook, command, mcp), `source`, `origin` (authored, sourced, vendored), `disposition` (qualified, grandfathered-pending-use, demoted, untriaged, orphaned), `targets`, and optionally `requires`, `assumes`, `upstream`, `ref`, `shelf`, `summary`. Comments and other top-level keys occur. A list key given as a scalar is a one-item list; `null` and absent mean none. `assumes` (decision-022) is a token list like `requires`, e.g. `assumes: [path:_meta/plans, port:8737]`; no real entry carries it yet. Excerpt:

```yaml
version: 1

primitives:
  - id: prepare-compact
    type: command
    source: primitives-core/commands/prepare-compact.md
    origin: authored
    disposition: qualified
    targets: [claude-code]
  - id: carbon-design-server
    type: mcp
    source: primitives-core/mcp/carbon-design.json
    origin: authored
    disposition: qualified
    requires: [hosted-mcp]
    targets: [claude-code, codex]
  - id: pocketbase-best-practices
    type: skill
    source: primitives-core/skills/pocketbase-best-practices
    origin: vendored
    upstream: https://github.com/greendesertsnow/pocketbase-skills
    ref: c573263e84a2066d0564f428dd8160e74fc54226
    disposition: qualified
    targets: [claude-code]
  - id: context-watermark
    type: hook
    source: primitives-core/hooks/context-watermark
    origin: authored
    disposition: qualified
    targets: [claude-code, codex]
```

**`externals.yaml`**: `externals:` list of third-party extenders recorded by reference (`id`, `kind`, `upstream`, `ref`, optional `path`, `provides`, `targets`). An id in both files (today `pocketbase-best-practices` and `carbon-builder`) is projected from the roster; the external is skipped with the warning `external <id> skipped: also a roster entry`.

```yaml
externals:
  - id: kata
    kind: plugin
    upstream: https://github.com/hsb3/kata-oversight
    path: plugins/kata
    ref: fced756974bed7c7288276568d43e83759218e6b
    provides: "Archived reference only (kata's MCP shim was merged upstream). …"
    targets: [claude-code, codex]
  - id: carbon-builder
    kind: skill
    upstream: https://github.com/carbon-design-system/carbon-mcp
    path: public/skills/carbon-builder
    ref: 3cbe743d8bc36d6dd3bcfea98ac3ac09bca71f9c
    provides: "IBM's own Carbon Design System skill (v1.2.0), vendored verbatim …"
    targets: [claude-code]
```

**Unit sources** (a roster entry's `source`):

| type | source | entry file | frontmatter, body |
|---|---|---|---|
| skill | directory | `SKILL.md` | YAML frontmatter, markdown body |
| agent | one `.md` file | that file | YAML frontmatter, markdown body |
| command | one `.md` file | that file | YAML frontmatter, markdown body |
| hook | directory with `hook.py`, optional `config.json`/`hook.json`, README, helpers | `hook.py` | none: `{}` and `""` |
| mcp | one `.json` file | that file | none: `{}` and `""` |

Frontmatter is the YAML mapping between a first line `---` and the next line `---`; the body is everything after the closing line. Values keep their YAML types: a folded scalar (`description: >-`) is its folded text, a block sequence (`tools:` then `  - Read` lines) a list. A file without the block has `{}` and its whole text as body; unparseable YAML gives `{}` and a warning. A command and an MCP source:

```markdown
---
description: Update the handoff and prepare a compaction prompt that preserves live work.
---

Invoke the `atelier:compact-handoff` skill and follow it.
```

```json
{"mcpServers": {"carbon-design": {"type": "http", "url": "https://mcp.carbondesignsystem.com/mcp"}}}
```

**`.claude-plugin/marketplace.json`** (trimmed):

```json
{"name": "dotfiles-agents", "metadata": {"version": "0.13.1", "description": "Plugins for coding sessions: …"},
 "plugins": [
  {"name": "atelier", "source": "./plugins/atelier", "version": "0.39.0", "description": "Delegate work to model-tiered agents …", "author": {"name": "Henry S. Burden III"}},
  {"name": "bun", "source": "./plugins/bun", "version": "0.1.1", "description": "Bun as the default JS/TS runtime …"}]}
```

**`plugins/<id>/`**, a plugin's assembly of symlinks into `primitives-core/` (other files are ignored; a missing directory means no members):

```
plugins/carbon/.mcp.json                ->  ../../primitives-core/mcp/carbon-design.json
plugins/carbon/skills/carbon-builder    ->  ../../../primitives-core/skills/carbon-builder
plugins/atelier/agents/builder.md       ->  ../../../primitives-core/agents/builder.md
plugins/atelier/commands/activate.md    ->  ../../../primitives-core/commands/activate.md
plugins/code-desk/hooks/worker-context  ->  ../../../primitives-core/hooks/worker-context
plugins/code-desk/hooks/_lib            ->  ../../../primitives-core/hooks/_lib
plugins/code-desk/hooks/codex-hooks.json    (regular file)
```

**`docs/workflows.md`**, the "Choose a workflow" table, read by `package` only:

```markdown
## Choose a workflow

| Stage | Current marketplace plugin(s) | Choose them when |
| --- | --- | --- |
| Start a project | [code-desk](../plugins/code-desk/README.md), [mise-en-place](../plugins/mise-en-place/README.md), [solo-skills](../plugins/solo-skills/README.md) | Use code-desk to establish a quality contract and gate; … |
| Release | [code-desk](../plugins/code-desk/README.md) | Use its contract and pull-request-finding workflow before release. … |

## Practical starts
```

## The projection (`evals ingest`)

Write order and natural keys: frameworks (slug), framework_elements (framework, slug), sources (slug), extenders (slug), files (extender, relpath), distributions (slug), frontmatter_dimensions (key, applies_to), assessments (extender, framework, element, `mechanical-v1`). After the plan block, each extender retired is listed as `  retired <kind>/<slug>` (`  to retire <kind>/<slug>` on a dry run). Ingest is always the whole tree; it has no scope flag.

- **Seed data** (`data/frameworks.json`, `data/sources.json`, `data/frontmatter-spec.json`, Appendix B). A framework is written with slug, name, source_org, source_url, kind, applies_to, status, summary; an element with framework, slug, name, element_kind, description, criteria, category, and `sort_order` = its index in the file; a source with every field it lists. A seeded row is never deleted, and rows not in the files are left alone.
- **Extenders from the roster** (every type): slug = id; name = frontmatter `name` as text, else id; kind = type; description = frontmatter `description` as text, else roster `summary`, else `""`; origin; upstream and upstream_ref = roster `upstream` and `ref`, else `""`; repo_path = source; shelf = roster `shelf`, else `""`; disposition; requires and assumes = the roster lists (`[]` when none); frontmatter; body; entry_file; file_count; total_bytes = sum of size_bytes; word_count = whitespace-separated words of the body; `retired = false`. `source` and `notes` are not sent. A source path that does not exist gives a warning and no files.
- **Extenders from externals**: slug = name = id; kind = `kind`; description = `provides`; origin `external`; source = the source whose prefix in `upstream_prefixes` (`data/sources.json`) begins the upstream URL, else `""`; upstream; upstream_ref = `ref`; repo_path, shelf, disposition, body, entry_file `""`; requires and assumes `[]`; frontmatter `{}`; file_count, total_bytes, word_count 0; `retired = false`. No files.
- **Files** of a roster extender: every file under a directory source, or the single file, skipping names starting with `.` and directories named `.*` or `__pycache__`; symlinked directories are not descended, symlinked files are read through. relpath = path relative to the source (the file name for a single-file unit), in sorted order. content = the text when the bytes are valid UTF-8, else `""` with is_binary true; size_bytes; sha256 = hex digest of the bytes; language by extension, case-insensitive: `.py` python, `.sh` shell, `.js` javascript, `.ts` typescript, `.md` markdown, `.json` json, `.yaml`/`.yml` yaml, `.toml` toml, `.txt` text, `.css` css, `.html` html, else `""`. role, first match: the entry file → `entrypoint`; first path segment `references` → `reference`, `scripts` → `script`, `assets` → `asset`, `templates` → `template`, `evals` or `eval` → `eval`; base name starting `LICENSE` (any case) → `license`; ending `.md` or `.txt` → `doc`; `.json`, `.yaml`, `.yml`, `.toml` → `config`; else `other`. Stored files of that extender missing from the scan are deleted.
- **Distributions**, one per marketplace plugin: slug = name; version and description from the manifest (`""` when absent); members = the roster extenders the assembly links, in this order: `skills/*`, `agents/*.md` (`.md` stripped), `hooks/*`, `commands/*.md` (`.md` stripped), each sorted by symlink name within its folder and kept only when the name is a roster id (so `_lib` drops out), then `.mcp.json`, resolved to the roster entry whose `source` equals the link's target path. kind = `standalone` when the symlink names under `skills/`, `agents/` (stripped) and `hooks/` are together exactly `[<plugin id>]`, else `bundle` (a plugin carrying `hooks/_lib` is a bundle).
- **Frontmatter dimensions**: one per (kind, key) over the keys observed in roster extenders' frontmatter plus those of `data/frontmatter-spec.json`. requirement, description and spec_framework (that framework's record id) come from the spec file, else `custom`, `""` and `""`; observed_count = number of roster extenders of that kind carrying the key.
- **Mechanical assessments**, assessor `mechanical-v1`, verdict and evidence exactly as below. A value is *set* unless missing, null, false, 0, `""`, `[]` or `{}`; `<json>` is `JSON.stringify` of the value (`null` when missing).
  - skill, framework `anthropic-agent-skills`: `skill-md-entrypoint`: present `SKILL.md at folder root`, or absent `no SKILL.md found`. `frontmatter-name` with name = frontmatter `name` as text (`""` when missing): present if 1–64 characters, partial if longer, absent if empty; evidence `name=<json of name> (<n> chars)`. `frontmatter-description` the same with limit 1024; evidence `<n> chars`. `concise-body`: n = number of `\n` in SKILL.md plus 1 (0 without SKILL.md); present if n ≤ 500, else partial; evidence `<n> lines`. `references-dir`, `scripts-dir`, `assets-dir`: present `<n> file(s)` when files exist under `references/`, `scripts/`, `assets/`, else absent `not bundled (optional)`.
  - agent, framework `claude-code-subagents`: `frontmatter-name` (key `name`), `frontmatter-description` (`description`), `tools-allowlist` (`tools`), `model-tier` (`model`): present if set, else absent; evidence `<key>=<json>`. `system-prompt-body`: present if the body has non-whitespace, else absent; evidence `<n> words`.
  - hook, framework `hook-dir-layout`: `hook-py-entrypoint`: present `hook.py in the hook's directory`, or absent `no hook.py found`. `python-only-handler`: absent `legacy .sh handler(s): <json list of the .sh relpaths>` when any file ends `.sh`, else present `no .sh handler`. `stdlib-only-imports`: absent `no hook.py to scan` without hook.py; partial `non-stdlib imports: <json sorted list>` when a top-level import of hook.py is not stdlib; else present `all top-level imports are stdlib`. A top-level import is a line beginning in column 0 with `import a, b.c as d` (modules `a`, `b.c`) or `from a.b import …` (module `a.b`; `from .` relative imports are skipped); it is stdlib when its part before the first `.` is in `data/python-stdlib.json`. `config-present`: present `<n> file(s)` when `config.json` or `hook.json` is at the hook root, else absent `not bundled (optional)`.
  - command, mcp: none.
- **Retire.** After all other writes, every extender whose slug is neither a roster id nor an external id, and is not already retired, gets `retired = true`; nothing else about it, or anything else, changes. A returning slug is un-retired by its next upsert.
- `ingest` never writes assessments of another assessor, job_coverage, relationships, eval_runs or eval_responses.

## Evaluation inputs

Every verdict links back to the run, prompt and response that produced it, so an eval run is loaded first and verdict and curation files name an existing one; a missing eval run is a validation error.

**Eval-run manifest** (`evals load-eval-run`). Paths are relative to the manifest's directory; files are read as UTF-8.

```json
{
  "run": {"slug": "m1-coverage-judged-2026-07-20", "kind": "judged",
          "method": "how the run was designed and executed", "criteria_file": "JUDGING-CRITERIA.md",
          "frameworks": ["hsb3-jobs-to-be-done"], "status": "complete", "notes": ""},
  "responses": [
    {"role": "judge-1", "agent_type": "foreman-kit:scout", "model": "sonnet",
     "prompt_file": "prompts/judge-1.md", "response_text_file": "responses/judge-1.txt",
     "response_json_file": "responses/judge-1.json",
     "extenders": ["handoff", "compact-handoff"], "tokens": 65840, "duration_ms": 174422}
  ],
  "link_assessor": "coverage-v1"
}
```

`run.slug` and `run.kind` (an eval_runs kind) are required; `criteria_text` is inline or read from `criteria_file`; `frameworks` are existing framework slugs; status defaults to `complete`, method and notes to `""`. Each response: `role` required and unique in the run; `prompt` or `prompt_file`, `response_text` or `response_text_file` (default `""`); `response_json` or `response_json_file` (default `{}`); `extenders` (at most 100 slugs, each a non-retired extender, refused as `<slug> (retired)` or `<slug> (no such extender)`); `tokens` and `duration_ms` finite non-negative numbers when present. Writes eval_runs (key slug: slug, kind, method, criteria_text, frameworks, status, notes), then eval_responses (key run+role: run, role, agent_type, model, prompt, response_text, response_json, extenders, tokens, duration_ms, measurement), then with `link_assessor` sets `eval_run` on every assessment of that assessor whose eval_run differs (plan line `assessments`). A metric absent from the manifest is sent as 0 and marked unavailable. `--parse-only` checks shapes, files and metrics. The response `measurement`:

```json
{"version": 1, "source": "eval-run-manifest",
 "available": {"tokens": true, "duration_ms": true},
 "provenance": {"tokens": "manifest", "duration_ms": "manifest"},
 "execution": {"validity": "unknown", "reason": "manifest does not attest execution validity", "preconditions": null},
 "source_identity": {"manifest_file_sha256": "<sha256 of the manifest file's bytes>",
                     "resolved_response_sha256": "<below>",
                     "resolved_response_canonicalization": "json-sorted-keys-utf8",
                     "revision": {"value": null, "available": false}}}
```

A provenance value is `null` where its availability is false. `resolved_response_sha256` is the canonical hash (as record_sha256 below) of `{"role", "agent_type", "model", "prompt", "response_text", "response_json", "extender_slugs": <the list as given>, "tokens": {"value": <n or null>, "available": <bool>}, "duration_ms": {"value": …, "available": …}}` with the resolved values and the same defaults; a response_json holding NaN or Infinity is a validation error.

**Verdict file** (`evals load-verdicts`, `evals compare-verdicts`):

```json
{
  "assessor": "coverage-v1",
  "framework": "hsb3-jobs-to-be-done",
  "eval_run": "m1-coverage-judged-2026-07-20",
  "fill": "absent",
  "extenders": [
    {"extender": "handoff", "verdicts": [
      {"element": "sustain-continuity", "verdict": "present", "evidence": "keeps the handoff current so a cold session can resume"},
      {"element": "plan-work", "verdict": "partial", "evidence": "…", "score": 0.5}]},
    {"extender": "mermaid", "verdicts": []}
  ]
}
```

Required: `assessor` (non-empty; `mechanical-v1` is refused, ingest owns it), `framework` (slug), `eval_run` (record id or slug of an existing eval run). Optional `fill`. Verdicts are `present`, `partial`, `absent`, `not-applicable`; `evidence` defaults to `""`; `score` is a number. Extenders and elements are named by slug or else by name; an extender must exist and not be retired (`unknown extender <x> (retired)` or `(not in DB)`); an element must belong to the framework. Rows: with `fill`, one per element of the framework for each listed extender (its listed verdict, else `fill` with evidence `""`); without `fill`, one per listed element. Each row sends extender, framework, element, eval_run, verdict, evidence, assessor, and score only when given; natural key (extender, framework, element, assessor). Also refused: a duplicate extender in a file, a duplicate element within an extender, the same natural key from two files. `--extenders a,b`: the files' extender set must equal exactly that set, missing and extra both being errors (the guard for delta passes, so carried extenders are never relinked to a new eval run). `--complete`: every non-retired extender must be listed. Plan line `assessments`.

`compare-verdicts` needs no database. It expands each side to (framework, extender, element) → verdict; for each (framework, extender) present on both sides it compares every element listed on either side, using a side's `fill` where that side does not list the element and skipping the element when that side has no `fill`. Output: each disagreement, sorted, as `<framework> <extender> <element>: left=<v> right=<v>`, then `verdict agreement: <a>/<t> (<p>%)`, p rounded to an integer. No overlap → `no overlapping extenders`, exit 1.

**Curation file** (`evals load-curation`), per-job curation and pairwise extender links:

```json
{
  "eval_run": "m1-coverage-adjudication-2026-07-20",
  "framework": "hsb3-jobs-to-be-done",
  "job_coverage": [
    {"job": "produce-dataviz", "status": "partial", "disposition": "author", "source": "", "rationale": "…"}
  ],
  "relationships": [
    {"extender_a": "compact-handoff", "extender_b": "handoff", "kind": "feeds-into", "job": "sustain-continuity",
     "evidence": "…", "assessor": "adjudication-v1"}
  ]
}
```

`eval_run` required (id or slug); `framework` defaults to `hsb3-jobs-to-be-done` and its element slugs name jobs; `source` is a sources slug or `""`; `job` is optional in a relationship; select values per Appendix A; both endpoints are non-retired extenders. job_coverage: key (job), fields job, status, disposition, source, rationale, eval_run. relationships: key (extender_a, extender_b, kind, job), fields those plus evidence, assessor, eval_run. A duplicate key in the file is refused. The file is the scope: only the rows it lists are read, diffed or written. Plan lines `job_coverage`, `relationships`.

## Harness output (`evals load-runs`)

**Ledger** (`--ledger <path>`): JSON Lines written by the harness, one object per trial, keys sorted. Blank lines are ignored; a line that is not a JSON object is skipped with a warning naming its line number. Row key: `campaign|harness|model|candidate|case|config|trial`, each as text (trial an integer), a missing or null campaign read as `""`; a later line with the same key replaces an earlier one. Three generations coexist: 22 fields (no campaign, log_path or token counts), 28 (adds them), 29 (adds preconditions). A 29-field row (`checks` has 6 items and `grades` 2, first of each shown; three whole rows are in Appendix C):

```json
{"cache_creation_tokens":18170,"cache_read_tokens":9544,"campaign":"weekly-20260817","candidate":"scout","case":"stale-config-trap","checks":[{"evidence":"FINDINGS.md present","id":"findings-exists","passed":true}],"cli_version":"1.18.15","config":"baseline","cost_usd":0.0861297,"duration_ms":1466021,"error":null,"exit_code":0,"grader_model":"claude-haiku-4-5-20251001","grades":[{"evidence":"…","id":"a1-timeout-not-stale","passed":true}],"harness":"opencode","input_tokens":13,"kind":"agent","log_path":"harness/runs/opencode-scout-stale-config-trap-baseline-2-20260817-133552.log","model":"claude-sonnet-4-5","num_turns":3,"output_tokens":1006,"passed":true,"plugin_errors":[],"preconditions":{"auth_env_present":["ANTHROPIC_API_KEY"],"campaign":"weekly-20260817","cli_version":"1.18.15","grader_model":"claude-haiku-4-5-20251001","harness":"opencode","model":"claude-sonnet-4-5","network_assumption":"assumed-available","self_installs":[],"timeout":600},"skill_used":false,"tool_names":["task","write"],"trial":2,"ts":"2026-08-17T13:35:52","workspace":null}
```

harness is claude, opencode or codex; config with or baseline; trial 0-based; model the id as typed or `default`; `ts` naive local ISO time, kept as text; a skip row has `passed: null` and `error: "unsupported: <harness> cannot host kind=<kind>"`.

**Scope.** `--campaign <label>` (exact match; `--campaign ""` selects the empty legacy label) and `--candidate <id>` filter the ledger rows and the existing runs alike; omitted means no filter. Nothing in scope → `no ledger rows in scope; nothing to do`, exit 0. An unreadable ledger → exit 1.

**Logs.** `--runs-dir` defaults to `<ledger dir>/runs`; a missing directory means no logs. A log is one trial's raw CLI output, named `<harness>-<candidate>-<case>-<config>-<trial>-<YYYYmmdd-HHMMSS>[-<32 hex>].log`, its first line `# preconditions: {…}`, then one vendor event per line. Linkage, explicit claims first:
1. A row with `log_path` claims it. New rows hold a path relative to the ledger's directory (`runs/<file>`); legacy rows hold `harness/runs/<file>`, relative to the old repository root. The log is `<ledger dir>/<log_path>` if that file exists, else `<runs-dir>/<basename>` if that exists, else unobserved. Its basename is claimed either way.
2. A row without `log_path` takes the earliest by name of the unclaimed `.log` files in `--runs-dir` named `<harness>-<candidate>-<case>-<config>-<trial>-…`. None → warning `no log matches prefix '<prefix>' (run ingested with empty log fields)`; several → warning `ambiguous link for '<prefix>': <n> candidates, picked earliest '<file>'`.

`runs.log_path` stores the row's `log_path` verbatim; a prefix-matched row stores `harness/runs/<file>`, the form the live rows already carry; with neither, log_path is not sent. Log bytes are decoded as UTF-8 with replacement.

**Validation**, before any write: `passed` and `skill_used` booleans or null; `exit_code` an integer or null; `num_turns`, `cost_usd`, `duration_ms`, `input_tokens`, `output_tokens`, `cache_creation_tokens`, `cache_read_tokens` finite non-negative numbers (not booleans) or null. A violation names the row key and the field.

**Run row.** Sent: campaign (`""` default), harness, model, candidate, case, config, trial, kind, grader_model, passed, skill_used, exit_code, num_turns, cost_usd, duration_ms, input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens, error, workspace, checks, grades, tool_names, ts, cli_version, all verbatim from the ledger; log_path; measurement; and from a parsed log era, session_id (`""` when none), model_usage, provenance. Without a parsed log, era is `na` for opencode and codex and not sent for claude, and session_id is `""`. `preconditions` and `plugin_errors` are not columns; they live in `measurement.execution`. When era is `na` and a log was parsed, a null cost_usd, duration_ms, input_tokens, output_tokens, cache_read_tokens or cache_creation_tokens takes the log's rollup value (the ledger wins). Null values are then dropped from the body, except the ten **measurement fields** (passed, skill_used, exit_code, num_turns, cost_usd, duration_ms, input_tokens, output_tokens, cache_creation_tokens, cache_read_tokens), which are sent as null. When diffing, a measurement field that `measurement.available` marks false is not compared: PocketBase stores 0 or false for null, and that must not read as a change.

**`measurement` v1** of a run (exact vectors in Appendix C.2):

```json
{"version": 1, "source": "harness-ledger",
 "available": {"<measurement field>": "<its body value is not null>"},
 "provenance": {"<measurement field>": "ledger | log-rollup | null"},
 "execution": {"validity": "valid | invalid | skipped | unknown", "reason": "…",
               "preconditions": "<the ledger object, or null>", "plugin_errors": "<the ledger value>"},
 "source_identity": {"record_sha256": "…", "record_canonicalization": "json-sorted-keys-utf8",
                     "log_sha256": "<sha256 of the log file's bytes, or null>", "log_available": "<log_sha256 is not null>",
                     "log_observation": "observed | absent | unobserved-local", "revision": {"value": null, "available": false}}}
```

- provenance: `ledger` when the ledger value is not null; else `log-rollup` when the field is one of the six rollup fields and was filled from the log; else null.
- log_observation: `observed` when log bytes were read; `absent` for a skip row (passed null and error starting `unsupported:`); else `unobserved-local`.
- execution, first matching rule: exit_code not null and ≠ 0 → `invalid`, "producer exit_code was nonzero"; plugin_errors a non-empty list → `invalid`, "producer recorded plugin_errors"; passed null and error starting `unsupported:` → `skipped`, "explicit unsupported producer row"; error a non-empty string → `invalid`, "producer recorded error"; passed not a boolean → `unknown`, "passed was not an explicit boolean"; exit_code not 0 → `unknown`, "exit_code was not explicitly zero"; plugin_errors not a list → `unknown`, "plugin_errors were not recorded"; preconditions not valid → `unknown`, "preconditions were missing or malformed"; else `valid`, "producer recorded completed run evidence". Preconditions are valid when they are a non-empty object whose harness, cli_version, model, campaign and network_assumption are strings, grader_model is present and a string or null, timeout is a finite non-negative number, and auth_env_present and self_installs are lists of strings.
- **record_sha256** = SHA-256 hex of the UTF-8 bytes of the whole ledger row serialised as Python's `json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False)`: keys sorted by code point at every level; no whitespace; strings escaped only for `"`, `\` and control characters (`\b \f \n \r \t`, the rest as lowercase `\u00xx`), all else raw (non-ASCII, `/`, U+2028); `true`, `false`, `null`; a number written in the ledger without fraction or exponent is an integer, written as its exact digits; one with a fraction or exponent is a float, written as Python's `repr`: the shortest round-trip digits, positional when the decimal exponent is in [-4, 16) with at least one fractional digit (`1.0`, `0.0001`, `0.047738249999999996`, `123456789012345.0`), otherwise `d[.ddd]e±XX` with at least two exponent digits (`1e-05`, `2.5e-07`, `1e+16`), and `-0.0` stays `-0.0`. `JSON.parse` loses the integer/float distinction, so the number lexemes must be taken from the line. A mismatch re-stamps every live run once; the Appendix C.1 vectors are mandatory tests.

**A logless re-run never erases evidence.** When an existing run is re-loaded with log_observation `unobserved-local`: its stored non-empty session_id and era are kept; a measurement field unavailable now but stored non-null keeps its stored value, and stays available with provenance `log-rollup` if the stored measurement had it so; and when the stored measurement says `observed` with a log_sha256, the new one keeps that log_sha256 with `log_available: true` and `log_observation: "observed"`. Children are never deleted, so stored events and tool calls survive.

**Claude log** (stream-json). Lines split exactly as Python's `str.splitlines()` does (on `\n`, `\r\n`, `\r`, `\v`, `\f`, U+001C, U+001D, U+001E, U+0085, U+2028, U+2029), each trimmed. `seq` is the 0-based physical line index: a blank line or one that is not a JSON object yields no event but counts, so the `# preconditions` header is seq 0. `system/thinking_tokens` events are dropped.
- Run meta: the `system/init` event gives session_id, era (`legacy` when its `tools` is a list of at most 5, else `post`; `post` when there is no init) and provenance (its keys among tools, plugins, slash_commands, apiKeySource, permissionMode, capabilities, memory_paths); the `result` event gives model_usage (its `modelUsage`) and a fallback session_id.
- Event row: vendor `claude`; event_type `<type>/<subtype>`, or `<type>` without a subtype; role assistant → `assistant`, user → `tool_result`, system → `system`, result → `result`, other → `system`; payload = the event after excision. assistant: input_tokens, output_tokens, cache_read_tokens (`cache_read_input_tokens`), cache_write_tokens (`cache_creation_input_tokens`) from `message.usage`; text = its text blocks concatenated, first 5000 characters; tool_name and tool_call_id when it has exactly one tool_use block. user: ts from `timestamp`; tool_call_id and is_error when it has exactly one tool_result block. result: text = `result`, first 5000 characters.
- ts from an ISO-8601 time with zone = `trunc(((whole seconds since the epoch × 10⁶ + microseconds) / 10⁶) × 1000)` in IEEE doubles, which reproduces the stored values (`Date.parse` alone can differ by 1 ms); unparseable → null.
- Tool calls: one per tool_use block in order (tool_call_id = `id`, tool_name = `name`, input), joined to the tool_result whose `tool_use_id` matches: output = its `content`, is_error, status `error` or `ok`, started_ts = that user event's ts. A call never answered has status `no_result`. wallclock_ms is null.
- Excision: in a tool_use `input`, a `content` (kind `write_content`) or `new_string` (kind `edit_diff`) string longer than 5000 characters becomes a text artifact and is replaced by `{"$artifact": "<sha256>"}`; in a tool_result's content list, an image `{"type": "image", "source": {"data": <base64>, "media_type": …}}` becomes a `screenshot` artifact (decoded bytes; mime = media_type, default `image/png`) and `data` is replaced by the marker; in the user event's `tool_use_result` object, `file.base64` becomes a `screenshot` (`image/png`) the same way, then every string leaf there equal to one of the event's tool_result string contents is replaced by `{"$deduped": "content"}`.

**Opencode log** (JSONL, one fused event per tool call). Same line and seq rules. Vendor `opencode`; event_type = `type`; role tool_use → `tool_call`, text → `assistant`, step_start and step_finish → `system`, other → `system`; ts = `timestamp` when an integer; session_id = the first non-empty `sessionID`; era `na`.
- tool_use, with state = `part.state`: when `state.metadata.filediff.patch` equals `state.metadata.diff` it becomes `{"$deduped": "diff"}`; each `state.attachments[].url` that is a `data:` URI becomes a `screenshot` artifact (mime from the URI, default `image/png`) replaced by the marker; `state.input.content` and `state.input.newString` longer than 5000 characters become `write_content` and `edit_diff` artifacts. The call: tool_call_id = `part.callID`, tool_name = `part.tool`, input = `state.input`, output = `state.output`, status = `state.status`, is_error = (status is `error`), wallclock_ms = `time.end − time.start`, started_ts = `time.start`; the event row repeats tool_name, tool_call_id, status, is_error and wallclock_ms.
- text: text = `part.text`, first 5000 characters. step_finish: cost_usd = `part.cost`; input_tokens, output_tokens, cache_read_tokens, cache_write_tokens = `part.tokens.input`, `.output`, `.cache.read`, `.cache.write`.
- Rollup: cost_usd = sum of the step_finish costs (null when none); input_tokens, output_tokens, cache_read_tokens, cache_creation_tokens = sums of the step_finish token counts (0 when none); duration_ms = max − min of the integer timestamps (null when none).

**Codex log** (`harness: codex`; `codex exec --json`, JSONL). The line, seq, linkage, artifact and measurement rules are the same as for the other logs. Vendor `codex`, era `na` (so the rollup fill applies). session_id is the `thread_id` of the first `thread.started` event. Codex events carry no timestamps, so every ts is null.

A captured log (codex-cli 0.162.1, header line omitted):

```jsonl
{"type":"thread.started","thread_id":"01a132ee-ff13-7c01-8170-7d57383f6262"}
{"type":"item.completed","item":{"id":"item_0","type":"error","message":"`--dangerously-bypass-hook-trust` is enabled. Enabled hooks may run without review for this invocation."}}
{"type":"turn.started"}
{"type":"item.completed","item":{"id":"item_2","type":"agent_message","text":"OK"}}
{"type":"turn.completed","usage":{"input_tokens":12868,"cached_input_tokens":0,"cache_write_input_tokens":12865,"output_tokens":5,"reasoning_output_tokens":0}}
```

The tool-item shapes below come from codex's documented exec schema, not a capture:

```jsonl
{"type":"item.started","item":{"id":"item_0","type":"command_execution","command":"/bin/zsh -lc 'cat SKILL.md'","aggregated_output":"","exit_code":null,"status":"in_progress"}}
{"type":"item.completed","item":{"id":"item_0","type":"command_execution","command":"/bin/zsh -lc 'cat SKILL.md'","aggregated_output":"---\nname: mermaid\n...","exit_code":0,"status":"completed"}}
{"type":"item.completed","item":{"id":"item_2","type":"file_change","changes":[{"path":"/tmp/…/ws/README.md","kind":"update"}],"status":"completed"}}
{"type":"error","message":"Reconnecting... 1/5"}
{"type":"turn.failed","error":{"message":"unexpected status 401 Unauthorized: Incorrect API key provided"}}
```

- **Event row**, one per JSON-object line:
  - event_type: `type`, with `/<item.type>` appended for `item.started`, `item.updated` and `item.completed` (`item.completed/command_execution`).
  - role:
    - an item event whose item.type is `agent_message` or `reasoning` → `assistant`;
    - one whose item.type is `error` or `todo_list` → `system`;
    - any other item event → `tool_call`;
    - `turn.completed` and `turn.failed` → `result`;
    - everything else (`thread.started`, `turn.started`, a top-level `error`) → `system`.
  - payload: the event.
- **Field values on event rows:**
  - `agent_message` and `reasoning`: text is `item.text`, first 5000 characters.
  - `tool_call` events: tool_call_id `item.id`, tool_name `item.type`, status `item.status`. is_error is true when status is `failed`, or when `exit_code` is a non-zero integer.
  - `turn.completed`: input_tokens, output_tokens, cache_read_tokens and cache_write_tokens are `usage.input_tokens`, `usage.output_tokens`, `usage.cached_input_tokens` and `usage.cache_write_input_tokens`.
  - `turn.failed`: text is `error.message` and is_error is true.
  - a top-level `error`: text is `message`.
- **Tool calls:** one per distinct `item.id` among the `tool_call` events, in order of first appearance, each taken from its last event:
  - tool_call_id `item.id`, tool_name `item.type`;
  - input: the item minus `id`, `type`, `status`, `aggregated_output` and `exit_code`;
  - output: `{"aggregated_output": …, "exit_code": …}` for `command_execution`, else null;
  - status: `item.status`, or `no_result` when the item never reached `item.completed`;
  - is_error as above; wallclock_ms and started_ts null.
- **Nothing is excised.** Codex events carry no file contents and no images (`file_change` lists paths only).
- **Rollup:** input_tokens, output_tokens, cache_read_tokens and cache_creation_tokens are the sums over `turn.completed` usage (0 when none). cost_usd and duration_ms are null: codex reports no price, and the ledger's wall-clock duration stands.

Codex rows in the ledger have `cost_usd` and `num_turns` null by design, and a `model` that is never `default`.

**Artifacts** are content-addressed by the sha256 of their bytes and deduplicated across the whole load; the first run in ledger order to produce a sha owns `run`. An existing artifact with that sha is reused and never updated. A new one is created with run, kind, mime, sha256, byte_size, text_ref (non-screenshots: the first 5000 characters of the bytes decoded as UTF-8 with replacement) and the protected file `blob`, named `<first 12 hex of the sha>.png` for a screenshot, else `.txt`. A run event or tool call links `artifact` to the first of its artifacts (the others stay recoverable from the payload markers); events of other runs may link the same artifact.

**Writes.** Order runs → artifacts → run_events (key run+seq) → tool_calls (key run+tool_call_id). Event fields: seq, ts, vendor, role, event_type, tool_name, tool_call_id, status, is_error, input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, cost_usd, wallclock_ms, text, payload, run, artifact. Tool-call fields: tool_call_id, tool_name, input, output, status, is_error, wallclock_ms, started_ts, run, artifact. Nulls are not sent. Existing children are read only for the existing runs in scope; a child of a run still to be created counts as a create on a dry run. Plan lines `runs`, `artifacts`, `run_events`, `tool_calls`; linkage warnings print before the plan as `linkage warnings (<n>):` with `  - <text>` lines.

**`--parse-only`** prints exactly this shape (the numbers are the real ledger's on a checkout without logs):

```
[parse-only] planned records (no DB connection):
  runs:        216
  run_events:  0
  tool_calls:  0
  artifacts:   0 post-dedup (0 screenshot, 0 text)
  runs with log reference: 168/216
  runs with observed log bytes: 0/216
  era split:   legacy=0, post=0, na=0
  warnings (48):
    - no log matches prefix 'claude-mermaid-add-architecture-diagram-with-0-' (run ingested with empty log fields)
```

`warnings:    none` when there are none; "log reference" counts runs whose body has a log_path; the era split counts parsed logs only.

## Reports (`evals report`)

Reads frameworks, framework_elements, extenders, sources, job_coverage, relationships, assessments and eval_runs whole: from the database, or with `--fixtures <dir>` from `<dir>/<collection>.json`, each a JSON array of records as the API returns them (no credentials needed). Deterministic: the same data gives byte-identical files (lines joined with `\n`, one final `\n`). Retired extenders are excluded, and so are assessments whose extender is not a live extender and relationships with an endpoint that is not (each counted once). A table cell writes `|` as `\|` and newlines as spaces. A missing `hsb3-jobs-to-be-done` framework is exit 1. Prints `wrote <path>: <J> jobs (<G> gap, <P> partial), <R> relationships` and `wrote <path>: <E> extenders, <N> eval_runs`. Reports are never tracked in any repository.

The **scope paragraph** in both files: `Retired units excluded: **<r>**. Suppressed rows: **<a> assessments**, **<s> relationships**. Counts cover all fetched rows, before section-specific filtering. Assessments and relationships referencing retired or missing extenders are excluded; each relationship counts once even if both endpoints are excluded. Stored history is retained; eval-run linked-row counts reflect this active projection.`

**`coverage-matrix.md`** (jobs = elements of `hsb3-jobs-to-be-done` in sort_order; *coverage rows* = live `coverage-v1` assessments of that framework; rows shown are illustrative):

```markdown
# Extender coverage matrix — jobs-to-be-done

_Generated by `evals report` — do not hand-edit. Truth lives in the database
(assessor `coverage-v1` assessments + `job_coverage` + `relationships`);
this file is a rendered snapshot for reading and diff review._

Framework: `hsb3-jobs-to-be-done` (24 jobs, 7 families) x 83 extenders.
Provenance: eval_runs `m1-coverage-adjudication-2026-07-20`, `m1-coverage-judged-2026-07-20`.

<scope paragraph>

## Matrix

| Job | Family | Status | Present | Partial | Disposition | Source |
|---|---|---|---|---|---|---|
| `orient-codebase` | understand-research | **covered** | handoff, mermaid | — | author | — |

## Gaps and partial coverage

- **`produce-dataviz`** (partial, disposition author): <rationale>

## Relationships

| Kind | Count |
|---|---|
| complementary | 12 |

### Duplicative pairs (M3 coalesce candidates)

- <a slug> = <b slug>: <evidence>

### Conflicting pairs

- <a slug> x <b slug>: <evidence>

### Directed hand-off links (composition-planner substrate, EDB-22)

- <a slug> -> <b slug> (precedes)
- <a slug> => <b slug> (feeds-into)
```

Families = distinct categories of the jobs; extenders = live extenders. Provenance = the slugs of the eval runs linked from coverage rows, job_coverage rows and live relationships, sorted, in backticks, comma-separated, `none` when empty. Matrix status in bold (`?` without a job_coverage row); Present and Partial = sorted slugs of coverage rows with that verdict (`—` if none); disposition (`?`); source slug (`—`). Gaps: jobs whose status is gap or partial, in job order. Relationships: live relationships counted by kind, kinds sorted; the duplicative and conflicting sections only when they have pairs, sorted by (a slug, b slug); the directed section always, sorted by (a slug, kind, b slug).

**`analysis.md`**:

```markdown
# Extender-DB analysis

_Generated by `evals report` — do not hand-edit. Companion to `coverage-matrix.md`;
covers the DB's other cross-cutting answers: per-extender profiles, duplicative/conflicting/directed relationships, an assessor comparison, and the
eval-runs provenance index._

<scope paragraph>

## Extender profiles

| Extender | Kind | Jobs present | Jobs partial | Relationship degree |
|---|---|---|---|---|
| `handoff` | skill | 2 | 1 | 3 |

## Duplicative, conflicting, and directed relationships

_Pairs that need a resolution (`duplicative`/`conflicting`) or carry an ordering
decision (`precedes`/`feeds-into`, the composition-planner substrate, EDB-22)._
`complementary` pairs are informational and excluded — see the kind-count table
in `coverage-matrix.md`.

| Kind | A | B | Status | Evidence |
|---|---|---|---|---|
| duplicative | `a` | `b` | open | … |

## Assessor comparison

_Present/partial/absent verdict counts per extender, per assessor. `—` = the
assessor never assessed that extender (not the same as an all-absent triple)._

| Extender | Kind | mechanical-v1 (P/Pa/Ab) | judged-v1 (P/Pa/Ab) | coverage-v1 (P/Pa/Ab) |
|---|---|---|---|---|
| `handoff` | skill | 7/0/2 | — | 2/1/21 |

## Eval-run provenance index

| Slug | Kind | Status | assessments | job_coverage | relationships | Total |
|---|---|---|---|---|---|---|
| `m1-coverage-judged-2026-07-20` | judged | complete | 864 | 0 | 0 | 864 |
```

Profiles: live extenders by slug; distinct elements of their coverage rows that are present, and partial; degree = live relationships touching it. Relationship listing: kinds duplicative, conflicting, precedes, feeds-into, sorted by (kind, a slug, b slug); status `resolved` when the evidence contains `RESOLVED`, else `open`. Assessor comparison: per live extender and each of the three assessors, `<present>/<partial>/<absent>` counts, `—` when it has no rows. Index: eval runs by slug with the rows linked from live assessments, all job_coverage and live relationships.

## Package and deploy (`evals package`)

Builds `--out`, which must not exist and must not be inside `--source-root` (parents are created; on failure nothing is left behind). Two runs on the same inputs produce byte-identical trees:

```
<out>/Dockerfile  <out>/start.sh  <out>/railway.toml
<out>/pb_hooks/toolbox_catalog.pb.js    the catalog route
<out>/pb_hooks/toolbox-catalog.json     the catalog; outside pb_public, so never served as a file
<out>/pb_hooks/toolbox-package.json     the receipt
<out>/pb_migrations/…                   every migration of this repository
<out>/pb_public/…                       the UI build: index.html, assets/…
```

- **UI build** (`--ui-build`, default this repository's `ui/dist`): a regular directory without symlinks, holding `index.html` and at least one file under `assets/`; refused if it contains a source map (`*.map`), a `.env*` file, or a path part `node_modules`, `src` or `private*`; each `<script type="module" src>` and `<link rel="stylesheet" href>` of index.html must be a relative or root path (no scheme, no `//`, no `..`) to a file of the build. Missing → `evals package: no UI build at <dir>; run bun run build:ui`.
- **Catalog inputs** `.claude-plugin/marketplace.json` and `docs/workflows.md` must be regular files with no symlink at or above them inside the source root. The workflow table is the first table after a heading `Choose a workflow` of level 2 or deeper, ending at the next heading or non-table line; it has a header row, a separator row and at least one row. Header cells are exactly `Stage`, `Current marketplace plugin(s)`, `Choose them when`; separator cells match `:?-+:?`; each row has exactly 3 non-empty cells; plugin links `[<id>](../plugins/<id>/README.md)` have label = id, at least one per row, each a marketplace plugin. Workflow id = the stage lower-cased, each run of characters outside `a-z0-9` replaced by `-`, leading and trailing `-` removed (empty is an error); rows with the same id must agree. The manifest's `plugins` is a list of objects with unique string `name`s. Every violation is an exit-1 error naming it.
- **`toolbox-catalog.json`** = `JSON.stringify(catalog, null, 2)` with keys sorted at every level, plus `\n`, in UTF-8 (shown compacted):

  ```json
  {"plugins": [{"description": "Bun as the default JS/TS runtime …", "id": "bun", "name": "bun", "version": "0.1.1", "workflows": ["implement"]}],
   "source_snapshot": "<sha256 hex of the marketplace.json bytes, a 0x00 byte, the workflows.md bytes>",
   "workflows": [{"guidance": "Use its contract and pull-request-finding workflow before release. …", "id": "release", "name": "Release", "plugins": ["code-desk"]}]}
  ```

  plugins: every manifest plugin sorted by id, name = id, version and description `""` when absent, workflows = sorted ids of the workflows linking it. workflows: sorted by id, name = the stage, guidance = the third cell, plugins sorted.
- **`toolbox-package.json`**: `{"migrations": [<names>], "migrations_snapshot", "source_snapshot", "ui_files": [<relpaths>], "ui_snapshot"}`, keys sorted, 2-space indent, final `\n`; a snapshot is the sha256 over, for each file in sorted relative-path order, its relpath, a 0x00 byte, its bytes and a 0x00 byte.
- **Catalog route** `GET /api/toolbox/catalog`: 200 with the parsed `toolbox-catalog.json` for any authenticated request (users or superusers), 401 otherwise.
- **`Dockerfile`**, exactly:

  ```dockerfile
  FROM alpine:3.20

  ARG PB_VERSION=0.40.3
  ARG TARGETARCH

  RUN apk add --no-cache ca-certificates curl unzip
  RUN set -e; case "$TARGETARCH" in \
        amd64) PB_SHA256=8d81b6b79add0e219373e922ebe1dddbee7f57fcff602e3585e0d2c654b983ce ;; \
        arm64) PB_SHA256=d5092815259f5bc2dffabf6a71da2168851c8d75c04d6e56f6e7a38c48941c70 ;; \
        *) echo "unsupported PocketBase architecture: $TARGETARCH" >&2; exit 1 ;; \
      esac; \
      curl -fsSL -o /tmp/pb.zip "https://github.com/pocketbase/pocketbase/releases/download/v${PB_VERSION}/pocketbase_${PB_VERSION}_linux_${TARGETARCH}.zip"; \
      echo "$PB_SHA256  /tmp/pb.zip" | sha256sum -c -; \
      unzip /tmp/pb.zip -d /pb; rm /tmp/pb.zip; /pb/pocketbase --version

  WORKDIR /pb
  COPY start.sh ./start.sh
  COPY pb_public ./pb_public
  COPY pb_hooks ./pb_hooks
  COPY pb_migrations ./pb_migrations
  RUN chmod +x /pb/start.sh

  EXPOSE 8090
  HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD wget -q -O- "http://127.0.0.1:${PORT:-8090}/api/health" >/dev/null 2>&1 || exit 1
  CMD ["/pb/start.sh"]
  ```

- **`start.sh`**, exactly (executable):

  ```sh
  #!/bin/sh
  set -eu

  data_dir=${PB_DATA_DIR:-/pb/pb_data}
  pb_bin=${POCKETBASE_BIN:-/pb/pocketbase}
  package_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
  : "${PB_SUPERUSER_EMAIL:?PB_SUPERUSER_EMAIL is required}"
  : "${PB_SUPERUSER_PASSWORD:?PB_SUPERUSER_PASSWORD is required}"
  if output=$("$pb_bin" superuser create "$PB_SUPERUSER_EMAIL" "$PB_SUPERUSER_PASSWORD" --dir "$data_dir" 2>&1); then
    :
  elif printf '%s' "$output" | grep -q 'failed to create new superuser account: email: Value must be unique\.$'; then
    :
  else
    printf '%s\n' "$output" >&2
    exit 1
  fi

  exec "$pb_bin" serve --http="${PB_BIND:-0.0.0.0}:${PORT:-8090}" --dir "$data_dir" \
    --hooksDir="$package_dir/pb_hooks" --publicDir="$package_dir/pb_public" \
    --migrationsDir="$package_dir/pb_migrations" --automigrate=false \
    --origins="${PB_CORS_ORIGINS:-https://invalid.local}"
  ```

  An existing superuser with that email is kept unchanged; any other bootstrap failure stops before serving. The server applies pending migrations at start (automatic generation of new migration files is off). The same script runs a persistent local instance with `PB_DATA_DIR`, `PB_BIND`, `PORT` and `POCKETBASE_BIN` set.
- **`railway.toml`**, exactly:

  ```toml
  [build]
  builder = "DOCKERFILE"
  dockerfilePath = "Dockerfile"

  [deploy]
  healthcheckPath = "/api/health"
  healthcheckTimeout = 100
  ```

Deploying the package (`railway up` with the volume at `/pb/pb_data` and server-only `PB_SUPERUSER_EMAIL`/`PB_SUPERUSER_PASSWORD`) is the owner's step.

## Local fixture (`evals fixture`)

Builds a package in a new temporary directory, from `--source-root` (default: the synthetic source tree the tests use) and this repository's `ui/dist` (missing → the `package` error); starts its `start.sh` with the PocketBase binary (`--pocketbase`, else `$PB_BINARY`, else `pocketbase` on `PATH`) on a free `127.0.0.1` port with an empty data directory, `PB_CORS_ORIGINS` set to its own URL and the superuser `fixture-admin@example.test` / `FixtureAdminPassword123`; waits up to 10 s for `/api/health` (else exit 1); creates the verified user `fixture-user@example.test` / `FixtureUserPassword123`; seeds; then prints

```
URL=http://127.0.0.1:<port>
EMAIL=fixture-user@example.test
PASSWORD=FixtureUserPassword123
Fixture runs until Ctrl-C; all data is deleted on exit.
```

On SIGINT or SIGTERM it stops the server, deletes the temporary directory and exits 0. It reads no credentials from the environment or from files and talks only to its own server.

Seed, all synthetic: source `ui-fixture-source`; framework `ui-fixture-framework` (job-taxonomy) with job element `ui-fixture-job`; extender `ui-fixture-primitive` (skill, source linked, body `# UI fixture primitive\n`, entry_file `SKILL.md`) with files `README.md` (doc), `SKILL.md` (entrypoint), `hooks/check.py` (script); distribution `ui-fixture-distribution` (plugin) with that member; eval run `ui-fixture-evaluation` (judged, running) with one response naming the extender; one assessment (present, score 1) and one job_coverage row (covered) linked to that eval run. 27 runs built by the same run-row builder as `load-runs`, so each carries `measurement` v1: runs 0 and 1 share campaign `ui-fixture-campaign`, harness opencode, model `ui-fixture-model`, candidate `ui-fixture-candidate`, case `ui-fixture-case`, trial 1, and are `baseline` (passed false) and `with` (passed true), with exit_code 0, plugin_errors `[]` and valid preconditions, so they form a valid comparison pair; runs 2–26 have campaign `toolbox-fixture`, mixed harnesses and models, and one has candidate `fixture-<img src=x onerror=alert(1)>`. One protected text artifact (`fixture protected evidence\n`, kind tool_output) is owned by run 0 and referenced by one run event and one tool call in each of runs 0 and 1.

## Toolbox UI

A single-page app served by the PocketBase service from `pb_public`, on the same origin as the API, built with Carbon. It only reads.

- **Sign-in** with email and password against the `users` collection. The token is held in memory only, never in localStorage, sessionStorage or a cookie; the password field is cleared after every attempt. A 400, 401 or 403 answer shows "Sign-in failed" / "Sign-in details were not accepted."; any other failure "Could not sign in. Try again." The session ends (back to sign-in; token, selections and loaded records cleared; requests in flight cancelled) on "Log out", when the token's JWT `exp` passes, and on any 401 answer. A deep link survives sign-in.
- **Shell**: header "Toolbox", caption "Source and evidence workspace", "Log out"; side navigation Home, Catalog, Documentation, Performance, Evaluations, collapsible below 66rem; a skip-to-content link that focuses the main region without changing the route; breadcrumb "Home / <area>"; the main region takes focus on each route change. Routes are hash fragments `#home` (default), `#catalog`, `#documentation`, `#performance`, `#evaluations`, with parameters after `?`; an unknown fragment keeps the current area.
- **Home**: "Your Toolbox", "Find tools for your workflow, read their documentation, and explore recorded performance and evaluations.", and a card per area with "Open <area>": Catalog "Find packaged tools and primitives for a workflow.", Documentation "Read stored instructions and references.", Performance "Explore recorded runs, comparisons, and evidence.", Evaluations "Review current assessments and coverage."
- **Every data region** shows exactly one of: loading ("Loading <subject>" / "Please wait while Toolbox reads the current records."), access ("Access to <subject> is unavailable" / "Your session may have expired or this area may not be available to your account."), error ("Could not load <subject>" / "The service did not return a usable response. Try again."), empty ("No <subject> records" / "This accessible source currently has no records."), or its records. Lists page through the API, 25 per page unless stated, request only the named fields, and append `id` as the last sort key; a request superseded by navigation, paging or sign-out is cancelled and its answer ignored. User text reaches a filter only as an escaped literal (the SDK's `pb.filter` parameters). Record text always renders as text, never as HTML. A URL from the data is a link only when it is a same-origin path (`/…` but not `//…`) or an `http`/`https` URL without credentials, with no surrounding whitespace and no backslash; otherwise it is shown as text.
- **Catalog**: `GET /api/toolbox/catalog`; "Packaged source snapshot: <source_snapshot>."; a search box and "Reset search" filter workflows and plugins by case-insensitive substring of id, name, slug, description or guidance; matches, workflows first, labelled "Workflow" or "Plugin", 10 per page, each with its name and its guidance (or description); "No packaged records match this search." Beside it, "Database extenders": extenders (fields id, slug, name, kind, description, body, entry_file, source; by slug; the same search as `slug ~ q || name ~ q || description ~ q`), each "<name or slug> · <kind>" linking to `#documentation?extender=<id>`; and "Explicit distribution membership": distributions (id, slug, kind, version, members; by slug) as "<slug> · <n> member record(s)". A new search resets all three pagers.
- **Documentation**: the same extender search list; choosing one, or arriving with `?extender=<id>`, loads the extender (id, body, entry_file, source), its source (id, name, url, publisher_kind, maintenance) and its files (id, extender, role, content, relpath; by relpath) and shows "Entry file: <entry_file>", "Source: <name>", "<publisher_kind> · <maintenance>", "Visit source" (a safe URL, else "Source URL unavailable"), "View assessments" linking to `#evaluations?extender=<id>`, the body (or "No stored extender body."), and the files as "<role> · <relpath>", each opening its content. No files: "This metadata-only extender has no stored reader files."
- **Evaluations**: assessments (id, framework, element, extender, eval_run, verdict, evidence, assessor, and the names of the expanded extender, framework and element; filtered by `?extender=<id>` when present; by created) as "<framework> · <element> · extender <name> · <verdict>; <assessor>; <evidence>; eval run <id>", the eval run linking to `#performance?campaign=<eval_run id>`; and job coverage (id, job, eval_run, status, disposition, rationale and the expanded job's name) as "Current job association: <job id> · <job name> · eval run <id> · <status> · <disposition>; <rationale>". Missing values read "<thing> unavailable".
- **Performance**
  - Runs: search over id, campaign, candidate, case, model, harness (substring); configuration filter All / Baseline / With; sort by record id (server order), or by duration or cost ascending, computed client-side over all pages with unavailable values last and ties by id; 25 or 50 per page; changing search, filter or sort returns to page 1. Columns: select, record id with "Campaign: <campaign>", configuration, identity (harness, model, candidate, case), execution validity, grades (as JSON text), outcome (`passed`), duration, cost, "Inspect" linking to `#performance?run=<id>`.
  - Selection: at most two runs (other checkboxes disabled at two), listed in a "Selected (<n>/2)" tray whose entries remove themselves and say "(off page)" when not on the current page; cleared on sign-out.
  - Comparison of the selection. Eligible only when exactly two distinct records share non-empty campaign, candidate, case, harness and model, one has config `baseline` and the other `with`, and both have `measurement.execution.validity` `valid`. Otherwise it says "Select one independently valid baseline and one with-configuration record with matching recorded identity." and the first failing reason: `select-exactly-two`, `duplicate-record`, `missing-<field>` or `<field>-mismatch` (fields checked in the order campaign, candidate, case, harness, model), `configuration-mismatch`, `execution-invalid`. When eligible: "n=1 each. Differences mean with minus baseline; no causality, savings, significance, or installed-state claim."; a table of Duration (ms) and Cost (USD) with baseline, with, and with − baseline plus its percentage of baseline (unavailable unless baseline > 0); a table of sources (source time `ts`, ingestion time `created`, source revision, CLI version); and one grouped bar chart per metric whose two values are available.
  - Measurement display: a run's number or boolean is shown only when `measurement.version` is 1, `measurement.available[<field>]` is true and the value is a finite non-negative number (a boolean for passed and skill_used, an integer for exit_code); otherwise "Unavailable". A legacy run without the envelope shows every metric as Unavailable. A number with 0 < |v| < 0.001 shows in exponential notation with 2 fraction digits, others in en-US format with at most 3 fraction digits, followed by the unit.
  - Campaign search: eval runs (id, slug, kind, method, criteria_text, status, notes; by slug; substring over id, slug, method, criteria_text, notes) linking to `#performance?campaign=<id>`.
  - Run detail (`?run=<id>`): metrics (Duration, Cost, the four token counts, Turns, Passed, Skill used, Exit code); the run record (checks, grades and provenance summarised as their keys or "<n> entries", execution validity and reason, preconditions, source time, ingestion time, source revision = `measurement.source_identity.revision.value` when available, CLI version; the raw measurement, provenance and grades in disclosures; "Source time is not interpreted when timezone is unknown; ingestion time is separate."); evidence = the artifacts the run owns plus those its events and tool calls link, deduplicated by sha256, with "Completeness: complete." or "Completeness: unknown." when any page failed, each "<id> · <sha256> · <n> bytes" (or "size unavailable") with "Open evidence", which requests a file token (`POST /api/files/token`) and navigates to `/api/files/artifacts/<id>/<blob>?token=<token>`, showing "Access denied." or "Could not access evidence." on failure, a newer click on the same artifact superseding an older one; events (by seq) and tool calls (by started_ts), 25 per page, each with its payload, or its input and output, in a disclosure; "Return to runs" restores the list and its focus.
  - Campaign detail (`?campaign=<eval run id>`): its facts (slug, kind, method, criteria, status, notes); "Conformance is not independent output quality; associations are current and can change."; its responses (role, prompt, response, tokens and duration under the eval-response measurement availability, raw response JSON); its assessments (extender linked to its documentation and its evaluations, framework, element, verdict, evidence); "Return to campaigns".

## Persistence

One PocketBase database: 17 collections, 16 base and the view `coverage_gaps`, plus PocketBase's own `users` auth collection. Appendix A defines every field. Collection names, field names and types, select values, relation targets and unique indexes are those of the live instance; v1 changes it only additively:

- `runs.harness` and `run_events.vendor` gain the value `codex`.
- `extenders` gains `assumes` (json, maxSize 2000000), beside `requires`.
- Nothing else. `command` and `mcp` are already values of `extenders.kind`, `frontmatter_dimensions.applies_to`, `frameworks.applies_to` and `sources.publishes`, so projecting them adds no select value.

Schema, access rules and settings are PocketBase JavaScript migrations in `pb_migrations/`, applied by the server at start. They must leave a database built by the previous tooling intact: that database has all 17 collections, created through the REST API without the three additions and without any of these migrations recorded, and real records. There the migrations update each collection in place, keeping existing field ids, existing options and select values, dropping, recreating or renaming no column, and add only the additions, rules and settings. On an empty database they create everything in dependency order (frameworks, sources, extenders, framework_elements, files, distributions, frontmatter_dimensions, eval_runs, eval_responses, assessments, job_coverage, relationships, coverage_gaps, runs, artifacts, run_events, tool_calls). On a migrated database they change nothing. They are forward-only (down migrations do nothing); an application rollback redeploys the previous package and leaves additive fields in place. Tests prove all three against a real server; the legacy-upgrade test builds the legacy schema through the REST API from Appendix A without the additions, inserts a record in every collection, starts the server with the migrations, and checks the records, the field ids and every field option against Appendix A.

Access rules (list, view, create, update, delete; `null` = superusers only):

| Collection | list, view | create, update, delete |
|---|---|---|
| `users` | `id = @request.auth.id` | `null` (no public sign-up; the owner creates accounts) |
| frameworks, sources, extenders, framework_elements, files, distributions, eval_runs, eval_responses, assessments, job_coverage, runs, artifacts, run_events, tool_calls | `@request.auth.id != ''` | `null` |
| frontmatter_dimensions, relationships, coverage_gaps | `null` | `null` |

`artifacts.blob` is a protected file, downloadable only with a short-lived token from `POST /api/files/token`. Observable: anonymous list → 200 with no items and anonymous view → 404 on the readable collections; a user's create, update or delete → 403; a user lists only itself in `users` and gets 404 viewing another user; anonymous `GET /api/toolbox/catalog` → 401; a protected blob without a token is refused. The migrations also turn PocketBase rate limiting on (`rateLimits.enabled = true`, its rules unchanged).

## Non-functional

- No credential appears in any output, report, package, receipt or fixture; the package carries no `.env`, `pb_data`, ledger, log or source-tree file; fixture credentials are synthetic.
- The only network peer is `PB_URL` (for `fixture`, its own loopback server). `report --fixtures`, `package`, `compare-verdicts` and every `--parse-only` need no credentials.
- Package, catalog, receipt, reports and plan output are deterministic.
- Against a local server, a full `ingest` of a tree the size of dotfiles-agents (about 83 extenders and 500 files) and a `load-runs` of 216 rows with their logs each finish within a minute.
- macOS and Linux.

## Architecture expectations

The map must show:

- **Actors**: the owner, who runs `evals` from the shell; the Toolbox reader, an authenticated browser user.
- **External systems**: the dotfiles-agents checkout, read through `--source-root` (roster, externals, unit sources, marketplace manifest, plugin assemblies, workflows table); the agent harness's output, read through `--ledger` and `--runs-dir` (the harness produces it and never calls this product); Railway, which hosts the deployed service and its volume; the PocketBase release on GitHub that the image build downloads; the local PocketBase binary that `fixture` and the tests run.
- **Containers this product owns**: the `evals` CLI; the PocketBase service (the binary with this repository's migrations, catalog hook and packaged catalog); the Toolbox UI, a static single-page app served by that service.
- **Data stores this product owns**: the PocketBase database (17 collections and `users`) with its file storage for artifact blobs; the seed data files `data/*.json`; and, generated and untracked, the report directory and the deploy package.
- **Relationships**: CLI → PocketBase REST as superuser, for every load and report; UI → PocketBase REST with a user token, the catalog route and token-gated file downloads; owner → Railway, deploying a package (outside this product).
- **Flows**, each readable end to end: *project the catalog* (owner → CLI → checkout → extenders, files, distributions, frontmatter dimensions, mechanical assessments); *load a harness campaign* (owner → CLI → ledger and logs → runs, artifacts, run_events, tool_calls); *record an evaluation pass* (manifest → eval_runs and eval_responses, then verdict file → assessments, then curation file → job_coverage and relationships); *render the reports* (CLI → collections → report directory); *package and deploy* (CLI → checkout, UI build and migrations → package → owner → Railway → migrations applied at start); *compare two runs* (reader → UI → runs, comparison, evidence through a file token).

## Out of scope for v1

Deploying to, provisioning or configuring Railway; backups and restores; creating browser accounts; any write from the UI; public sign-up; showing relationships, frontmatter dimensions or coverage gaps in the UI; browser end-to-end automation; running the harness, or loading automatically after a harness campaign; any writer from the database back to a repository; deleting or renaming collections or fields; moving data out of the live instance; the Codex usage digest (moves next to atelier's telemetry); the review-tier trial and the business-data migration tool (dropped); general PocketBase administration; Windows.

## Appendix A — collection schema

Conventions: `text` max 0 is PocketBase's default limit of 5000; every `json` has maxSize 2000000; a `select` allows one value unless "max N"; a `relation` allows one record and does not cascade unless stated; number and bool fields are optional, with no min, max or integer constraint; "req" = required; **new** marks the v1 additions. Every base collection ends with `created` (autodate, on create) and `updated` (autodate, on create and update). Indexes are exact.

- **frameworks**: slug text req · name text req · source_org text · source_url text · kind select req [archetype-set, section-taxonomy, authoring-spec, schema-spec, evaluation-rubric, principles, job-taxonomy, evaluation-methodology] · applies_to select max 7 [skill, agent, hook, mcp, command, plugin, any] · summary text · status select [active, candidate, superseded] · notes text. `CREATE UNIQUE INDEX idx_frameworks_slug ON frameworks (slug)`
- **framework_elements**: framework relation → frameworks req, cascade · slug text req · name text req · element_kind select req [archetype, section, component, principle, rule, dimension, job] · description text · criteria text · category text · sort_order number. `CREATE UNIQUE INDEX idx_fw_elements ON framework_elements (framework, slug)`
- **sources**: slug text req · name text req · url text · publisher_kind select [first-party, marketplace, individual, research-lab, community-collection] · publishes select max 6 [skill, agent, hook, mcp, command, plugin] · trust_tier select [trusted, provisional, watch, avoid] · publishes_evals bool · maintenance select [active, sporadic, dormant, unknown] · license text · adoption_signal text · rationale text max 20000 · evidence_url text max 20000 · status select [active, candidate, superseded] · notes text max 20000. `CREATE UNIQUE INDEX idx_sources_slug ON sources (slug)`
- **extenders**: slug text req · name text · kind select req [skill, agent, hook, mcp, command, plugin] · description text · origin select [authored, sourced, external, vendored] · upstream text · upstream_ref text · repo_path text · source relation → sources · shelf select [core, toggle] · disposition select [qualified, grandfathered-pending-use, demoted, untriaged, orphaned] · requires json · **assumes json (new)** · frontmatter json · body text max 2000000 · entry_file text · file_count number · total_bytes number · word_count number · notes text · retired bool. `CREATE UNIQUE INDEX idx_extenders_slug ON extenders (slug)`
- **files**: extender relation → extenders req, cascade · relpath text req · role select [entrypoint, reference, script, asset, template, eval, doc, license, config, other] · content text max 2000000 · is_binary bool · size_bytes number · sha256 text · language text. `CREATE UNIQUE INDEX idx_files_ext_path ON files (extender, relpath)`
- **distributions**: slug text req · kind select req [bundle, plugin, standalone] · version text · description text · members relation → extenders max 500. `CREATE UNIQUE INDEX idx_distributions_slug ON distributions (slug)`
- **frontmatter_dimensions**: key text req · applies_to select req [skill, agent, hook, mcp, command, plugin] · requirement select [required, optional, harness, custom, deprecated] · description text · spec_framework relation → frameworks · observed_count number. `CREATE UNIQUE INDEX idx_fm_dims ON frontmatter_dimensions (key, applies_to)`
- **eval_runs**: slug text req · kind select req [mechanical, judged, adversarial-review, adjudication, comparative, experiment] · method text max 200000 · criteria_text text max 2000000 · frameworks relation → frameworks max 20 · status select [planned, running, complete, abandoned] · notes text max 200000. `CREATE UNIQUE INDEX idx_eval_runs_slug ON eval_runs (slug)`
- **eval_responses**: run relation → eval_runs req, cascade · role text req · agent_type text · model text · prompt text max 2000000 · response_text text max 2000000 · response_json json · extenders relation → extenders max 100 · tokens number · duration_ms number · measurement json. `CREATE UNIQUE INDEX idx_eval_responses ON eval_responses (run, role)`
- **assessments**: extender relation → extenders req, cascade · framework relation → frameworks req · element relation → framework_elements · eval_run relation → eval_runs · verdict select req [present, partial, absent, not-applicable] · score number · evidence text · assessor text. `CREATE UNIQUE INDEX idx_assessments ON assessments (extender, framework, element, assessor)`
- **job_coverage**: job relation → framework_elements req · disposition select [author, vendor, reference, compare] · status select [covered, partial, gap] · source relation → sources · rationale text max 10000 · eval_run relation → eval_runs. `CREATE UNIQUE INDEX idx_job_coverage ON job_coverage (job)`
- **relationships**: extender_a relation → extenders req · extender_b relation → extenders req · kind select req [duplicative, conflicting, complementary, precedes, feeds-into] · job relation → framework_elements · evidence text max 10000 · assessor text · eval_run relation → eval_runs. `CREATE UNIQUE INDEX idx_relationships ON relationships (extender_a, extender_b, kind, job)`
- **coverage_gaps** (view; columns derived from the query): `SELECT jc.id AS id, fe.slug AS job_slug, fe.name AS job_name, fe.category AS category, jc.status AS status, jc.disposition AS disposition, jc.rationale AS rationale, jc.updated AS updated FROM job_coverage jc JOIN framework_elements fe ON fe.id = jc.job WHERE jc.status != 'covered'`
- **runs**: harness select req [claude, opencode, **codex (new)**] · era select [legacy, post, na] · campaign text · candidate text req · case text req · config select [with, baseline] · kind text · trial number · model text · grader_model text · cli_version text · session_id text · passed bool · skill_used bool · exit_code number · num_turns number · cost_usd number · duration_ms number · input_tokens number · output_tokens number · cache_creation_tokens number · cache_read_tokens number · error text max 2000 · workspace text · checks json · grades json · tool_names json · model_usage json · provenance json · measurement json · log_path text · ts text. `` CREATE UNIQUE INDEX idx_runs_key ON runs (campaign, harness, model, candidate, `case`, config, trial) `` · `CREATE UNIQUE INDEX idx_runs_session ON runs (session_id) WHERE session_id != ''` · `CREATE INDEX idx_runs_log ON runs (log_path)`
- **artifacts**: run relation → runs req (no cascade) · kind select [write_content, edit_diff, screenshot, tool_output] · mime text · blob file (one file, maxSize 10000000, any mime type, no thumbs, **protected**) · sha256 text req · byte_size number · text_ref text max 5000. `CREATE UNIQUE INDEX idx_artifacts_sha ON artifacts (sha256)` · `CREATE INDEX idx_artifacts_run ON artifacts (run)`
- **run_events**: run relation → runs req, cascade · seq number · ts number · vendor select [claude, opencode, **codex (new)**] · role select [assistant, tool_call, tool_result, system, result] · event_type text · tool_name text · tool_call_id text · status text · is_error bool · input_tokens number · output_tokens number · cache_read_tokens number · cache_write_tokens number · cost_usd number · wallclock_ms number · text text max 5000 · payload json · artifact relation → artifacts. `CREATE UNIQUE INDEX idx_run_events_key ON run_events (run, seq)` · `CREATE INDEX idx_run_events_call ON run_events (tool_call_id)`
- **tool_calls**: run relation → runs req, cascade · tool_call_id text req · tool_name text req · input json · output json · status text · is_error bool · wallclock_ms number · started_ts number · artifact relation → artifacts. `CREATE UNIQUE INDEX idx_tool_calls_key ON tool_calls (run, tool_call_id)` · `CREATE INDEX idx_tool_calls_name ON tool_calls (tool_name)`

## Appendix B — seed data files

Provided at init under `data/`; the product reads these files as they are. `data/frameworks.json`: 9 frameworks, 72 elements; an element's `sort_order` is its index.

Provided at init as `data/frameworks.json`.

`data/sources.json`: 10 sources; `upstream_prefixes` maps an external's upstream URL prefix to a source slug.

Provided at init as `data/sources.json`.

`data/frontmatter-spec.json`: spec-known frontmatter keys; `spec_framework` is a framework slug.

Provided at init as `data/frontmatter-spec.json`.

`data/python-stdlib.json`: Python 3.14 `sys.stdlib_module_names`.

Provided at init as `data/python-stdlib.json`.

## Appendix C — test vectors

All computed with the previous Python implementation. Every vector is a file provided at init under `test/vectors/`; each line of an input file is one exact input line, byte for byte.

### C.1 record_sha256

Ledger line 24 of the real `harness/results.jsonl`, 22-field legacy row (opencode, float cost, `\u2192` escapes):

Provided at init as `test/vectors/c1-ledger-line-24.jsonl`.
record_sha256 `379d29aaac065468505cb4b01fa896a040177d63ffffe6ccb970fd8ed063825d`

Ledger line 58 of the real `harness/results.jsonl`, 28-field row (claude, campaign `skillfix`, float cost, non-ASCII):

Provided at init as `test/vectors/c1-ledger-line-58.jsonl`.
record_sha256 `fa5978f82d55751f1dd3324463cff039ead7fd01d9a9bac1012743454669b593`

Ledger line 188 of the real `harness/results.jsonl`, 29-field row (opencode, with `preconditions`):

Provided at init as `test/vectors/c1-ledger-line-188.jsonl`.
record_sha256 `88db541a672c82ebbad6a7c7282188393eeeb9637e14be5ee129fcb6e0dfc66f`

Synthetic number and escaping cases (the real ledger has no exponent or `.0` floats):

Provided at init as `test/vectors/c1-synthetic.jsonl`.
canonical form:

Provided at init as `test/vectors/c1-synthetic.canonical.json`.
record_sha256 `8073810cd9dc23e3254f0fef9c77dc68726e52639f0a93fb4ef6f47be46ad57e`

### C.2 run measurement

`measurement` sent for ledger line 24 (above) loaded with no log and nothing stored yet (sorted keys):

Provided at init as `test/vectors/c2-measurement-line-24.json`.

and for ledger line 188 (its `log_path` file absent):

Provided at init as `test/vectors/c2-measurement-line-188.json`.

Its run body sends exactly these fields: `cache_creation_tokens`, `cache_read_tokens`, `campaign`, `candidate`, `case`, `checks`, `cli_version`, `config`, `cost_usd`, `duration_ms`, `era`, `exit_code`, `grader_model`, `grades`, `harness`, `input_tokens`, `kind`, `log_path`, `measurement`, `model`, `num_turns`, `output_tokens`, `passed`, `session_id`, `skill_used`, `tool_names`, `trial`, `ts` (`era` is `na`, `session_id` `""`, `log_path` the ledger value).

### C.3 log parsing

**Claude log** (its `Write` content is the letter `x` repeated 5001 times; `iVBORy1maXh0dXJl` is the base64 of the 12 bytes `\x89PNG-fixture`):

Provided at init as `test/vectors/c3-claude.log`.
Run meta: era `legacy`, session_id `sess-1`, provenance `{"apiKeySource": "apiKeyHelper", "plugins": [], "tools": ["Bash", "Read", "Skill"]}`, model_usage `{"claude-sonnet-4-5": {"costUSD": 0.01}}`.

Event rows (non-null fields except payload; `artifacts` = the shas in order, the first becomes `artifact`):

Provided at init as `test/vectors/c3-claude.events.jsonl`.
Payload of seq 4 and seq 6 after excision and mirror dedup:

Provided at init as `test/vectors/c3-claude.payloads-seq4-seq6.jsonl`.
Tool calls:

Provided at init as `test/vectors/c3-claude.tool-calls.jsonl`.
Artifacts (deduplicated): `c4c7a80748655c031bc38b16ba41e13650acfe8f0e5b4b1841d3d2f7a9616450` screenshot image/png 12 bytes, file `c4c7a8074865.png`; `89206d01a7a5f7f6d904c37e473b8b9c695376f9bada9711cde47b23aff314f9` write_content text/plain 5001 bytes, file `89206d01a7a5.txt`.

**Opencode log:**

Provided at init as `test/vectors/c3-opencode.log`.
Run meta: era `na`, session_id `ses-oc`, rollup `{"cache_creation_tokens": 44, "cache_read_tokens": 33, "cost_usd": 0.005, "duration_ms": 1500, "input_tokens": 11, "output_tokens": 22}`.

Event rows:

Provided at init as `test/vectors/c3-opencode.events.jsonl`.
Payload of seq 1 (`filediff.patch` deduplicated):

Provided at init as `test/vectors/c3-opencode.payload-seq1.json`.
Tool-call bodies as sent (json coercion turns the output string `"[1,2]"` into a list):

Provided at init as `test/vectors/c3-opencode.tool-calls.jsonl`.
