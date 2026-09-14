# Interaction

Input routing, discoverability, startup, instrumentation, crash handling — and first, whether to build a full-screen TUI at all. Verified 2026-08-01.

Law numbers (`L…`) refer to `laws.md`.

---

## 0. Should this be a TUI at all?

Answer this before anything else. A non-fullscreen CLI — streaming lines to stdout with ANSI colour, no alternate screen, no mouse capture, no scroll regions — is exempt from most of the hard problems in this domain. Native scrollback, native find, native click-drag-copy, working pipes, no reflow subsystem.

**Score these five. Two or more "yes" justifies full-screen; zero or one does not.**

1. **Does content change in place after it is printed?** A status column that flips, a diff whose hunks fold. If every line is final when emitted, you are writing a log, not a UI.
2. **Is there modal navigation?** Panels you focus between, a dialog stack, modes that change what keys mean. If the only mode is "typing at a prompt", a readline composer over normal output covers it.
3. **Does anything need spatial persistence?** A fixed input box, a status bar, a tree on the left. Persistence is the one thing native scrollback genuinely cannot give you.
4. **Is there direct manipulation?** Selecting, expanding, filtering things on screen — interacting with what's drawn, not just reading it.
5. **Is the session long-lived?** Minutes to hours in one process. A tool that runs 900ms and exits should never take the screen.

