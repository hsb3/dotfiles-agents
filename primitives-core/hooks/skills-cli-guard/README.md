# skills-cli-guard

`PreToolUse` on `Bash`. Denies a command that runs the third-party `skills` package through a
runner: `npx`, `bunx`, `bun x`, `pnpx`, `pnpm dlx`, `yarn dlx`, `npm exec`, with any runner
flags (`-y`, `--yes`, `--`, or between the words, as in `pnpm --silent dlx`) and any
`skills@<version>`. Run inside a code repo, that CLI claims every skill under any `.agents/`
or `.claude/` folder, overwrites hand-authored skills and drops a `skills-lock.json`.
`skills remove -g --all` deletes hand-authored skills from the user skills dir. Author, move
and delete skill directories by hand instead.

It reads the command text and never runs a shell. Heredoc bodies are dropped first, wherever
the opener sits, then `shlex` tokenizes the rest in one pass. A runner counts only as the first
word of a simple command, after any `NAME=value` assignments or a reserved word (`if`, `then`,
`do`, `{`, `!` and the like). That includes a command after `;`, `&&`, `||`, `|`, `(`, a
newline, one inside `$( ... )` or backticks, and one in a function body after `name()`. A bare
`npx skills` with no arguments is denied.

## What it lets through

- `npx skills --help`, `-h`, `--version` and `-V`, when those are the only arguments (a
  trailing redirect such as `2>&1` is fine).
- The words as text: arguments to `echo`, `git commit -m`, `rg` and the like, single- or
  double-quoted spans, heredoc bodies (`<<EOF`, `<<'EOF'`, `<<-EOF`) and `#` comments. That
  includes a body opened inside `"$( ... )"`, as in `git commit -m "$(cat <<'EOF' ... EOF` and
  `gh pr create --body "$(cat <<'EOF' ...`.
- Other packages: `npx skillset`, `npx @scope/skills`, `npx prettier skills`.
- **An unterminated quote fails open.** Everything from the open quote on goes unread, because
  the shell refuses to run that text too. Commands ended before it are still checked.

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
- A `<<` that opens no heredoc: one in quotes or a comment (`-m "a << b"`), or an arithmetic
  shift (`$((1<<2))`). It reads as an opener, so the following lines go unread until one
  equals the word after it.
- A runner flag with a separate value, such as `npm --prefix dir exec skills`.
- A function body written `function f { ... }`. The `f() { ... }` form is read.
- One quoted word near a megabyte, such as a huge `-m "..."` message. `shlex` slows down on a
  single long word and the hook runs past its 10 s timeout. A heredoc body of any size is
  dropped before `shlex` and stays fast.
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
