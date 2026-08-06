# Making iTerm2 the macOS default terminal

"Default terminal" is not one setting. It is five uniform type identifiers that drift apart
independently, which is why a machine can open `.command` in Terminal.app, `.sh` in one emulator,
and bare executables in a third:

| UTI | Covers |
|---|---|
| `public.unix-executable` | Executables with no extension |
| `com.apple.terminal.shell-script` | `.command`, `.tool` |
| `public.shell-script` | `.sh` |
| `public.zsh-script` | `.zsh` |
| `public.bash-script` | `.bash` |

## Setting them

`duti` (Homebrew) is the usual tool:

```bash
for uti in public.unix-executable com.apple.terminal.shell-script \
           public.shell-script public.zsh-script public.bash-script; do
  duti -s com.googlecode.iterm2 "$uti" all
done
```

**`duti` exits 0 whether or not the binding took.** LaunchServices silently discards a
(type, role) pair the app does not declare in its `Info.plist`. iTerm2 declares only
`public.unix-executable` with role `Shell`; the script types come from a legacy extension-only
entry, so requesting role `shell` for those is dropped on the floor while role `all` is accepted.
Never treat the exit code as proof.

## Verifying

Read the binding back:

```bash
defaults read com.apple.LaunchServices/com.apple.launchservices.secure | grep -A6 shell-script
```

`duti -x <ext>` is **not** a check on this: it reports the viewer/editor handler, so it keeps
naming the old app even after the terminal binding is correct.

The functional check — what would macOS actually open this with — needs no windows:

```swift
// swift thisfile.swift /path/to/an/executable/script
import AppKit
let u = URL(fileURLWithPath: CommandLine.arguments[1])
print(NSWorkspace.shared.urlForApplication(toOpen: u)?.lastPathComponent ?? "none")
```

## Consequence worth flagging to the user

Claiming a script UTI with role `all` also routes **non-executable** `.sh` and `.command` files to
the terminal rather than to an editor. Double-clicking a script in Finder then runs it instead of
opening it. That is usually intended for `.command`, and often not for a `.bash` file someone was
previously opening in an IDE — say so before changing it.
