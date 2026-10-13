# agent-harness — product spec (v1)

A command-line tool the owner runs by hand or from a weekly schedule. It measures whether a coding-agent extender (a skill, a set of subagent definitions, or a Claude Code plugin, called the **candidate**) makes a headless coding agent better at real tasks.

For each test case it does the following:
- copies the case's fixture workspace into a throwaway directory;
- runs one agent CLI (Claude Code, opencode or Codex) on the case's prompt, twice over: once with the candidate injected (config `with`) and once without (config `baseline`);
- runs each CLI under a per-run home, so the operator's own configuration never leaks in;
- grades the final workspace with the case's deterministic `check.py` and an LLM rubric grader;
- appends one JSON row per trial to an append-only ledger.

The number that matters is the **with − baseline pass-rate delta**, computed within one (campaign, harness, model) cell. The tool has no server, no database and no parallelism.

## Stack

- **Language and runtime:** TypeScript on Bun 1.4 (developed against 1.4.3).
- **Dependencies:** no runtime dependencies. The only devDependencies are `typescript` 7.0.2 and `@types/bun` 1.4.2, as exact pins (as provisioned). Bun's 3-day `minimumReleaseAge` rejects anything newer.
- **Binary:** package `bin` name `agent-harness`.
- **Gate:** `bunx tsc --noEmit && bun test`.

The test suite never runs a real agent CLI and never reaches the network:
- It puts stub executables named `claude`, `opencode`, `codex` (and `python3` where useful) first on `PATH`.
- Each stub records its argv, cwd and environment, prints one of the recorded streams in Appendix A to stdout, and exits with the code given there.
- The two shipped `check.py` files need a real `python3`. Tests that run them skip when none is on `PATH`.

## Behaviour

| Command | Does | Output | Exit |
|---|---|---|---|
| `agent-harness <candidate> --candidate-dir <path> [run flags]` | Runs the **grid** for one candidate. For every (harness, model) cell that passes preflight, it runs every case × config × trial whose resume key is not already in the ledger, one **trial** each, and appends one row per trial. A cell that fails preflight prints why and is skipped; the other cells still run. A failed trial is data, not an error. | Per cell: the preconditions line, one progress line per trial run, the summary line, then the report for `<candidate>`. | 0 when at least one cell passed preflight. 1 when none did. 2 on bad input. 3 on an unknown harness. |
| `agent-harness <candidate> --candidate-dir <path> --smoke [--harness] [--model] [--timeout] [--runs-dir]` | **Loadability check** per cell. Injects the candidate into an empty workspace and sends the prompt `Reply with exactly: OK`. Loads no cases, does no grading and writes no ledger row, but writes a log. A cell fails on plugin errors, on a kind its harness cannot host, or on a non-zero exit. | One smoke block per cell. | 0 when at least one cell ran and every cell that ran passed, else 1. 2 on bad input. 3 on an unknown harness. |
| `agent-harness <candidate> --report [--results]` | Aggregates every ledger row of `<candidate>`, across all campaigns, harnesses and models. Needs no `--candidate-dir`, and ignores the run flags. | The report. | 0. 3 on an unknown `--harness` value. |
| `agent-harness campaign --cases-dir <dir> --candidates-root <dir> [run flags] [--dry-run]` | **Weekly campaign.** Discovers the cased candidates and runs the grid for each one with a dated campaign label, then prints each candidate's report. Never touches anything belonging to the evals database. | The campaign lines (below), also appended to the campaign log. | 0 when every candidate's run exited 0. 1 when any failed or none were discovered. 2 on bad input. 3 on an unknown harness. |

Validation runs in this order:
1. Harness names are checked first. An unknown one exits 3 with `unknown harness 'x'; valid harnesses: claude, codex, opencode`.
2. Then bad input, which exits 2:
   - any usage error: no candidate name, an unknown flag, a non-integer `--trials` or `--timeout`, or a value below 1;
   - a config other than `with` or `baseline`;
   - no `--candidate-dir` outside `--report`;
   - a candidate path that does not exist (`no such candidate path: <path>`), or that is a file not ending in `.md` (`<path>: not a directory or a flat agent .md file`);
   - a candidate of no recognizable kind;
   - duplicate agent names;
   - an invalid case dataset.

All of these are decided before any agent CLI runs.

`agent-harness --help` prints usage to stdout and exits 0. No arguments prints usage to stderr and exits 2. Every error message goes to stderr.

### Run flags

| Flag | Default | Meaning |
|---|---|---|
| `--harness <list>` | `claude` (`campaign`: `claude,opencode,codex`) | Comma-separated list of `claude`, `opencode`, `codex`. Order is kept and duplicates are dropped. |
| `--model <list>` | the harness default | Comma-separated model ids. Every listed id runs under every listed harness. |
| `--case <id>` | all cases | Run only this case id. |
| `--configs <list>` | `with,baseline` | Config order is kept. |
| `--trials <n>` | `3` | Trials per case × config, numbered from 0. |
| `--campaign <label>` | `""` (`campaign`: `weekly-<YYYYMMDD>`, local date) | First segment of the resume key. |
| `--grader-model <id>` | `claude-haiku-4-5-20251001` | Grader model, recorded on every row. |
| `--timeout <s>` | `600` | Per agent run and per grader run. |
| `--keep-workspaces` | off | Also keep the run directories of passing trials (failing ones are always kept). |
| `--cases-dir <dir>` | `<pkg>/cases` | |
| `--results <file>` | `<pkg>/results.jsonl` | The ledger. |
| `--runs-dir <dir>` | `<pkg>/runs` | Per-trial logs. |

`<pkg>` is the directory holding the harness's `package.json`. The defaults never depend on the current directory. Relative paths given on the command line resolve against the current directory.

**Harness defaults.** When `--model` is omitted, each harness runs one cell with its default model, and the row records that id:

| Harness | Default model recorded | Invoked as |
|---|---|---|
| claude | `claude-sonnet-4-5` | `claude-sonnet-4-5` |
| opencode | `claude-sonnet-4-5` | `anthropic/claude-sonnet-4-5` |
| codex | `gpt-6.1-sol` | `gpt-6.1-sol` |

The row's `model` is always the id as typed, or that default; it is never `default`.

