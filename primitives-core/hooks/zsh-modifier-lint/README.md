# zsh-modifier-lint

`PreToolUse` on `Bash`. Denies an unbraced `$NAME:` or `$<digits>:` followed by a letter zsh
applies as a history modifier, because the command runs under zsh and zsh rewrites it silently:
`T=main; git push origin $T:refs/heads/x` expands the refspec to `mainefs/heads/x`, where
bash keeps `main:refs/heads/x`. The letters are `a c e h l q r s t u A P Q`, plus `&` inside
double quotes or an unquoted heredoc (`:s` is an error, the rest corrupt silently). `f`, `g`
and `w` prefix a modifier, so `$B:feature/x` (`:fe`) and `$B:gh-pages` (`:gh`) are hits too. The deny names each
hit and its rewrite (`$T:refs` becomes `"${T}":refs`: brace and quote the name, keep the rest
outside the quotes so a glob in it still expands), up to five per deny. Inside backticks an
escaped `\$T:r` is a hit too, because the shell drops that backslash before the inner command
runs.

It reads the command text only and never runs a shell. A malformed payload or a non-`Bash`
tool exits 0 with no output.

## What it lets through

- The braced form `${T}:r`, an escaped `\$T:r` outside backticks, an escaped colon `$T\:r`, and `"$T":r`.
- A non-letter after the colon: `$PATH:/usr/bin`, `$HOME:$X`, `$T:-x`, `$T:=x`, `$T:+x`, `$T:?x`.
- Letters zsh leaves alone, such as `$B:main`, `$B:fix/y` and `$B:wip`.
- An unquoted `$T:&`, where `&` ends the word before zsh can read it as a modifier.
- Single-quoted text, `$'...'`, and the body of a quoted heredoc (`<<'EOF'`, `<<"EOF"`, `<<\EOF`).
- A `#` comment. A `#` that starts an unquoted word runs to the end of the line, as it does
  when zsh runs a command non-interactively, so nothing in it is flagged.

## What it cannot see

- Special parameters (`$?`, `$$`, `$#`, `$*`, `$@`, `$-`, `$!`), `$#NAME`, subscripts
  (`$T[1]:r`), and the `F` and `W` prefixes, which take a delimited argument (`$T:F:2:r`).
- A heredoc ends at a line equal to its delimiter, with leading tabs stripped for `<<-`. The
  delimiter is one unspaced word, and a terminator glued to more text (`EOF)`) is not one, so
  the body runs to the end of the command.
- A `<<` inside arithmetic (`$((1<<2))`) is read as a heredoc opener, so the rest of the command
  is scanned as an unquoted heredoc body, where single quotes do not protect.
- Parentheses in `$( )` are counted, so a `case` pattern's `)` closes it early. In `"$(case $y in
  a) echo '$T:r';; esac)"` the rest is then read as double-quoted text and the single-quoted `$T:r` is
  flagged, though zsh prints it literally.
- Inside an unquoted heredoc body, `$( )` is not tracked: a single-quoted `$T:r` or a separating
  `&` inside one is flagged.
- Text another shell builds or reads later: `eval "$cmd"`, a script file, or `zsh -c '$T:r'`.

## Override

```bash
ATELIER_ZSH_MODIFIER_OVERRIDE=1 cc -o $f:r $f
```

For a modifier you mean. The assignment must come at command position on the command that
holds the hit, or on a command that encloses it (`ATELIER_ZSH_MODIFIER_OVERRIDE=1 echo
$(basename $T:r)`). The same string as an argument is not an override, and neither is an
assignment on the line before, which a newline ends as `;` does. Nothing is logged.

## Targets

`claude-code` only. The shell Codex runs commands in is unverified. The hook does not check which
shell Claude Code uses: under bash a hit is not corrupted, but the braced rewrite reads the same there.
