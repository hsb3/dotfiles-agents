# skills-cli-guard

`PreToolUse` on `Bash`. Denies a command that runs the third-party `skills` package through a
runner: `npx`, `bunx`, `bun x`, `pnpx`, `pnpm dlx`, `yarn dlx`, `npm exec`, with any runner
flags (`-y`, `--yes`, `--`) and any `skills@<version>`. Run inside a code repo, that CLI claims
every skill under any `.agents/` or `.claude/` folder, overwrites hand-authored skills and drops
a `skills-lock.json`. `skills remove -g --all` deletes hand-authored skills from the user skills
dir. Author, move and delete skill directories by hand instead.

It reads the command text and never runs a shell. The text is split into logical lines, heredoc
bodies are dropped, and `shlex` tokenizes each line. A runner counts only as the first word of
a simple command, after any `NAME=value` assignments or a reserved word (`if`, `then`, `do`,
`{`, `!` and the like). That includes a command after `;`, `&&`, `||`, `|`, `(`, a newline, and
one inside `$( ... )` or backticks. A bare `npx skills` with no arguments is denied.

## What it lets through

- `npx skills --help`, `-h`, `--version` and `-V`, when those are the only arguments (a
  trailing redirect such as `2>&1` is fine).
- The words as text: arguments to `echo`, `git commit -m`, `rg` and the like, single- or
  double-quoted spans, heredoc bodies (`<<EOF`, `<<'EOF'`, `<<-EOF`) and `#` comments.
- Other packages: `npx skillset`, `npx @scope/skills`, `npx prettier skills`.
- **An unterminated quote fails open.** Everything from the open quote on goes unread, because
  the shell refuses to run that text too. Complete lines before it are still checked.

## What it cannot see

Not containment. It catches the plain mistake, not a determined workaround.

- A runner behind a wrapper: `env`, `sudo`, `command`, `exec`, `xargs`, `bash -c '...'`, or a
  script file.
- The CLI reached any other way: `npm x`, `node_modules/.bin/skills`, or a globally installed
  `skills` binary run directly.
- A `$(...)` or backticks inside double quotes, such as `x="$(npx skills list)"`. `shlex` returns
  the quoted span as one word.
- A quoted or escaped `;`, `|`, `&` or `(`. It reads as an operator, so a later word can look
  like a command.
- A `#` inside a word, such as `${#x}`. It starts a comment, and the rest of that line goes
  unread.
- An arithmetic `<<`, such as `$((1<<2))`. It reads as a heredoc opener, so the following lines
  go unread until one equals the operand.
- Spelling games such as `npx sk""ills`. The text must contain `skills` to be scanned at all.

## Override

```bash
ATELIER_SKILLS_CLI_OVERRIDE=1 npx skills ...
```

The assignment must come before the runner, on the same command. The same string on an earlier
line or command, after `export`, or as an argument is not an override. Use it only when the run is
deliberate and cannot touch hand-authored skills. Nothing is logged.

## Targets

`claude-code` only. Nobody has checked which shell Codex runs commands in, so it is not a target.