**Grid.** Cells are harness × model, harness-major, in the order given. Each cell first runs **preflight**:
- `claude`: fails when `claude` is not found on `PATH`.
- `opencode`: fails when `opencode` is not found on `PATH`, or when none of the six auth env vars (see Preconditions) is set and non-empty.
- `codex`: fails when `codex` is not found on `PATH`, or when `OPENAI_API_KEY` is unset or empty.

A failed preflight prints `<harness>: CLI not found on PATH` or `<harness>: no credentials — set one of <NAMES>` to stderr.

A cell that passes preflight:
1. runs `<exe> --version` once;
2. prints the preconditions line;
3. walks the cases (sorted by id) × configs × trials 0..n−1, skipping every trial whose resume key is already in the ledger, and printing a progress line after each trial it runs;
4. prints the summary line and the report.

**One trial.**
1. Takes `ts`, the local time `YYYY-MM-DDTHH:MM:SS`.
2. Creates the **run dir** `<tmp>/harness-<harness>-<candidate>-<case>-<config>-<trial>-<random>/`, where `<tmp>` is the OS temp dir and honours `$TMPDIR`. Its `ws/` is a copy of the case's `fixture/`, or an empty directory when the case has none. Every per-run home and config dir below lives inside the run dir.
3. `with`: injects the candidate the harness's way. `baseline`: injects nothing.
4. When the harness cannot host the kind, writes a **skip row**, deletes the run dir and runs no CLI.
5. Codex plugin only: when installing the plugin fails, writes an **injection-failure row**, runs no CLI, and keeps the run dir.
6. Runs the agent CLI with cwd = `ws/` under the timeout, and writes the log.
7. Folds stdout into the trial record (per harness, below).
8. Runs `check.py` if the case has one, then the grader if the case has assertions.
9. Applies the pass rule.
10. Deletes the run dir unless the trial failed or `--keep-workspaces` is set.
11. Appends the row at once, so an interrupted run resumes cleanly, then prints the progress line.

**Pass rule.** A trial passes when all three hold:
- the harness's success test holds;
- it is not the case that the config is `with` and `plugin_errors` is non-empty;
- every check and every grade has `passed: true`.

A trial with no checks and no grades passes on success alone.

**The `error` field.**
- Timeout gives `timeout after <s>s`.
- A missing executable gives `executable not found: <name>`.
- A non-zero exit gives the last 2000 characters of stderr. If stderr is empty, it gives the event error from the fold; failing that, `exit <code>`.
- Exit 0 gives the event error from the fold, or null.

**Console lines.**
- **Preconditions line:** `preconditions: harness=<h> · cli=<cli_version> · campaign=<label or (none)> · model=<model> · grader=<grader model> · timeout=<s>s · auth_env=<names joined by "," or (none)> · network=assumed-available`.
- **Progress line:** `<mark> <harness> <case> <config> trial <n>`, where the mark is `✓` for passed, `✗` for failed and `∅` for a skip row.
- **Summary line:** an empty line, then `<ran> trial(s) run, <skipped> skipped (already in <results path as given>)`.

**Smoke block.** A smoke run uses the same injection, argv, environment and isolation as a `with` trial, in a fresh run dir that is deleted afterwards. It uses the cell's model and `--timeout`, and writes `<runs-dir>/<harness>-smoke-<candidate>-<YYYYMMDD-HHMMSS>-<32 hex>.log`: raw stdout with no header. Output:

```
harness: <harness>
kind: <kind>
plugins loaded: <names joined by ", " | (none) | (not reported)>
✗ plugin_error: <entry>                      (one line per entry; non-string entries as compact JSON)
✗ exit <code>: <first 400 chars of the error field>     (only when the exit code is not 0)
✓ loadability OK | ✗ loadability FAILED
```

Only claude reports which plugins it loaded. opencode and codex print `(not reported)`. A kind the harness cannot host prints `kind: <kind>` then `∅ <harness> cannot host kind=<kind> — skip`, and the cell fails. A failed codex plugin install prints as a `✗ plugin_error:` line.

**Report.** The report covers every row of the candidate. A **cell** is (campaign, harness, model, case, config) over the rows whose `passed` is a boolean. Cells are sorted by those five values as strings, with null read as `""`. For each cell:
- `n`: the number of rows;
- `pass`: the pass rate, with 2 decimals;
- `p@n`: `Y` if any row passed, else `n`;
- `p^n`: `Y` if all rows passed, else `n`;
- `cost`: mean±sample stdev of the numeric `cost_usd` values, 4 decimals each;
- `ms`: mean±sample stdev of the numeric `duration_ms` values, rounded to integers.

The stdev is 0 for a single value. `cost` and `ms` print `-` when the cell has no numbers. An empty campaign prints `-`.

The report has five parts:
1. An empty line, then the title `<candidate> — <N> trial row(s)`, where N counts every row, skip rows included.
2. The table: columns joined by two spaces, each left-aligned and padded to its widest entry (header included), with trailing spaces trimmed. Under the header comes a line of `-` as long as the header line.
3. One delta line per `with` cell that has a matching `baseline` cell: `delta (with - baseline) [<campaign>/<harness>/<model>] <case>: <sign><2 decimals>`. The `<campaign>/` part is left out when the campaign is empty. The sign is `+` for ≥ 0.
4. When there are skip rows: an empty line, `<k> unsupported/skip row(s):`, then one line each: `  ∅ [<campaign>] <harness>/<model> <case> <config>: <error>`. The `[<campaign>] ` part is left out when the campaign is empty.
5. Edge cases. With no rows, the whole report is `no result rows for <candidate>`. With rows but none that carry a pass signal, it is the line `<candidate> — <N> row(s), none with a pass signal` followed by the skip section.

Example:

```

mermaid — 13 trial row(s)
campaign         harness  model              case                      config    n  pass  p@n  p^n  cost           ms
---------------------------------------------------------------------------------------------------------------------
weekly-20261019  claude   claude-sonnet-4-5  add-architecture-diagram  baseline  3  0.33  Y    n    0.1520±0.0101  40112±3120
weekly-20261019  claude   claude-sonnet-4-5  add-architecture-diagram  with      3  1.00  Y    Y    0.1977±0.0123  44168±2010
weekly-20261019  codex    gpt-6.1-sol        add-architecture-diagram  baseline  3  0.67  Y    n    -              61234±5120
weekly-20261019  codex    gpt-6.1-sol        add-architecture-diagram  with      3  0.67  Y    n    -              58810±4410
delta (with - baseline) [weekly-20261019/claude/claude-sonnet-4-5] add-architecture-diagram: +0.67
delta (with - baseline) [weekly-20261019/codex/gpt-6.1-sol] add-architecture-diagram: +0.00

1 unsupported/skip row(s):
  ∅ [weekly-20261019] opencode/claude-sonnet-4-5 add-architecture-diagram with: unsupported: opencode cannot host kind=plugin
```