**The price list, itemised** (Claude Code's opt-in fullscreen renderer, `code.claude.com/docs/en/fullscreen`):

| Before | With alternate screen |
|---|---|
| `Cmd+f` / tmux search finds text | `Ctrl+o` transcript mode, then `/` to search or `[` to dump into real scrollback |
| Native click-drag select and copy | In-app selection; app writes clipboard via `pbcopy`/`wl-copy`/OSC 52 |
| `Cmd`-click a URL | App-handled, and "the terminal mouse protocol has no way to encode the `Cmd` key" |
| Click-drag selects text even while the app has mouse capture on | Mitigated, not solved — the three L45 mitigations |

Plus: the content "lives in the alternate screen buffer instead of your terminal's scrollback", so your scrollback is whatever you implement. claude-code#38283 is the resulting report — a user with `history-limit 200000` in tmux found the app capped near 2000 lines, and "important output — tool results, diffs, earlier conversation — scrolls out of reach." All of that was free before.

**Both major agent CLIs ship non-fullscreen as first-class.** Codex has `AltScreenMode::Never`, documented "Inline mode only, preserves scrollback", plus `--no-alt-screen` overriding config (`codex-rs/tui/src/lib.rs::determine_alt_screen_mode`). Claude Code ships fullscreen as an opt-in research preview behind `/tui fullscreen`; the default classic renderer "keeps the conversation in your terminal's native scrollback so `Cmd+f` and tmux copy mode work as usual."

**What justifies it.** No flicker, "memory stays constant regardless of conversation length" because only visible messages stay in the render tree, an input box that does not move while output streams, mouse support. The flicker win is largest "in terminal emulators where rendering throughput is the bottleneck, such as the VS Code integrated terminal, tmux, and iTerm2." Worth the bill for a session that lasts hours.

**Right:** decide on day one; if it is close, put the renderer behind a boolean and ship both. Codex and Claude Code each did, and each can switch at runtime. Cheap on day one, architectural by month three (L46). **Wrong:** going full-screen "because it looks more serious", then owing a scrollback implementation, a selection model, a clipboard fallback, and a mouse-capture opt-out. And regardless of the four questions: if output is ever piped, redirected, or read by CI, build the non-TTY path first.

---

## 1. Focus and key routing

**Define one routing order and write it down before the second component exists:**

```
1. hard global escape hatches   (quit, suspend — must work from inside a modal)
2. top of the modal/dialog stack (traps everything else)
3. the focused component        (and only it)
4. bubble to focused ancestors  (until one consumes)
5. context bindings, then global bindings
```

Crush states its version as a rule in `internal/ui/AGENTS.md`: "Dialog messages are intercepted first in `Update` before other routing" and "Focus state determines key event routing: `uiFocusEditor` sends keys to the textarea, `uiFocusMain` sends them to the chat list." Focus is a single enum field on the top model — `focus uiFocusState` — not a flag per component (L22).

**Give sub-components a consumed-guard, not a full model.** Crush, verbatim:

> **`Attachments`** and **`Completions`** have non-standard `Update` signatures (e.g., returning `bool` for "consumed") that act as guards, not as full Bubble Tea models.

The parent keeps control of the order. A child returning a model and a command has already acted by the time you learn whether it wanted the key; a child returning `bool` lets the parent try the next handler.

```go
func (m *UI) handleKey(k tea.KeyMsg) tea.Cmd {
    if m.dialog.Len() > 0 { return m.dialog.HandleMsg(k) }   // 2: modal traps
    if m.completions.Update(k) { return nil }                 // 3: guard consumed it
    if m.focus == uiFocusEditor { return m.editor.Update(k) }
    return m.globalBindings(k)                                // 5
}
```

**Why:** the failure is silent and intermittent. A key handled twice makes `d` delete an attachment *and* scroll half a page. A modal that does not trap lets `Ctrl+P` open a palette *behind* the confirmation you were supposed to answer — and now Escape closes the wrong one.

**Make modals trap by construction, not by every handler remembering to check.** lazygit returns a different binding set entirely while a prompt is open (`pkg/gui/keybindings.go`): "if the search or filter prompt is open, we only want the keybindings for that context. It shouldn't be possible, for example, to open a menu while the prompt is showing; you first need to confirm or cancel the search/filter."

**The three bug classes.**

- *Key fires in two places.* Two components matched, neither reported consuming. Make "consumed" an explicit return value, not an inferred one.
- *Modal does not trap.* Globals were evaluated before the stack top. Fix by ordering, in exactly one place — not `if !modalOpen` scattered through handlers.
- *A binding works everywhere except inside a text input.* Usually correct behaviour nobody documented: the input legitimately consumes printable characters. The real bug is the inverse — gemini-cli#849, where `Enter` was globally bound to submit and users could not type a newline into their own prompt. Reserve modified chords (`Ctrl`/`Alt`) for global actions, keep bare letters for non-input contexts, and never bind an unmodified printable key globally.

**Make precedence explicit where two sets overlap.** lazygit prepends user custom commands "because we want to give our custom keybindings precedence over default keybindings", and its menu carries a `keybindingsTakePrecedence` flag with a comment for the one inverted case — the keybindings menu itself, where essential bindings must shadow item shortcuts so the menu stays an accurate cheat sheet (`pkg/gui/context/menu_context.go`).

**Add these to the text-area checklist (L49), on top of the ones laws.md already names.** A UTF-8 sequence split across two reads is one key, not several — buffer incomplete multi-byte sequences instead of decoding partial bytes as garbage. Dead keys and combining marks arrive as multi-codepoint edits, not one keystroke per codepoint — apply them as a single edit. A paste over your size cap gets a placeholder ("pasted 340 lines") instead of flooding the composer with raw text the user never asked to see inline.

---

## 2. The Escape problem

Esc is `0x1b`. Every escape sequence begins with `0x1b`. Alt+X is conventionally `0x1b` then `X`. On a lone `0x1b` the parser cannot know which — until more bytes arrive or enough time passes.

**Legacy answer: a timeout.** Values in shipping code:

| Where | Value |
|---|---|
| Textual `constants.ESCAPE_DELAY` | `_get_environ_int("ESCDELAY", 100, minimum=1) / 1000.0` — **100ms**, env-overridable |
| Claude Code Ink input layer | `NORMAL_TIMEOUT = 50` ms; `PASTE_TIMEOUT = 500` ms (claude-code#29129) |
| tmux `escape-time` | historically **500ms**; `set -s escape-time 0` is the near-universal dotfile fix |
| ncurses | `ESCDELAY`, historically 1000ms |

Textual's docstring is the honest framing: "The delay (in seconds) before reporting an escape key (**not used if the extend key protocol is available**)." Its parser (`src/textual/_xterm_parser.py`) comments "Could be the escape key was pressed OR the start of an escape sequence", reads with `yield read1(constants.ESCAPE_DELAY)`, and emits `events.Key("escape", "\x1b")` on `ParseTimeout`.

**Modern answer: the kitty protocol's disambiguate flag.** Flag `0b1` "will cause the terminal to report the Esc, alt+key, ctrl+key, ctrl+alt+key, shift+alt+key keys using CSI u sequences instead of legacy ones", which exists precisely because "pressing the Esc key generates the byte 0x1b which also is used to indicate the start of an escape code." Escape becomes `CSI 27 u` — unambiguous, zero delay.

```
query:  CSI ? u     → reply CSI ? <flags> u   (no reply within a beat = unsupported)
push:   CSI > 1 u   (1 disambiguate; 2 event types, 4 alternate keys, 8 all-keys, 16 assoc. text)
pop:    CSI < u
```

**What breaks.**

- **tmux swallows the negotiation.** claude-code#29129: outside tmux, Claude Code sends `\033[>1u`, gets `\033[27u`, parses instantly. Inside tmux, "tmux's `input_csi_table` has no handler for the `>` intermediate in `\033[>1u`", the enable sequence "is silently dropped", and "tmux always sends bare `\033` for unmodified Escape to inner programs, regardless of `extended-keys` or `extended-keys-format` settings." The reporter had all three tmux settings correct and still paid 50ms per Escape. Neovim's workaround is DCS passthrough to negotiate with the *outer* terminal.
- **Slow links split the sequence.** Over SSH, `\033[A` can arrive with `\033` in one segment and `[A` in the next, further apart than your timeout. A short timeout turns arrow keys into "Escape, then A" — in a vim-mode editor, a mode change followed by an append. A long timeout makes Escape feel broken. No single value is right for both, which is the entire argument for the protocol.

**Rules.** Query the protocol; if it answers, use it and skip the timeout — do not infer support from `$TERM` (L42). When falling back, use 50–100ms behind an env var: 500ms is unusable for modal editing, 10ms misfires over SSH; raise it further over SSH (L89, `terminal.md` §9). Ship a kill switch (L43) and a fallback binding.

**Accept `alt+esc` as a synonym for `esc` in every Escape binding.** Crush does this throughout `internal/ui/model/keys.go` — `key.WithKeys("esc", "alt+esc")` on `Editor.Escape`, `Chat.Cancel`, `Chat.ClearHighlight`, `Initialize.No`. When a terminal or multiplexer delivers `ESC ESC` the parser reports Alt+Escape; bind only `esc` and a fast double-tap does nothing.

---

## 3. Keybinding design and discoverability

**One file defines every binding.** gemini-cli mandates it twice — in `packages/cli/GEMINI.md` ("**Shortcuts**: only define keyboard shortcuts in `packages/cli/src/ui/key/keyBindings.ts`") and in `.gemini/commands/strict-development-rules.md`:

> Define all new keyboard shortcuts in `packages/cli/src/ui/key/keyBindings.ts` and document them in `docs/cli/keyboard-shortcuts.md`. Be careful of keybindings that require the `Meta` key, as only certain meta key shortcuts are supported on Mac. Avoid function keys and shortcuts commonly bound in VSCode.

Bindings are named by dotted command id (`Command.ESCAPE = 'basic.cancel'`, `'edit.deleteWordLeft'`, `'scroll.pageUp'`) so the id is stable while the key is data. Crush's equivalent is one `KeyMap` struct in `internal/ui/model/keys.go`, nested groups per context plus flat globals.

**Generate the docs from the keymap** (L53). gemini-cli's `npm run docs:keybindings` runs `scripts/generate-keybindings-doc.ts`, which imports `keyBindings.ts` and rewrites the region between `<!-- KEYBINDINGS-AUTOGEN:START -->` and `:END` in `docs/reference/keyboard-shortcuts.md`. lazygit's `pkg/cheatsheet/generate.go` runs under `go generate ./...`, instantiates a dummy app config, walks the real controllers, and emits `docs-master/keybindings/Keybindings_{LANG}.md` per language. Wire it into CI and fail on diff, or it rots as fast as a hand-written table.

**Show bindings in context, not on a help page** (L52). lazygit's footer is built from the live set (`pkg/gui/options_map.go`): current-context plus global bindings, deduplicated, filtered to `len(binding.Keys) > 0 && binding.DisplayOnScreen && !binding.IsDisabled()`, joined with `" | "`, truncated with `…` at terminal width. Note the third predicate — an unavailable binding disappears rather than lying.

**One key shows every action valid right now.** lazygit's `x` menu, `OptionsMenuAction.Call` (`pkg/gui/controllers/options_menu_action.go`) partitions live bindings into three labelled sections — **local** (`ViewName` matches the focused view), **global**, **navigation** — each a selectable, filterable row. Details worth copying:

- Rows carry their `DisabledReason`, so an unavailable action is greyed *with the reason*, not hidden. Discoverability includes "why not".
- Multi-key bindings list every alias in the tooltip (`KeybindingsTooltip + strings.Join(keyLabels, ", ")`).
- `AllowFilteringKeybindings: true` — typing `@` filters on key labels, so "what is bound to `<c-o>`?" is answerable from inside the menu.
- `KeepConflictingKeybindings: true` — because the menu doubles as a cheat sheet, it deliberately shows bindings its own navigation keys would shadow.

**Make the keymap user-remappable, and merge rather than replace.** gemini-cli reads `~/.gemini/keybindings.json` (`Storage.getUserKeybindingsPath`) and "Keybindings are merged with the default bindings" (`loadCustomKeybindings`). Replacing wholesale makes every new default you ship invisible to anyone who ever customised one key.

**Conflict detection: write the test, because the frameworks do not.** They manage precedence explicitly and rely on review. lazygit's `pkg/gui/controllers/menu_controller.go` carries the honest state of the art: "NOTE: if you add a new keybinding here, you'll also need to add it to `reservedKeys` in `pkg/gui/context/menu_context.go`". That comment is a test waiting to be written. Your bindings are already data in one file, so the test is a dozen lines: enumerate every binding, group by `(context, key)`, fail on any group larger than one, with an allowlist for intentional shadowing. It catches two contributors independently picking `Ctrl+T`, which review does not.

---

## 4. Startup latency and first paint

**Paint the chrome before you have the data.** The frame, borders, status bar, and a skeleton or spinner in each pane are computable from zero bytes of I/O. Everything needing network, filesystem, or a subprocess goes into a task that posts a message when it lands.

**Why:** a user cannot distinguish "still loading" from "hung" on a blank screen. lazygit#4770: one added model field put `git for-each-ref --sort=-creatordate --format=... refs/tags` on the startup path at ~400ms per call, run several times — 4.4s on a 5,000-tag repo, 7.9s at ~8,000 tags. Reverted, then reimplemented (lazygit#4777). lazygit#5163 is the same shape at scale: "takes multiple dozen seconds to even open the app" on nixpkgs.

**Make it structural, not a discipline.** gitui puts every git call behind a crate whose stated purpose is exactly this (`asyncgit/README.md`): "The primary goal however is to allow putting certain (potentially) long running git2 calls onto a thread pool. crossbeam-channel is then used to wait for a notification confirming the result. In gitui this allows the main-thread and therefore the ui to stay responsive." gitui's benchmark on the Linux kernel repo (900k commits) reports 24s / 0.17 GB with **Freezes: No**, versus lazygit at 57s / 2.6 GB with freezes and occasional crashes, and tig at 4m20s.

Framework support exists: Textual's `Widget.set_loading(True)` swaps in a `LoadingIndicator` (or your `get_loading_widget()` override) while data is in flight, deferring via `call_later` if not yet mounted. Crush models the pre-data phase in the top-level `uiState` enum — onboarding, initialization, landing, active chat — so "no data yet" is a screen you designed rather than an absence.

**Give it a number.** Under 100ms to first frame feels instant; past ~300ms the user notices; past a second they wonder if it launched. Measure it in CI against a synthetic large fixture (L64) — you will not see the regression on your own small repo, which is exactly how lazygit#4770 shipped.

---

## 5. Performance instrumentation

**Instrument the loop before you profile.** Time goes to four places, in rough order of likelihood:

1. **Your own work on the UI thread** — the subprocess, the query, the parse. Almost always the answer.
2. **Terminal write throughput**, which varies enormously by emulator. Claude Code's docs name the slow ones: "terminal emulators where rendering throughput is the bottleneck, such as the VS Code integrated terminal, tmux, and iTerm2."
3. **Layout/measure**, especially anything touching every item to draw the visible ones (L39). Crush: `list.TotalHeight` "renders **every** item ... Never call `TotalHeight` per frame during a resize."
4. **Draw** — rarely dominant, and the first thing everyone blames.

**Idle CPU is a first-class metric; animations are the usual culprit.** lazygit#4734: "consuming 60% CPU usage in the background" while idle — the `Fetching /` spinner animating at its 50ms default against a background fetch that never completed because a remote was unreachable; raising the interval to 5000ms collapsed CPU use. An animation is an infinite render loop with a friendly name, and every spinner needs a timeout on the thing it spins for.

**What to record.** Timestamp the loop phases into the log file (L48):

```
frame  seq=1841  since_last=16.4ms  events=3  layout=0.9ms  draw=2.1ms  write=11.2ms  bytes=8412
```

Once that line exists, every perf report is a bisect instead of a guess. Add a counter for frames emitted while nothing changed — zero at idle, and lazygit#4734 becomes a one-line diagnosis.

**Tooling.** Textual ships the closest thing to a purpose-built TUI debugger: `textual console` in one terminal, `textual run --dev app.py` in another, `-v` for verbose, `-x` to exclude message groups (`EVENT`, `DEBUG`, `INFO`, `WARNING`, `ERROR`, `PRINT`, `SYSTEM`, `LOGGING`, `WORKER`). It logs every key and click, which makes input-routing bugs reproducible. It does not report frame times — that part is yours.

**Do not accept a perf report without the terminal name.** lazygit#2179, still unresolved: `TERM=vte-direct` was slow, `TERM=xterm-256color` plus `COLORTERM=truecolor` was not, and nobody ever identified what consumed the 5-second gap the debug log showed between init and the main loop. Your test matrix is emulators, not operating systems (L47); your bug template must ask for emulator, multiplexer, and whether it is over SSH.

---

## 6. The crash UI and bug reporting

**Restore the terminal first in the panic hook, then chain to the previous hook** (L75) — code and the full teardown order are in `terminal.md` §1. Get the order wrong and the panic prints a staircase across the alternate screen and vanishes when the shell resets the terminal; the user sees a flash and a dead prompt, and files "it just quit". Add a `Drop` guard so non-panicking exits restore too — codex's `TerminalRestoreGuard::drop` calls `restore_silently()`.

**Publish where the log is, in XDG cache.** gitui: `gitui -l` enables logging, and the README lists `$HOME/Library/Caches/gitui/gitui.log` (macOS), `$XDG_CACHE_HOME/gitui/gitui.log` (else `$HOME/.cache/gitui/gitui.log`), `%LOCALAPPDATA%/gitui/gitui.log` (Windows). Codex writes `codex-tui.log` under its home's `log/` dir with `mode(0o600)` on Unix and a non-blocking appender, defaulting to `codex_core=info,codex_tui=info,codex_rmcp_client=info` overridable by `RUST_LOG`. It also deletes the legacy shared log at startup — "Shared append-only TUI logs could grow without bound." An unbounded log file is a support ticket in six months.

**Enforce "no stray writes to the screen" mechanically** (L48). Codex's TUI crate opens with `#![deny(clippy::print_stdout, clippy::print_stderr)]`. One `println!` in a render path corrupts the frame — permanently, with native scrollback. A lint catches it; a review guideline does not.

**Build "generate a bug report" as a feature.** Codex's `codex-feedback` crate:

- A second `tracing` layer writes into an in-memory **ring buffer**, `DEFAULT_MAX_BYTES = 4 * 1024 * 1024` (4 MiB), capturing at `Level::TRACE` — "Capture everything, regardless of the caller's `RUST_LOG`, so feedback includes the full trace when the user uploads a report." Nobody has to reproduce the bug again with logging turned on.
- A `metadata_layer` collects tags from events with `target: "feedback_tags"` (`MAX_FEEDBACK_TAGS = 64`), so endpoint, auth mode and retry state ride along instead of being scraped out of log text.
- `snapshot()` grabs ring bytes, tags, a thread id, and environment diagnostics — and the environment probe is deliberately narrow: `FeedbackDiagnostics::collect_from_env` reports only whether `HTTP_PROXY`/`HTTPS_PROXY`/`ALL_PROXY` (and lowercase variants) are set, headlined "Proxy environment variables are set and may affect connectivity", because proxies are the top cause of "works on mine".
- Attachments are named and enumerable: `codex-logs.log`, `codex-connectivity-diagnostics.txt`, `codex-doctor-report.json` (explicitly "redacted"), caches, Windows sandbox log.
- Consent is a gate the caller must pass — "The caller is responsible for applying any user-consent gate before setting `include_logs` or passing diagnostic attachments" — and each attachment filename is "shown in Sentry **and in the feedback consent UI**". The user sees the file list before anything leaves.

Minimum viable version: a `/bug` command that writes the last N KB of the in-memory log plus version, terminal name, `$TERM`, multiplexer, and window size to a file, prints the path, and says to attach it. A couple of hours, and it converts unreproducible reports into fixable ones.