**Campaign.**
- Both `--cases-dir` and `--candidates-root` are required (exit 2 when either is missing).
- **Candidates** are the subdirectory names of `--cases-dir`, sorted, excluding `_template` and `smoke-echo`. When there are none, it prints `no candidates discovered under <dir>` and exits 1.
- **Candidate path:** the first `<root>/*/<name>/` directory in sorted order, else the file `<root>/agents/<name>.md`. When neither exists, it prints `WARN: no candidate named '<name>' under <root>` and the candidate counts as failed.
- Each candidate runs exactly as `agent-harness <name> --candidate-dir <path>` would, with the campaign's flags. The candidate fails when that run would exit non-zero, which prints `FAILED: candidate '<name>' exited <code>`. The campaign then continues.
- Output, in order:
  1. `=== campaign <label> @ <YYYY-MM-DD HH:MM:SS> ===`
  2. `candidates: <names joined by space>`
  3. each candidate's run output
  4. per candidate, `=== report: <name> ===` and its report
  5. `campaign '<label>' complete: ok`, or `campaign '<label>' complete: <n> failed`, followed by ` (log: <path>)`
- Everything printed is also appended to `<dir of --results>/campaign-logs/<label>.log`.
- **`--dry-run`** resolves the candidates, then for each one prints:
  - `DRYRUN: agent-harness <name> --candidate-dir <path> --cases-dir <dir> --harness <list> --configs <list> --trials <n> --campaign <label>`, with ` --model <list>` appended when given;
  - `DRYRUN: agent-harness <name> --report`.

  A dry run runs nothing, writes nothing (not even the campaign log), and exits by the same rule.
- Re-running on the same day reuses the label, so it resumes.

**Scheduled campaign (optional script).** `scripts/launchd.sh` is POSIX `sh`, and a test runs `sh -n` on it.

| Subcommand | Does |
|---|---|
| `install <cases-dir> <candidates-root>` | Writes `~/Library/LaunchAgents/com.hsb3.agent-harness.campaign.plist`, then runs `launchctl bootout gui/<uid>/<label>` (ignoring failure) and `launchctl bootstrap gui/<uid> <plist>`. Prints `launchctl kickstart -k gui/<uid>/<label>` as the next step, which approves any keychain prompt once. |
| `uninstall` | Boots the agent out and deletes the plist. |
| `status` | Prints the `state`, `last exit` and `next fire` lines from `launchctl print gui/<uid>/<label>`, or `agent not loaded`. |
| `run <cases-dir> <candidates-root>` | 1. Prepends `$HOME/.bun/bin:$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin` to `PATH`. 2. If a `secret` command is on `PATH`, sets each of `ANTHROPIC_API_KEY` and `OPENAI_API_KEY` that is unset from `secret get <NAME>`, never printing a value. 3. Runs `agent-harness campaign --cases-dir … --candidates-root …` with bun. 4. Posts `agent-harness campaign: ok` or `agent-harness campaign: failed` with `osascript` (ignoring failure). 5. Exits with the campaign's exit code. |

The plist contains:
- `Label` `com.hsb3.agent-harness.campaign`;
- `ProgramArguments`: `/bin/sh`, `<pkg>/scripts/launchd.sh`, `run`, the absolute cases dir and the absolute candidates root;
- `WorkingDirectory` `<pkg>`;
- `StartCalendarInterval`: Weekday 1, Hour 9, Minute 0;
- `RunAtLoad` false;
- `StandardOutPath` `~/Library/Logs/agent-harness-campaign.out.log` and `StandardErrorPath` `~/Library/Logs/agent-harness-campaign.err.log`, with `~` expanded.

## Candidates and cases

**Candidate.** `--candidate-dir` names a directory or a single `.md` file. A `.md` file is copied into a fresh temp directory, which becomes the candidate directory and is removed when the command exits. The **kind** is the first match:

| Kind | Rule |
|---|---|
| `skill` | `<dir>/SKILL.md` is a file. The skill name is the directory's base name. |
| `plugin` | `<dir>/.claude-plugin/plugin.json` is a file. Its `name` (default: the directory's base name) and `version` (default `0.0.0`) are used by codex. |
| `agent` | `<dir>` holds at least one top-level `*.md` file other than `README.md` (case-insensitive). |
| none | Exit 2 with `<path>: not recognizable as skill / agent / plugin`. |

**Agent files** are those `*.md` files, sorted by filename. Each is parsed as follows:
- **Frontmatter:** the file starts with a line `---`, and the frontmatter runs to the next line that is `---` (`^---\s*\n(.*?)\n---\s*\n?(.*)$`, dot matches newline).
- **Field value:** the first frontmatter line matching `^<key>:\s*(.+)$`, trimmed, with every leading and trailing `"`/`'` character stripped.
- **Name:** the `name` field; when that is absent or empty, the filename without `.md`.
- **Description:** the `description` field, else the first line of the trimmed body, cut to 200 characters.
- **Body:** the text after the frontmatter (the whole text when there is none), trimmed.

Two files that resolve to the same name exit 2 with `duplicate agent name '<name>': <file1> and <file2>`. Example agent file:

```markdown
---
name: scout
description: Read-only investigator. Use before changing unfamiliar code.
model: haiku
tools: Read, Grep, Glob
---
You are a scout. Report what you find with file paths and line numbers.
```

**Case dataset.** The layout is `<cases-dir>/<candidate>/<case-id>/case.json`, with an optional `fixture/` directory (copied as the workspace) and an optional `check.py`. Subdirectories without `case.json` are ignored, and `--case` selects one id.

`case.json` is `{"prompt": <non-empty string>, "assertions": [{"id": <string>, "text": <string>}]}`. `assertions` is optional, and other keys are ignored.

Each of these errors exits 2:
- `no eval cases at <dir> — copy cases/_template to author some`
- `<file>: not valid JSON`
- `<file>: missing required field 'prompt'`
- `<file>: every assertion needs 'id' and 'text'`
- `no case.json found under <dir>`, with ` for --case <id>` appended when `--case` was given.

Real example (prompt and text trimmed):

```json
{"prompt": "Read `pipeline.py`. It defines five pipeline stage functions, in execution order: `start`, `extract`, `transform`, `load`, `end`. Add a `## Pipeline Flow` section to `PIPELINE.md` containing a single Mermaid flowchart … Do not modify `pipeline.py`.",
 "assertions": [{"id": "a1-stages-in-correct-order", "text": "The Mermaid flowchart in PIPELINE.md represents the five pipeline stages from pipeline.py (start, extract, transform, load, end) in their correct execution order, …"}]}
```

**`check.py`.** It runs as `python3 <case dir>/check.py`, with cwd = the final workspace, a 120 s timeout and the subprocess rules. Its exit code is ignored. Its stdout must be a JSON array of `{id, passed, evidence}`, for example `[{"id":"hello-file-exists","passed":true,"evidence":"HELLO.txt present"}]`. Any failure becomes `[{"id":"check.py","passed":false,"evidence":"check-error: <reason>"}]`: a spawn error, a timeout, stdout that is not JSON, or JSON that is not an array. Existing checks use the Python standard library only.

## Agent CLIs

**Common rules.**
- The executables `claude`, `opencode`, `codex` and `python3` are found by bare name on `PATH`.
- A child's environment is the harness's own environment, minus the scrub set listed for each harness and the four vars `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_CACHE_HOME` and `XDG_STATE_HOME`, plus the per-run values listed for each harness.
- Credentials reach a CLI only through environment variables. Nothing the harness writes contains a credential.
- `cli_version` is the trimmed stdout of `<exe> --version`. It is `unknown` when stdout is empty, and `unavailable` when the executable is missing or takes longer than 30 s. Real values: `2.1.296 (Claude Code)`, `opencode v2.0.25`, `codex-cli 0.162.1`.
- Every fold reads stdout line by line and skips any line that is not a JSON object. The log's first line is a `#` header.
- The **trial record** a fold produces has these fields: `result` (the agent's final text, which the grader sees), `tool_names`, `skill_used`, `plugins` (smoke only), `plugin_errors`, `cost_usd`, `duration_ms`, `num_turns`, `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_creation_tokens`, and an event error. Every value is null or empty unless stated.

### claude (Claude Code 2.1.296)

**argv:**

```
claude -p <prompt> --output-format stream-json --verbose --permission-mode acceptEdits
  --allowedTools Skill,Task,Bash,Edit,Read,Write,Grep,Glob --setting-sources "" --strict-mcp-config
  [injection flags] --model <model>
```

Never pass `--bare`: it hides the Skill and Task tools, so an injected skill or agent loads but can never be called.

**Environment:**
- Scrub every variable whose name starts with `CLAUDE`. This includes `CLAUDECODE`, `CLAUDE_CODE_*` and `CLAUDE_CONFIG_DIR`; when the harness runs inside a Claude Code session these carry the parent session's id, socket and settings.
- Set `HOME=<run>/home` and `CLAUDE_CONFIG_DIR=<run>/claude-config`, creating both.
- Set `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1`. The operator's API organization rejects the `context_management` beta that Claude Code 2.1.296 sends by default. Every call then fails with fixture A1's `API Error: 400 … HIPAA-configured organizations: context_management`. With this variable set, the same call succeeds; this was verified live for `claude-sonnet-4-5` trials and the `--bare` haiku grader.
- `ANTHROPIC_API_KEY` passes through. The CLI authenticates with it directly, and its init event reports `"apiKeySource":"ANTHROPIC_API_KEY"`.

The adapter refuses to run when it cannot create these dirs; there is no path that falls back to the operator's home.

**Injection:**

| Kind | Injection |
|---|---|
| plugin | `--plugin-dir <candidate dir>` |
| skill | A synthetic plugin `<run>/plugin/`. Its `.claude-plugin/plugin.json` is `{"name":"eval-<skill>","version":"0.0.0","description":"eval-harness wrapper for skill candidate <skill>"}` and the candidate is copied to `<run>/plugin/skills/<skill>/`. Then `--plugin-dir <run>/plugin`. |
| agent | `--agents <json>`, where the JSON is `{"<name>":{"description":<description>,"prompt":<body>},…}` with one entry per agent file. |

**Fold.** The output is stream-json, one event per line:

| Event | Contributes |
|---|---|
| `{"type":"system","subtype":"init"}` | `plugins` from `plugins` (smoke prints their `name`s). `plugin_errors` from `plugin_errors`, stored verbatim; an absent key means `[]`. |
| `{"type":"assistant"}` | One `tool_names` entry for each `message.content[]` block with `type:"tool_use"`: its `name`. |
| `{"type":"result"}` | `result`, `total_cost_usd`→`cost_usd`, `duration_ms`, `num_turns`. From `usage`: `input_tokens`, `output_tokens`, `cache_read_input_tokens`→`cache_read_tokens` and `cache_creation_input_tokens`→`cache_creation_tokens`. When `is_error` is true, the event error is `result`. `subtype` is `success` even on errors, so it is not used. |

`skill_used` is true when any tool name is `Skill`. **Success** is exit code 0.

### opencode (opencode 2.0.25)

**argv:**

```
opencode run <prompt> --format json --auto --standalone -m <provider/model>
```

There is no `--dir` flag; cwd is the workspace. `--standalone` is mandatory. Without it, opencode 2.x starts a detached background service (`opencode serve --service`) under the per-run home, and that service outlives the trial and escapes the process-group kill. A model id containing `/` is passed as is; otherwise it gets the prefix `anthropic/`.

**Environment:**
- Scrub every variable whose name starts with `OPENCODE`.
- Set `HOME=<run>/home` and `OPENCODE_CONFIG_DIR=<run>/oc-config`, creating both for both configs. In 2.x that directory is the config root.
- The XDG scrub matters here: opencode honours `XDG_*` over `HOME`. Provider keys pass through.

**Injection:**

| Kind | Injection |
|---|---|
| skill | The name must match `^[a-z0-9]+(-[a-z0-9]+)*$` and be 1–64 characters, otherwise the kind is unsupported, because opencode silently ignores such skills. Copy the candidate to `oc-config/skills/<name>/` and write `oc-config/opencode.json` as `{"$schema":"https://opencode.ai/config.json","permission":{"skill":{"<name>":"allow"}}}`. |
| agent | Write one `oc-config/agents/<name>.md` per agent file (translation below), and `oc-config/opencode.json` as `{"$schema":"https://opencode.ai/config.json"}`. |
| plugin | Unsupported. |

**Agent translation:**

```
---
description: <description as a JSON string literal>
mode: subagent
model: <model>
permission:
  edit: deny
  bash: deny
  <key>: allow
---
<body>
```

- The `model:` line appears only when the frontmatter has a `model`. A value without `/` and without `-` is omitted: `haiku`, `sonnet`, `opus` and `inherit` are aliases opencode cannot resolve. A value containing `/` passes through unchanged. Any other value gets the prefix `anthropic/`.
- `permission:` appears only when the frontmatter has a `tools` field. Split it on commas and whitespace, lower-case each entry, and map `bash→bash`, `edit→edit`, `write→edit`, `read→read`, `grep→grep`, `glob→glob`, `webfetch→webfetch`, `websearch→websearch`; any other tool is ignored.
- Emit `edit: deny` and then `bash: deny`, each only when that key is not allowed. Then emit `<key>: allow` for every allowed key, in sorted order. opencode applies the last matching rule, and it normalizes `bash` to its `shell` action.

For the scout example above, the result is `description: "Read-only investigator. Use before changing unfamiliar code."`, no model line, and `permission:` with `edit: deny`, `bash: deny`, `glob: allow`, `grep: allow`, `read: allow`.

**Fold.** Events are JSONL with a top-level `type` and, usually, a `part`:

| Event | Contributes |
|---|---|
| `step_start` | Counts toward `num_turns` (null when 0). |
| `tool_use` | `part.tool` appended to `tool_names`. `skill_used` is true when any tool is `skill`. |
| `text` | Each non-empty `part.text` is collected. `result` is all of them joined by `\n`. |
| `step_finish` | Sums `part.cost` into `cost_usd`, and `part.tokens.{input, output, cache.read, cache.write}` into input, output, cache-read and cache-creation tokens. Each stays null when no `step_finish` carries it. The 2.0.25 capture had no `step_finish`, so null is normal. |
| `error` | The event error is the first non-empty string among `error.data.message`, `error.message`, `part.message`, `message`, `error.name` and `error` (when it is a string), else `opencode reported an error event`. The last error event wins. It goes to the `error` field only, never to `plugin_errors`. |

`duration_ms` is the harness's wall-clock time for the CLI process. opencode never reports plugins or plugin errors. **Success** is exit code 0.

### codex (codex-cli 0.162.1)

**argv:**

```
codex exec --json --skip-git-repo-check --ephemeral --sandbox workspace-write
  -c sandbox_workspace_write.network_access=true --dangerously-bypass-hook-trust
  -C <workspace> -m <model> <prompt>
```

Workspaces are not git repos, which is why `--skip-git-repo-check` is needed. Network access is on to match the other two CLIs. Hook trust is bypassed so a plugin's hooks run, as they do under `claude --plugin-dir`. Never pass `--ignore-user-config`, because the per-run `config.toml` carries the injected plugin.

**Environment:**
- Scrub every variable whose name starts with `CODEX_`.
- Set `HOME=<run>/home` and `CODEX_HOME=<run>/codex-home`, creating both. `HOME` must be isolated too: codex also discovers skills under `~/.agents/skills`.
- Set `CODEX_API_KEY` to the value of `OPENAI_API_KEY`. `codex exec` authenticates with it, and no `auth.json` is ever written. Codex adds its own system skills under `codex-home/skills/.system/` in both configs.

**Injection:**

| Kind | Injection |
|---|---|
| skill | Copy the candidate to `codex-home/skills/<name>/`. Codex lists it to the model as `<name>: <description>`. |
| agent | Write one `codex-home/agents/<name>.toml` per agent file with exactly three keys: `name`, `description` and `developer_instructions` (the body). Each value is written as a JSON string literal, which is a valid TOML basic string. The frontmatter's `model` and `tools` are not carried over. |
| plugin | Build a local marketplace in `<run>/codex-market/`: copy the candidate to `codex-market/plugins/<plugin>/`, and write `codex-market/.claude-plugin/marketplace.json` as `{"name":"agent-harness","owner":{"name":"agent-harness"},"plugins":[{"name":"<plugin>","source":"./plugins/<plugin>","version":"<version>"}]}`. Then run `codex plugin marketplace add <run>/codex-market --json` followed by `codex plugin add <plugin>@agent-harness --json`, each with the trial's environment, cwd = workspace and a 60 s timeout. If either fails (non-zero exit, timeout or missing executable), the trial becomes an injection-failure row whose message is `codex plugin install failed: <that step's error text>`. On success, codex records the plugin in `codex-home/config.toml` and lists its skills as `<plugin>:<skill>`. |

**Fold.** The stream is JSONL. `item.started` and `item.updated` events are ignored.

| Event | Contributes |
|---|---|
| `{"type":"item.completed","item":{…}}` with `item.type` = `agent_message` | `result` is the last such `item.text`. |
| `item.completed` with `item.type` = `reasoning`, `todo_list` or `error` | Nothing. `error` items are notices: `--dangerously-bypass-hook-trust` emits two in every run. |
| `item.completed` with any other `item.type` | The type is appended to `tool_names`. Examples are `command_execution`, `file_change`, `mcp_tool_call` and `web_search`. `skill_used` is true when a `command_execution` item's `command` contains `SKILL.md`. |
| `turn.completed` | Sums `usage.input_tokens`, `usage.output_tokens`, `usage.cached_input_tokens`→cache-read and `usage.cache_write_input_tokens`→cache-creation; a missing key counts as 0. All four stay null when no `turn.completed` occurs. |
| `turn.failed` | The event error is `error.message`. |
| top-level `{"type":"error","message":…}` | When there is no `turn.failed` and no `turn.completed`, the event error is the last such message. Otherwise it is ignored, because these events also report retries. |

`cost_usd` and `num_turns` are always null: codex reports neither a price nor a per-step count. `duration_ms` is the harness's wall-clock time for the CLI process. `plugin_errors` is empty, or holds the injection-failure message. **Success** is exit code 0 with a non-empty `result`.

### Grader (always claude)

**argv:**

```
claude -p <prompt> --bare --model <grader model> --output-format json --json-schema <schema>
  --allowedTools Read,Grep,Glob --setting-sources "" --strict-mcp-config
```

- It runs with cwd = workspace, the `--timeout` and the subprocess rules.
- Its environment gets the same scrub as a claude trial and the same `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1`, with `HOME=<run>/grader-home` and `CLAUDE_CONFIG_DIR=<run>/grader-config`.
- `--bare` is right here: in that mode auth is strictly `ANTHROPIC_API_KEY`.

The grader runs only for cases with assertions, and the grader is claude even when the trial ran opencode or codex.

**Schema** (passed as compact JSON):

```json
{"type":"object","properties":{"grades":{"type":"array","items":{"type":"object","properties":{"id":{"type":"string"},"passed":{"type":"boolean"},"evidence":{"type":"string"}},"required":["id","passed","evidence"]}}},"required":["grades"]}
```

**Prompt** (verbatim; `{…}` are substitutions):

```
You are an impartial grader for a coding-agent trial. Judge each assertion against the trial workspace (your current directory) and the agent's final response below. You may Read/Grep/Glob files. Be strict: an assertion passes only with concrete evidence you can cite (file path + line, or a quoted excerpt). If you cannot determine an assertion, mark it failed with evidence starting 'unknown:'. Do not give benefit of the doubt.

Workspace files:
{digest}

Agent's final response (truncated):
{result}

Assertions (JSON):
{assertions}

Return JSON matching the schema: every assertion id exactly once.
```

- `{digest}` lists every file under the workspace, recursively, as one line each `<relative path> (<size>B)`, sorted by path. It is capped at 80 lines, followed by `... and <k> more` when longer, and is `(empty)` when there are no files.
- `{result}` is the first 3000 characters of the trial's `result`.
- `{assertions}` is the case's assertions array as compact JSON.

The grades are `structured_output.grades` from stdout, which is one JSON object. Anything else (a spawn error, a timeout, stdout that is not JSON, or no array) gives every assertion `{"id":<id>,"passed":false,"evidence":"grader-error"}`.

## Ledger, resume key and logs

**Row.** One JSON object per trial with exactly these 29 fields. This schema is a contract with the evals loader:

| Field | Type | Value |
|---|---|---|
| `ts` | string | Trial start, local time, `YYYY-MM-DDTHH:MM:SS`. |
| `campaign` | string | `--campaign`; `""` when unset. |
| `harness` | string | `claude`, `opencode` or `codex`. |
| `model` | string | The model id as typed, or the harness default. |
| `candidate` | string | The positional name. |
| `case` | string | The case id. |
| `config` | string | `with` or `baseline`. |
| `trial` | integer | 0-based. |
| `kind` | string | `skill`, `agent` or `plugin`. |
| `grader_model` | string or null | `--grader-model` when the case has assertions and the agent ran; else null. |
| `passed` | boolean or null | The pass rule; null on skip rows. |
| `checks`, `grades` | array of `{id, passed, evidence}` | `[]` when absent or not run. |
| `skill_used` | boolean | From the fold; false when no agent ran. |
| `tool_names` | array of string | In call order. |
| `plugin_errors` | array | From the fold, or the injection-failure message. |
| `exit_code` | integer or null | The agent's exit code. −1 on timeout or a missing executable. The failing step's code on injection failure. Null on skip rows. |
| `error` | string or null | See the `error` field rules. Skip rows have `unsupported: <harness> cannot host kind=<kind>`. |
| `cost_usd` | number or null | |
| `duration_ms`, `num_turns`, `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_creation_tokens` | integer or null | |
| `workspace` | string or null | The absolute path of `<run>/ws` when the run dir was kept; else null. |
| `log_path` | string or null | The trial log's path **relative to the directory containing the ledger file**, `/`-separated, which may contain `..`. Null when no agent ran. |
| `cli_version` | string | |
| `preconditions` | object | See Preconditions. |

The four row variants:
- **Normal row:** all fields as above.
- **Skip row:** `passed:null`, `grader_model:null`, `checks:[]`, `grades:[]`, `skill_used:false`, `tool_names:[]`, `plugin_errors:[]`, `exit_code:null`, every metric null, `workspace:null` and `log_path:null`.
- **Injection-failure row:** the same as a skip row, except `passed:false`, `plugin_errors:[<message>]`, `error:<message>`, the failing step's `exit_code`, and the kept `workspace`.

**Resume key.** `<campaign>|<harness>|<model>|<candidate>|<case>|<config>|<trial>`, where the trial is a decimal number. A missing `campaign` on an old row reads as `""`. A key is done when any row with it exists, whether passed, failed or skipped. Lines that are not JSON objects with these fields are skipped silently, both on resume and in the report.

**Serialization.** Rows are written the way Python's `json.dumps(row, sort_keys=True)` writes them:
- keys sorted by code point at every depth;
- `", "` and `": "` as separators;
- every non-ASCII character escaped as `\uXXXX` with lowercase hex, using UTF-16 code units;
- `/` is not escaped;
- numbers print as JavaScript prints them.

Each row is followed by `\n`. A real row (claude, from the legacy ledger, with its lists and evidence trimmed and `log_path` in its new form):

```json
{"cache_creation_tokens": 36157, "cache_read_tokens": 105942, "campaign": "weekly-20260817", "candidate": "mermaid", "case": "add-architecture-diagram", "checks": [{"evidence": "found 1 ```mermaid fenced block(s) in README.md", "id": "c1-mermaid-fence-in-readme", "passed": true}], "cli_version": "2.1.224 (Claude Code)", "config": "with", "cost_usd": 0.19766235, "duration_ms": 44168, "error": null, "exit_code": 0, "grader_model": "claude-haiku-4-5-20251001", "grades": [{"evidence": "README.md lines 7-17 contain a Mermaid flowchart", "id": "a1-diagram-covers-all-services", "passed": true}], "harness": "claude", "input_tokens": 36, "kind": "skill", "log_path": "runs/claude-mermaid-add-architecture-diagram-with-0-20260817-090006-6b0e3f1c9a2d4e8f8a7b5c3d2e1f0a9b.log", "model": "claude-sonnet-4-5", "num_turns": 12, "output_tokens": 1964, "passed": true, "plugin_errors": [], "preconditions": {"auth_env_present": ["ANTHROPIC_API_KEY"], "campaign": "weekly-20260817", "cli_version": "2.1.224 (Claude Code)", "grader_model": "claude-haiku-4-5-20251001", "harness": "claude", "model": "claude-sonnet-4-5", "network_assumption": "assumed-available", "self_installs": [], "timeout": 600}, "skill_used": true, "tool_names": ["Read", "Read", "Read", "Skill", "Read", "Edit"], "trial": 0, "ts": "2026-08-17T09:00:06", "workspace": null}
```

A codex row differs only in its values: `"harness": "codex"`, `"cli_version": "codex-cli 0.162.1"`, `"cost_usd": null`, `"num_turns": null`, and `"tool_names": ["command_execution", "file_change"]`.

**Preconditions object** (sorted keys): `auth_env_present`, `campaign`, `cli_version`, `grader_model`, `harness`, `model`, `network_assumption`, `self_installs`, `timeout`.
- `auth_env_present` is the sorted **names**, never values, of those of `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_GENERATIVE_AI_API_KEY`, `OPENROUTER_API_KEY` and `GROQ_API_KEY` that are set and non-empty.
- `grader_model` is the `--grader-model` value, even when the case has no assertions.
- `network_assumption` is always `"assumed-available"`.
- `timeout` is an integer in seconds.
- `self_installs` lists the lines of the agent's stdout that contain any of `npm install`, `npm i `, `npx playwright install`, `playwright install`, `pnpm add`, `yarn add`, `bun add`, `pip install`, `pip3 install`, `uv add`, `uv pip install`, `brew install`, `apt-get install`, `cargo install` or `go install`. Each line is trimmed and cut to 120 characters; the result is deduplicated, sorted and capped at 20 entries. It is `[]` on skip and injection-failure rows.

The row's `preconditions` and the log header are the same object.

**Per-trial log.** The path is `<runs-dir>/<harness>-<candidate>-<case>-<config>-<trial>-<YYYYMMDD-HHMMSS>-<32 lowercase hex>.log`, with a local timestamp and random hex. Line 1 is `# preconditions: <preconditions object, same serialization>`. After it comes the agent's raw stdout, verbatim; it is partial on a timeout, and empty when the executable is missing. Stderr is not logged.

## Persistence

- **Ledger:** append-only JSONL at `--results`, created with its parent directory on the first append. Each row is appended as a single write right after its trial; rows are never rewritten or removed. The repo ships an empty `results.jsonl`, tracked in git.
- **Logs:** `--runs-dir`, one file per agent run (trial or smoke). They are never deleted by the harness, and are git-ignored.
- **Campaign logs:** `<dir of --results>/campaign-logs/<label>.log`, appended to. Git-ignored.
- **Run dirs** in the OS temp dir. A run dir is deleted after a passing trial (unless `--keep-workspaces` is set), after a skip row and after a smoke run. It is kept after a failing trial, and its `ws/` path is recorded in `workspace`.
- **Shipped cases:** exactly `cases/_template/rename-this-case/` and `cases/smoke-echo/create-file/` (Appendix B). Real cases live with the primitives they test and arrive through `--cases-dir`.
- The harness writes nowhere else. It never reads or writes the evals unit or its database; ingestion is a separate, deliberate step run by the owner.

## Non-functional

- **Every subprocess** (agent CLIs, the grader, `check.py`, `--version`, codex plugin installs) runs with:
  - a list-form argv and never a shell;
  - stdin from `/dev/null`;
  - its own process group;
  - a timeout, on which the whole group gets SIGKILL and the stdout captured so far is kept.
- An agent run that times out records `exit_code: -1` and `error: "timeout after <s>s"`. A missing executable records `exit_code: -1` and `error: "executable not found: <name>"`. Both still produce a normal row.
- The harness never runs a trial against the operator's real home or config, and never writes a credential to disk. Preconditions record env var names only.
- No runtime dependencies. No network from the test suite. Temp dirs honour `$TMPDIR`, so tests can keep everything inside the repo.
- **Timeout test:** one test proves the group kill, using a stub that starts a sleeping descendant and then hangs. The descendant must be gone afterwards.
- `bunx tsc --noEmit` is clean.

## Architecture expectations

The map must show these elements:
- **Person:** the owner, who runs `agent-harness` by hand.
- **Scheduler:** launchd, which triggers the weekly `campaign` through the optional script.
- **External systems, each with its contract named on the relationship:**
  - **Claude Code CLI**: stream-json argv/env/events. It is used twice: as an agent under test, and as the grader (JSON result with `structured_output`).
  - **opencode CLI**: JSON events, run with `--standalone`.
  - **Codex CLI**: `exec --json` events and the plugin-install commands.
  - **python3**, which runs `check.py` (stdout JSON array).
  - **The Anthropic and OpenAI model APIs**, reached only through those CLIs.
  - **The evals loader**, a downstream consumer outside this system. It reads the ledger (the 29-field row and the 7-field key) and the per-trial logs, linked through `log_path`.
- **Inputs it reads but does not own:** the candidate extender, and an external cases directory.
- **Data stores it owns:**
  - the ledger `results.jsonl`;
  - the `runs/` logs;
  - `campaign-logs/`;
  - the shipped `cases/`;
  - the ephemeral run dirs with their per-run homes.
- **Flows:**
  - **"Evaluate a candidate"** must read as a flow: owner → harness → run dir (fixture copy, injection) → agent CLI → log → `check.py` → grader → ledger row.
  - **"Weekly campaign"** must read as a flow: launchd → script → `agent-harness campaign` → the same trial flow per candidate → ledger and campaign log. A later, separate step has the owner run the evals loader over the ledger.

## Out of scope for v1

- Running trials in parallel, or concurrent harness processes sharing one ledger.
- Docker or VM sandboxing.
- Hosting Claude plugins under opencode.
- Ingesting into evals or PocketBase.
- Codex runtime and hook probes (they belong to atelier).
- Other agent CLIs (copilot, gemini).
- Estimating cost for codex.
- `check` scripts in languages other than Python.
- JSON output from the report.
- CI configuration.
- Windows.
- Rewriting or migrating legacy ledger rows.
- An `--allow-bash` flag.

## Appendix A — recorded streams (test fixtures)

Each stream is a file provided at init under `test/fixtures/streams/`, byte for byte as given to the stub's stdout. The fold expectations stay here.

The **captured** streams come from real runs on 2026-10-12, under exactly the isolation above, with the prompt `Reply with exactly: OK` and a one-line demo skill injected. They are trimmed only of unused fields, and their paths are shortened. The **constructed** streams use the same event shapes, the opencode 1.x shapes, or the documented `codex exec --json` item schema, and add tool calls, errors and usage that a one-word reply cannot show. Each heading gives the exit code a stub should use. Stderr is empty unless stated. Expected folds follow each stream.

**A1. claude, captured (2.1.296, `claude-haiku-4-5`), API error. Exit 1.**

Provided at init as `test/fixtures/streams/A1-claude-api-error.jsonl`.

Fold:
- `plugins` names `eval-demo-skill, cc-plugin-agents-md`; `plugin_errors []`; `tool_names []`; `skill_used false`.
- `cost_usd 0`, `duration_ms 407`, `num_turns 1`, and all four token fields 0.
- Event error, and therefore the row's `error`: the `result` text. Not a success.
- Smoke prints the two plugin names, `✗ exit 1: API Error: 400 …`, and `✗ loadability FAILED`.

**A2. claude, constructed, successful skill trial. Exit 0.**

Provided at init as `test/fixtures/streams/A2-claude-skill-trial.jsonl`.

Fold:
- `tool_names ["Read","Skill","Edit"]`; `skill_used true`; `result "Added the diagram to README.md."`.
- `cost_usd 0.19766235`, `duration_ms 44168`, `num_turns 12`.
- Tokens: input 36, output 1964, cache read 105942, cache creation 36157.
- `plugin_errors []`; error null. A success.

**A3. claude, constructed, plugin load error. Exit 0.**

Provided at init as `test/fixtures/streams/A3-claude-plugin-error.jsonl`.

Fold:
- `plugin_errors [{"plugin":"eval-x","message":"boom"}]`.
- A `with` trial fails even when every check passes; a `baseline` trial is unaffected.
- Smoke prints `✗ plugin_error: {"plugin":"eval-x","message":"boom"}` and FAILED.

**A4. opencode, captured (2.0.25, `anthropic/claude-haiku-4-5`). Exit 0.**

Provided at init as `test/fixtures/streams/A4-opencode-captured.jsonl`.

Fold: `result "OK"`, `num_turns 1`, `tool_names []`, `skill_used false`, and cost and all tokens null (no `step_finish`). Error null. A success. Smoke prints `plugins loaded: (not reported)` and OK.

**A5. opencode, constructed (1.x shapes), skill trial. Exit 0.**

Provided at init as `test/fixtures/streams/A5-opencode-skill-trial.jsonl`.

Fold:
- `tool_names ["skill","read"]`; `skill_used true`; `num_turns 2`; `result "Added the diagram."`.
- `cost_usd 0.014100000000000001`, the floating-point sum of 0.0128 and 0.0013.
- Tokens: input 55, output 354, cache read 32490, cache creation 14290.

**A6. opencode, constructed, error event. Exit 1.**

Provided at init as `test/fixtures/streams/A6-opencode-error.jsonl`.

Fold: event error `invalid x-api-key`. Because stderr is empty, the row's `error` is `invalid x-api-key`. `plugin_errors []`. Not a success. The same stream with exit 0 gives the same `error`, and the trial counts as a success.

**A7. codex, captured (0.162.1, `gpt-6-luna`). Exit 0. Stderr: `Reading additional input from stdin...`.**

Provided at init as `test/fixtures/streams/A7-codex-captured.jsonl`.

Fold:
- `result "OK"`; `tool_names []`; `skill_used false`.
- Tokens: input 12868, output 5, cache read 0, cache creation 12865.
- `cost_usd` and `num_turns` null. Error null. A success.

**A8. codex, constructed, skill trial. Exit 0.**

Provided at init as `test/fixtures/streams/A8-codex-skill-trial.jsonl`.

Fold:
- `tool_names ["command_execution","file_change"]`; `skill_used true`; `result "Added the diagram to README.md."`.
- Tokens: input 24310, output 812, cache read 18944, cache creation 5120.

**A9. codex, constructed, failed turn. Exit 1.**

Provided at init as `test/fixtures/streams/A9-codex-failed-turn.jsonl`.

Fold: `result ""`; all tokens null; event error, and the row's `error`: `unexpected status 401 Unauthorized: Incorrect API key provided`. Not a success.

**A10. codex plugin install, captured. Both steps exit 0.**

`codex plugin marketplace add <run>/codex-market --json` prints:

Provided at init as `test/fixtures/streams/A10-codex-marketplace-add.json`.

`codex plugin add demo-plugin@agent-harness --json` prints:

Provided at init as `test/fixtures/streams/A10-codex-plugin-add.json`.

Afterwards `codex-home/config.toml` holds `[marketplaces.agent-harness]` (`source_type = "local"`, `source = "<run>/codex-market"`) and `[plugins."demo-plugin@agent-harness"]` (`enabled = true`). A stub that exits 1 with stderr `plugin not found` on the second step must produce an injection-failure row with `error: "codex plugin install failed: plugin not found"`.

**A11. grader, constructed (claude `--output-format json`). Exit 0.**

Provided at init as `test/fixtures/streams/A11-grader-result.json`.

Grades: the one entry in `structured_output.grades`. Stdout `not json`, or this object without `structured_output`, gives `[{"id":"a1-diagram-covers-all-services","passed":false,"evidence":"grader-error"}]`.

## Appendix B — shipped cases (verbatim)

These files are provided at init at their shipped paths under `cases/`, identical to the cases in use today.

`cases/_template/rename-this-case/case.json`:

Provided at init as `cases/_template/rename-this-case/case.json`.

`cases/_template/rename-this-case/check.py`:

Provided at init as `cases/_template/rename-this-case/check.py`.

`cases/smoke-echo/create-file/case.json` has no assertions, so it never calls the grader:

Provided at init as `cases/smoke-echo/create-file/case.json`.

`cases/smoke-echo/create-file/check.py`:

Provided at init as `cases/smoke-echo/create-file/check.py`.

Real cases live outside this repo, and are selected by their directory names under `--cases-dir`.
