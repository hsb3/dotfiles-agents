# The terminal as a device

The terminal is shared, stateful hardware you are borrowing. Every mode you set is global to the tty and outlives your process. Verified 2026-08-01.

Law numbers (L…) refer to `laws.md`.

## Before you ship — ten minutes, all testable

1. `kill -9 $(pgrep yourapp)` from another pane. Type in the original shell. If you see no echo, or `^[[<0;40;12M` when you move the mouse, your teardown does not survive SIGKILL — that is expected; what you must verify is that you documented the recovery and that steps 2–5 below *do* work.
2. `kill -TERM`, `kill -INT`, `kill -HUP` — each separately. Shell usable after all three? SIGHUP is the one people miss.
3. Force a panic/unhandled exception in a render path. Shell usable, and is the stack trace *readable* (it will be printed while raw mode may still be on, so it needs `\r\n`)?
4. Ctrl-Z, then `fg`. Then Ctrl-Z, then `bg`, then `fg`. Screen repainted, input working, no double-suspend hang?
5. `yourapp | cat`, `yourapp > /tmp/f`, `yourapp < /dev/null`. No escape sequences in the file, no hang waiting for a terminal reply.
6. `NO_COLOR=1 yourapp`, `TERM=dumb yourapp`, `CI=true yourapp`. Each produces usable output.
7. `printf 'x' | yourapp` in a container with no tty at all. Does not crash, does not block on a capability query.
8. Print `🧑‍🌾`, `👩🏽‍🚀`, `สวัสดี`, `가나다`, and `é` (as `e` + U+0301) inside a box border, at width 40. Border aligned in *your* terminal and in one other?
9. Drag the window edge continuously for five seconds. CPU stays sane, final frame correct, no torn intermediate state left behind.
10. Repeat 1–9 inside `tmux` with `allow-passthrough off` (the default), and inside `tmux` inside `ssh`.
11. Run under a light-background profile. Read every piece of dim/secondary text.
12. Confirm no capability query can block forever: kill the terminal's reply (test in a terminal that doesn't implement it, e.g. Terminal.app for OSC 11) and confirm you time out and continue.
13. Run it over a real SSH link, and again with ~200 ms of added latency (`tc qdisc add dev eth0 root netem delay 200ms`). Escape still cancels without eating the next key, the frame rate degrades instead of queueing, and an unknown `$TERM` on the remote host degrades rather than aborts (§9).

---

## 1. Restore the terminal on every exit path (L71–L75)

**Install teardown before you set the first mode, and make it idempotent and reentrant.** Raw mode, the alternate screen, cursor visibility, mouse tracking, bracketed paste, keyboard-protocol pushes and line wrap are all *terminal* state, not process state. The kernel restores none of it.

**Why.** Raw mode left on: no echo, no line editing, Ctrl-C does nothing — the shell looks hung and the user's only recovery is to type `reset` blind. Mouse tracking left on: every click injects `^[[<0;40;12M` into the shell and native selection is dead. Bracketed paste left on: every paste arrives wrapped in literal `200~`…`201~`. Alternate screen left on: their scrollback is gone. Cursor hidden: permanently invisible.

**Order matters, and it is not the reverse of setup.** Textual's teardown (`src/textual/drivers/linux_driver.py`, `stop_application_mode`):

```python
self._disable_bracketed_paste()      # \x1b[?2004l
self._enable_line_wrap()             # \x1b[?7h
self._disable_in_band_window_resize()# \x1b[?2048l
self.disable_input()                 # SIGWINCH -> SIG_DFL, \x1b[?1000l \x1b[?1006l, tcflush(TCIFLUSH)
termios.tcsetattr(self.fileno, termios.TCSANOW, self.attrs_before)
self.write("\x1b[<u")                # pop kitty keyboard stack
                                     # "must be done before leaving the alt screen"
self.write("\x1b[?1049l")            # leave alt screen
self.write("\x1b[?25h")              # show cursor
self.write("\x1b[?1004l")            # disable focus reporting
```

Two details there are load-bearing: popping the kitty keyboard stack **before** `?1049l` (the terminal associates the stack with the active screen), and `tcflush(TCIFLUSH)` to drop unread bytes so half-consumed escape sequences don't land in the shell.

Ratatui's `try_restore` (`ratatui/src/init.rs`) carries the inverse note: *"disabling raw mode first is important as it has more side effects than leaving the alternate screen buffer."* Pick one order, and run every step even if an earlier one errors — a failed write must not skip `disable_raw_mode`.

**Panic / unhandled exception.** Chain, don't replace. Ratatui:

```rust
fn set_panic_hook() {
    let hook = std::panic::take_hook();
    std::panic::set_hook(Box::new(move |info| { restore(); hook(info); }));
}
```

Bubble Tea's `recoverFromPanic` (`tea.go`) does the same and rewrites `\n` to `\r\n` in the panic text *"to ensure the output is formatted even when restoring the terminal does not work or when raw mode is still active."* Without that, a stack trace prints as a diagonal staircase. Go needs a `recover()` in every goroutine you spawn (`recoverFromGoPanic`); a panic on a render goroutine otherwise kills the process with no teardown at all.

**Signals.** Handle `SIGINT`, `SIGTERM`, `SIGHUP`. Bubble Tea notifies only `SIGINT` and `SIGTERM` (`tea.go:handleSignals`) — SIGHUP, which is what you get when the ssh connection drops or the terminal window is closed, is not covered by most frameworks. Add it. Convert the signal into a normal quit message rather than exiting from the handler, so your single teardown path runs; guard it with a once (`p.shutdownOnce.Do`).

**SIGTSTP / SIGCONT.** Ctrl-Z is a restoration path — but first make sure it is a *signal* at all. In raw mode `ISIG` is cleared (`cfmakeraw` does this), so Ctrl-Z is delivered to you as the byte `0x1A` in the input stream and no `SIGTSTP` is ever raised; a handler you never reach looks identical to a handler you never wrote. Two ways out: leave `ISIG` enabled (you keep signal generation, and give up literal Ctrl-C/Ctrl-Z as bindable keys), or clear it and bind `0x1A` yourself, raising `SIGTSTP` from the key handler — this is what Bubble Tea does. Only then does the handler below run.

Once the signal actually arrives: restore the terminal, *then* stop; on resume, re-claim and force a full repaint. Helix (`helix-term/src/application.rs`):

```rust
signal::SIGTSTP => {
    self.restore_term().unwrap();
    // pid 0 -> whole process group, so the user regains the terminal even when
    // helix was spawned under another process (e.g. `git commit`).
    // SIGSTOP, not SIGTSTP: re-raising SIGTSTP would just re-enter this handler.
    unsafe { libc::kill(0, signal::SIGSTOP) };
}
signal::SIGCONT => {
    for retries in 1..=10 {                  // neovim#12322 / neovim#13084
        match self.terminal.claim() { Ok(()) => break, Err(_) if retries < 10 => continue, .. }
    }
    self.compositor.resize(self.terminal.size());
    self.terminal.clear().expect("couldn't clear terminal");
    self.render().await;
}
```

The retry loop is not paranoia: on resume the tty may briefly refuse you. The related trap is `bg` — the process continues but is now a background job and terminal writes raise `SIGTTOU`. Textual probes for it with a no-op `tcsetattr` guarded by temporary `SIGTTOU`/`SIGTTIN` handlers that re-`SIGSTOP` (`linux_driver.py:start_application_mode`, referencing Textualize/textual#4104) — a no-consequence change that detects the problem before you spin application mode back up.

**SIGKILL and `kill -9` cannot be handled.** Don't pretend otherwise. What you can do: document the one-liner, and keep the damage small by not leaving exotic modes on longer than needed. Recovery, least destructive first:

- `stty sane` — fixes termios (echo, canonical mode). Does **not** touch alt screen, mouse, or paste modes.
- `printf '\033[?1049l\033[?25h\033[?1000l\033[?1002l\033[?1003l\033[?1006l\033[?2004l\033[<u\033[?7h'` — targeted, loses nothing, and for the three symptoms above (mouse, paste, alt screen) it is **strictly better than the soft reset below**. This plus `stty sane` is the complete recovery.
- `\033[!p` (DECSTR, soft reset) — does *not* mean "reset the DEC private modes." DECSTR resets a specific enumerated set — cursor visibility (back on), cursor/keypad modes, the scroll region, charset designations, SGR. It does **not** clear mouse tracking (1000–1006), bracketed paste (2004), or the alternate screen (1049) — i.e. none of the three symptoms this list opens with — and it turns autowrap *off*, which is a new problem in an already-broken shell. Scrollback survives. Useful for a scrambled charset or a stuck scroll region; not a recovery for mode leaks.
- `\033c` (RIS) / `reset(1)` — works, but clears scrollback in most emulators. Last resort, and never something your app emits on its own.

Do not emit RIS as "cleanup." It destroys work the user did before running you.

---

## 2. The non-TTY path is a real path (L76)

**Check `isatty` on the stream you are about to write to, and take a different code path — not a degraded version of the same one.** stdout and stderr are independently redirectable; check the one you're using.

**Why.** `yourapp > out.txt` producing a file full of `ESC[38;5;244m` is the single most common CLI complaint. Worse: a TUI that enters raw mode on a non-tty stdin blocks forever in CI with no output.

Precedence, as implemented in `charmbracelet/colorprofile` (`env.go:Detect`, doc comment quoted):

- `TERM=dumb` is treated as NoTTY unless `CLICOLOR_FORCE=1`
- `NO_COLOR` takes precedence over `CLICOLOR`/`CLICOLOR_FORCE`, and disables *colour* but not bold/italic/faint
- `COLORTERM=truecolor` upgrades to 24-bit; `TERM=*-256color` → 256; `CLICOLOR=1` with no `TERM` → ANSI when on a tty

`NO_COLOR` (no-color.org, proposed 2017): *"present and not an empty string (regardless of its value)"*. Respected widely but not uniformly — colorprofile's `envNoColor` is `strconv.ParseBool(env.get("NO_COLOR"))`, so `NO_COLOR=0` does **not** disable colour there, contrary to the spec. If you implement it, follow the spec; if you consume a library, test it.

`CLICOLOR`/`CLICOLOR_FORCE` (bixense.com/clicolors, BSD-derived): FORCE means *"ANSI colors should be enabled no matter what"* — that is the escape hatch for `yourapp | less -R`.

`FORCE_COLOR` is a *convention*, not a spec with a published site the way `NO_COLOR` (no-color.org) and `CLICOLOR`/`CLICOLOR_FORCE` (bixense.com/clicolors) are. It comes from Node's `supports-color`, where the value is a **level**: `0` disables colour, `1` forces basic 16-colour, `2` forces 256, `3` forces truecolor; a bare `FORCE_COLOR` with no value means "on." Consumers outside the Node ecosystem mostly treat it as a boolean, so accept both readings — any non-`0` value means force, and parse a numeric level if you can use one.

Rich's `Console.is_terminal` shows the shape of a mature check: explicit override → `TTY_COMPATIBLE=0|1` → `FORCE_COLOR` → `isatty()`, with hardcoded `False` for Jupyter and IDLE, *both of which claim to be a tty and cannot handle ANSI*. Special cases like these are why an emulator allowlist fails and a capability check succeeds.

**CI detection has no standard, only a convention.** GitHub Actions sets `CI=true` (announced 2020-04-15); most vendors follow, but the value and semantics vary — `ci-info` and `OndraM/ci-detector` exist precisely because you need a per-vendor table. Treat `CI` as a hint that stdout may be a pipe with a very wide "terminal", not as a capability statement.

**`isatty(stdout)` false does not mean "no terminal available."** A TUI can open `/dev/tty` directly and drive the real terminal there while stdout stays a pipe. That is how a TUI participates in a pipeline: fzf draws its UI on `/dev/tty` and writes only the selection to stdout, so `vim $(fzf)` works. If your app has a "pick something" mode, this is the shape — UI on `/dev/tty`, result on stdout — and it is also the fallback when stdout is redirected but a controlling terminal still exists. `open("/dev/tty")` failing (no controlling terminal at all: cron, a container, a daemon) is the real signal for the headless path.

**`yourapp | head` kills you mid-write.** When the reader closes early the next write gets `SIGPIPE`, whose default action is silent termination — fine, and usually what you want. The trap is a runtime that changed the default: **Rust ignores `SIGPIPE` at startup**, so the write returns `EPIPE`, `println!` panics on the unwrap inside, and the user sees a panic message plus your panic hook's teardown instead of a clean exit. Go's runtime raises `SIGPIPE` again for writes to fd 1/2 but turns it into an `EPIPE` error elsewhere. Decide explicitly: either restore the default disposition (`signal(SIGPIPE, SIG_DFL)` early in `main`) or treat `EPIPE`/`BrokenPipe` on stdout as a normal quit — run teardown, exit 0, print nothing.

**Ship a structured mode.** `--json` (or `--plain`) that is the *same data* through a different renderer, selected before any terminal setup. If your only non-tty behaviour is "same output, no colour", you have not tested the case where there is no controlling terminal at all.

### 2.1 The plain renderer is also the accessibility path

**Name it that way.** The `--plain` / `--json` renderer from above is not just the CI path: it is the path for screen readers, braille displays, and anyone for whom a repainting full-screen grid is unusable. A screen reader reads the terminal's text buffer; a full-screen TUI that repaints regions has no notion of "what changed" to announce, so the whole thing gets re-announced or nothing does. Document the flag as the accessible mode and keep feature parity with it, or it rots.

Inside the TUI path, four rules that cost almost nothing:

- **Never encode state in colour alone.** Red-for-error is invisible to a screen reader, and red-versus-green is unreadable for the ~8% of men with a colour-vision deficiency. Pair every colour with a glyph or a word — `✗ failed` / `● live` / `(queued)`. This is the same discipline as §6, from the other direction.
- **ASCII fallback for box drawing.** Non-UTF-8 locales (see §3), braille and speech output all do better with `+`/`-`/`|` than with `└`/`─`/`│`, and screen readers pronounce line-drawing characters as noise. Same trigger as the width fallback: one flag, one table of glyphs.
- **A reduced-motion switch.** Spinners, progress pulses and typewriter effects are repaint sources that re-announce, and they are a vestibular trigger besides; put every one of them behind a single `--no-animation` flag (plus the env-var form, so it can be set once). This is the same lever as the zero-idle-frames law (L92): the app that draws nothing when nothing changed is the app that is quiet for a screen reader.
- **Don't repaint unchanged regions.** Cell diffing is an accessibility feature, not only a performance one — a repainted-but-identical region is a change event to assistive tech.

**Keep the real cursor where the insertion point is.** The most common accessibility regression in a TUI is hiding the hardware cursor (`CSI ? 25 l`) and painting a fake block in reverse video. That block is invisible to everything outside your process: the IME candidate window positions itself at the real cursor, screen-reader carets and magnifier follow-focus track the real cursor, and the terminal reports the real cursor to the OS. Leave the cursor visible and move it to the logical insertion point as the last thing you write each frame. If you want a different look, ask for it — `DECSCUSR`, `CSI Ps SP q`: `0`/`1` blinking block, `2` steady block, `3` blinking underline, `4` steady underline, `5` blinking bar, `6` steady bar — and restore it on teardown like any other mode. Hide the cursor only where there genuinely is no insertion point (a full-screen list with no editable field), and park it somewhere sane rather than wherever the last write left it.

---

## 3. Display width is not string length, and terminals disagree (L77, L78)

**Measure in grapheme clusters, and cache the result keyed by the width algorithm you chose.** `len(s)` is wrong (bytes/codepoints ≠ cells). `wcwidth` per codepoint is also wrong (it can't see ZWJ sequences). `wcswidth` over the string is closer but still codepoint-based.

**Why.** One cell of error per line and your box border zig-zags; truncation cuts mid-sequence and emits a broken escape or a half emoji. lipgloss#258: Thai text `สวัสดี` in a fixed-width bordered container misaligned because nonspacing combining marks (U+0E31, U+0E35) were counted as width 1; fixed Feb 2024 via grapheme-cluster segmentation.

**Terminals genuinely disagree, and there is no correct answer.** Hashimoto measured 🧑‍🌾 (U+1F9D1 ZWJ U+1F33E, 3 codepoints) on 2023-10-02: **2 cells** in Ghostty, Contour, foot, iTerm2, WezTerm; **4** in Alacritty, GNOME Terminal, kitty, tmux, Warp, xterm; **5** in Windows Terminal; **6** in Terminal.app. Read the *disagreement* as the durable fact and the numbers as a 2023 snapshot. `ucs-detect` (jquast) finds 23 distinct implementations of "Wide" across ~35 terminals, 19 of ZWJ handling; Fitzpatrick modifiers and lone regional indicators are measured inconsistently by foot, WezTerm and Windows Terminal.

Libraries actually used: Go — `rivo/uniseg` and `clipperhouse/displaywidth` (Charm's `x/ansi` exposes both algorithms explicitly as `Method`: `WcWidth` vs `GraphemeWidth`, with `StringWidth` defaulting to grapheme clustering); Rust — `unicode-width` + `unicode-segmentation`; Python — `jquast/wcwidth` (ships tables for many Unicode versions and selects one at import time; the `UNICODE_VERSION` env var pins it, otherwise it uses the latest it carries — so two machines can measure the same string differently, and pinning is the fix. `wcswidth` returns `-1` if any C0/C1 control is present — handle that, don't let `-1` propagate into layout arithmetic).

**East Asian Ambiguous is a user setting, not a property of the text.** Charm gates it on an env var:

```go
var wcOptions = &runewidth.Condition{EastAsianWidth: false, StrictEmojiNeutral: true}
func init() { if ea, err := strconv.ParseBool(os.Getenv("RUNEWIDTH_EASTASIAN")); err == nil && ea { ... } }
```

**You can ask the terminal.** Two mechanisms:

- **Mode 2027** (Unicode Core / grapheme clustering): query `CSI ? 2027 $ p`, enable `CSI ? 2027 h`. If the DECRPM reply is 1 or 2, the terminal does grapheme clustering and your uniseg-style measurement will match it. Implemented in Ghostty, Contour, foot, WezTerm as of 2023–2025; **not in tmux** (absent from tmux CHANGES through the 3.8 development tree, 2026-07).
- **`CSI 6 n`** (cursor position report): print the string, ask where the cursor ended up, subtract. This is ground truth for that emulator, but costs a round trip and requires raw mode, so use it once at startup on a probe string — not per render.

**The `C`/`POSIX` locale is a real deployment, and it breaks wide characters.** With `LANG`/`LC_ALL` unset or set to `C`, a C/C++ `wcwidth` returns `-1` for anything non-ASCII, Python's `locale.getpreferredencoding()` reports ASCII, and Go/Rust — which don't consult the locale — will happily emit UTF-8 the terminal may not be configured to decode. This is not exotic: minimal containers ship no locales at all, `sudo` strips the environment by default (`env_reset`), and `ssh` only forwards `LC_*` if the server's `AcceptEnv` allows it. Read the locale at startup and treat "not UTF-8" as the trigger for the ASCII fallback (§2.1) — plain box characters, no emoji, no ambiguous-width glyphs — rather than discovering it as garbled output. Set `LANG=C.UTF-8` in your own container images.

Practical stance: measure with grapheme clustering, enable 2027 where available, and treat non-ASCII in fixed-width chrome as a hazard — if a border must align, put the risky text inside it with a computed pad, and re-verify after truncation.

---

## 4. Resize is an event stream, not an interrupt (L79)

**Handle `SIGWINCH` by setting a flag or writing to a self-pipe/channel, re-query the size with `TIOCGWINSZ` on the main loop, and throttle repaints.** Never render from the signal handler; almost nothing you want to call there is async-signal-safe.

**Why.** Dragging a window edge emits one SIGWINCH per frame — dozens per second. Naive handling means a full reflow and repaint per signal: the app pegs a core, lags behind the drag, and often ends where it started. The other failure is trusting a stale size: signals coalesce, so the count of signals tells you nothing; only the fresh `ioctl` does.

Zellij throttles at 50 ms (`zellij-client/src/os_input_output.rs`) — **leading-edge, and this is what zellij shipped, not what we recommend**: it renders on the first signal, then blocks the signal thread with `thread::sleep` to space out the next one. It bounds CPU, which was the goal, but it repaints at intermediate geometries and its last repaint is up to 50 ms stale. Read it for the throttle constant, not the shape:

```rust
const SIGWINCH_CB_THROTTLE_DURATION: time::Duration = time::Duration::from_millis(50);
// ...
SignalEvent::Resize => {
    // throttle sigwinch_cb calls, reduce excessive renders while resizing
    if sigwinch_cb_timestamp.elapsed() < SIGWINCH_CB_THROTTLE_DURATION {
        thread::sleep(SIGWINCH_CB_THROTTLE_DURATION);
    }
    sigwinch_cb_timestamp = time::Instant::now();
    sigwinch_cb();
}
```

Bubble Tea takes the same shape without a timer: `listenForResize` receives the signal and calls `checkResize`, which does `term.GetSize(p.ttyOutput.Fd())` and sends a `WindowSizeMsg` — the signal is a *hint to re-measure*, never the measurement.

Trailing-edge is the right debounce, and it is what you should write: emit on the last event of a quiet window, not the first, so the user sees the final geometry and not an intermediate one. Arm a timer on each SIGWINCH, reset it if another arrives, render when it expires — and never sleep on the signal-handling path. 50–100 ms is the range mature implementations use.

**In-band resize (mode 2048)** removes the race entirely: query `CSI ? 2048 $ p`, enable `CSI ? 2048 h`, and the terminal sends `CSI 48 ; rows ; cols ; ypixel ; xpixel t` as ordinary input — ordered with your keystrokes, so you can never repaint at a size that was already superseded. Implemented in Ghostty, iTerm2, kitty, foot (spec last updated 2026-03-14). Textual enables it and gates the SIGWINCH handler on it (`if not self._in_band_window_resize: send_size_event()`) so you don't get both. On Windows there is no SIGWINCH at all, so this is the clean path.

Invalidate every width-keyed cache on resize. Wrapping, height caches and rendered-markdown caches are all functions of width.

---

## 5. Multiplexers filter, rewrite, and lie (L83, L42, L80, L81)

**Assume tmux/screen sits between you and the terminal, that it strips sequences it doesn't parse, and that a query with no reply is the normal case, not an error.**

**Why.** The dangerous failure is silent. Capability *querying* — the thing you were told to do instead of sniffing `$TERM` — breaks when the multiplexer swallows the query and returns nothing. Your timeout fires, you conclude "unsupported", and you permanently degrade in an environment that supports the feature.

anthropics/claude-code#29129 (filed 2026-02-26, tmux 3.6a + Ghostty): the app sends the kitty keyboard enable `\x1b[>1u`; *"tmux's `input_csi_table` has no handler for the `>` intermediate character"*, so the sequence is dropped with no reply and no error. The app keeps receiving bare `\x1b`, can't disambiguate Escape from the start of a sequence, and eats a 50 ms timeout on every Escape keypress. Closed as not planned.

**Passthrough.** tmux wraps a sequence in a DCS with `tmux;` and **every `ESC` inside doubled**:

```
\033Ptmux;\033<your ESC-containing sequence>\033\\
```

screen uses a plain DCS `\033P` … `\033\\` and has a length limit — `go-osc52` splits long payloads and rejoins the chunks with `"\x1b\\\x1bP"` (i.e. close the DCS and immediately open another). It is gated: `allow-passthrough` was added in tmux 3.3 (2022) defaulting to **off**, with a third value `all` (works in invisible panes) added in 3.4 (2024-02-13). The FAQ's warning matters: *"Because tmux isn't aware of any changes made to the terminal state by the passthrough escape sequence, it is possible for it to undo them."* Passthrough is for fire-and-forget writes (OSC 52 clipboard, iTerm2 sequences), not for modes tmux also manages.

**`TERM` is rewritten inside tmux** — it must be `screen`, `tmux`, or `tmux-256color`, never the outer terminal's value. Setting `default-terminal "xterm-ghostty"` to fool capability sniffing is a common and broken workaround; it makes tmux advertise capabilities it does not implement.

**What commonly breaks, and the state in tmux (CHANGES as of 3.8 dev, 2026-07):**

| Feature | State |
|---|---|
| OSC 52 clipboard | Works with `set -g set-clipboard on`; three-state option since 2.5. Reads are usually blocked. |
| Kitty keyboard protocol | **Not implemented.** Partial CSI-u forwarding via `set -s extended-keys on`, `set -as terminal-features 'xterm*:extkeys'`, `set -s extended-keys-format csi-u`. No push/pop/query. |
| Synchronized output (2026) | Added in tmux **3.7** (2026-06-26). Absent in 3.6 and earlier. |
| Light/dark reporting (2031) | Added in tmux **3.6** (2025-11-26); tmux guesses from background colour when the outer terminal can't answer. |
| Grapheme clustering (2027) | Not implemented. |
| Sixel | tmux 3.4+ with sixel support compiled in; not universal. |
| Scroll regions | Per-pane; a DECSTBM-based scrollback strategy behaves differently inside tmux than outside. |

Nested multiplexers (tmux inside tmux, or tmux inside screen inside ssh) multiply every layer of filtering. Detect with `$TMUX` / `$STY` and prefer degrading to a mode with no queries at all over guessing.

zellij has its own version of the problem: zellij-org/zellij#3590 — it caches the OSC 10/11 reply and never invalidates it, so a theme switch leaves every client reading a stale background colour until `~/.cache/zellij/` is deleted.

---

## 6. Never hardcode a contrast assumption (L82, L44)

**Do not emit a fixed dim grey, or any colour chosen against an assumed background.** Use the terminal's default foreground with an attribute (`SGR 2` faint), or a colour you selected after detecting the background — and default to *readable* when detection fails.

**Why.** This is the most-filed TUI bug there is. A `#666666` "secondary" label is invisible on a dark theme *and* on a light one at the extremes, and the user cannot fix it from their side. vim's own default made this concrete: it falls back to `background=light` when OSC 11 detection fails, which *"almost always incorrectly detects light background for terminals with black background color"* (vim/vim#13933).

**Detection, best to worst:**

1. **Mode 2031 / `CSI ? 996 n`.** Reply is `CSI ? 997 ; 1 n` (dark) or `CSI ? 997 ; 2 n` (light). `CSI ? 2031 h` subscribes to *unsolicited* notifications, so you also get theme changes at runtime. Contour 0.4.0+, Ghostty 1.0+, kitty 0.38.1+, VTE 0.82.0+, tmux 3.6+, zellij 0.44.2+. This is the mechanism to prefer in 2026 — it answers the actual question (light or dark) rather than making you infer it.
2. **OSC 11.** Query `ESC ] 11 ; ? BEL`; reply `ESC ] 11 ; rgb:RRRR/GGGG/BBBB ESC \`. OSC 10 is the same for foreground. Convert and threshold — `termbg` uses YCbCr with `Y > 0.5 → light`.
3. **`COLORFGBG`.** Format `fg;bg` (e.g. `15;0`). Set by rxvt and Konsole; GNOME Terminal declined to (bugzilla 733423). Stale after a theme change and absent almost everywhere else. Last resort only.

**The two failure modes that bite:**

**Some terminals never answer.** Send a query that *every* terminal answers as a sentinel, and stop reading when it arrives. lipgloss does exactly this (`terminal.go:queryBackgroundColor`) — it writes `RequestBackgroundColor + RequestPrimaryDeviceAttributes` in one go and returns as soon as it sees the DA1 reply:

```go
case ansi.HasCsiPrefix(seq):
    switch pa.Command() {
    case ansi.Command('?', 0, 'c'): // DA1
        return false               // stop reading; no OSC 11 arrived -> unsupported
    }
```

with `defaultQueryTimeout = time.Second * 2` as a backstop and a cancellable reader. Apply the same pattern to every capability query you make.

**The reply arrives as ordinary input, and if you don't consume it, it lands in the shell.** microsoft/terminal#19904 (open): CLIs query OSC 11 and *"fail to consume the response from the terminal"*, so `rgb:1e1e/1e1e/1e1e` characters appear in the user's prompt after the tool exits — reported against Windows Terminal and Warp. This means: query only while you own the tty and are in raw mode, drain until your sentinel, and `tcflush(TCIFLUSH)` on teardown.

Also: an OSC 11 reply can interleave with a keystroke the user typed while you were waiting. Parse the input stream properly (a real escape-sequence parser, not a regex over a buffer) so a keypress mid-reply doesn't corrupt both.

**Design fallback.** When detection fails, use the terminal's own default foreground and background — `SGR 39` / `SGR 49` — and express hierarchy with faint/bold/reverse rather than absolute colours. That is correct on every background by construction. Ship a `--theme dark|light|auto` override, because detection will be wrong for someone.

---

## 7. Windows: mostly solved, with three real remainders (L47)

Since ConPTY (Windows 10 1809 / 10.0.17763, Oct 2018) Windows speaks VT like a Unix pty, and modern cross-platform TUI stacks target it directly. Helix's move from crossterm to termina (helix#13307) deleted its Windows Console API code entirely by requiring 10.0.17763+, and gained OSC 52 and bracketed paste on Windows in the process. **If you support 10.0.17763+, most of the historical Windows chapter no longer applies.** What remains:

**1. You must still turn VT on.** `ENABLE_VIRTUAL_TERMINAL_PROCESSING` (0x0004) on the output handle, and `ENABLE_VIRTUAL_TERMINAL_INPUT` (0x0200) on the input handle if you want VT-encoded key input:

```c
GetConsoleMode(hOut, &dwMode);
SetConsoleMode(hOut, dwMode | ENABLE_VIRTUAL_TERMINAL_PROCESSING);
```

It is not on by default, and `SetConsoleMode` returns `ERROR_INVALID_PARAMETER` on down-level systems. Save the original mode and restore it on exit — same rule as termios. In the same breath, set the output code page: `SetConsoleOutputCP(CP_UTF8)` (and `SetConsoleCP(CP_UTF8)` for input). The console's default is still the legacy OEM code page (437/850 in the US/Western Europe), and without this every non-ASCII byte you write renders as mojibake no matter how correct your width arithmetic is. Save and restore the previous code pages too — it is process-global console state, exactly like a mode. Note crossterm's fallback for environments where the WinAPI call fails but VT works anyway (Git Bash / MSYS): `enable_vt_processing().is_ok() || TERM is set and != "dumb"` (`src/ansi_support.rs`).

**2. Key encoding differs.** ConPTY's VT input loses information the Win32 key event had (key-up events, distinct modifiers, some AltGr combinations). `win32-input-mode` (`CSI ? 9001 h`, microsoft/terminal#6309) restores it by encoding full `KEY_EVENT_RECORD`s, but it is Windows-specific and has known interop breakage (microsoft/terminal#16343, WSL `.exe` interop). Kitty keyboard protocol support landed in Windows Terminal via microsoft/terminal#19817 (merged Feb 2026, targeting v1.25) — before that build, do not expect Enter vs Shift+Enter to be distinguishable there.

**3. No SIGWINCH.** Use in-band resize (mode 2048) where available, or the ConPTY resize path; do not port a signal-based resize loop.

Remaining gaps worth planning around, as of 2026-08: Windows Terminal has no synchronized output (mode 2026), so anti-tearing degrades there; and background-colour querying support varies by build — treat "no reply" as the expected case and fall back per §6. Legacy `conhost` without VT is now rare enough that "detect and degrade to plain output" is a sufficient answer; building a Console-API rendering backend for it is not worth the code.

---

## 8. Everything you didn't type is data, not instructions (L96)

**Sanitize every byte from a non-local source before it reaches the screen.** Model output, tool and subprocess output, file contents you preview, log lines you tail, git branch and commit-message text, HTTP responses, filenames — all of it is *content*. The terminal cannot tell content from commands; that distinction exists only in your renderer, and only if you put it there.

**Why.** Your app has the terminal in raw mode with the alternate screen up, and it is the only thing between an attacker-influenced string and a device whose entire API is in-band. The concrete risks, in rough order of how often they show up:

- **Cursor repositioning.** `CSI H`, `CSI A/B/C/D`, `CSI s`/`CSI u` let a line of text draw over your chrome — a fake prompt, a fake "verified" badge, a fake confirmation dialog above the real one. Your diff engine believes the screen holds what it last drew, so the corruption persists.
- **`OSC 0` / `OSC 2` title rewrite.** Silently retitles the window or tab. Some setups round-trip the title back into the input stream; even where they don't, it is a free forgery of context.
- **`OSC 52` clipboard writes.** Untrusted text can put arbitrary content on the user's clipboard, which is one paste away from a shell. This is why the OSC 52 path in L45 must be *app-controlled*: your yank key writes the clipboard, never a byte sequence that arrived in a stream.
- **`OSC 8` hyperlinks whose target differs from their label.** The visible text says one host and the URI says another; there is no hover preview in a terminal. If you emit links, build them yourself from a parsed URL — don't pass through an OSC 8 you received.
- **`DECSET`/`DECRST` changes that outlive you.** Untrusted text can turn on mouse tracking, turn off autowrap, enter the alternate screen, or leave the keyboard protocol pushed — and none of that is undone by your teardown, because your teardown restores the modes *you* set.
- **Permanent corruption where you own the scrollback (L46).** A committed line can never be un-drawn. In native-scrollback mode a single unfiltered `CSI` in a log line is damage the user carries for the rest of the session.

**Do this.** On the way in, strip or visibly escape all C0 controls except the ones your layout uses (`\t`, `\n`, and `\r` only as part of a normalized newline), all C1 controls (including the 0x80–0x9F single-byte forms — an 8-bit `0x9B` is a CSI introducer), and every complete CSI, OSC, DCS, APC, PM and SOS sequence. Handle the unterminated case: an OSC with no `ST`/`BEL` must not swallow the rest of the buffer, and a truncated sequence at a chunk boundary must not let the next chunk complete it — sanitize on the reassembled string, not per chunk. Render what you removed rather than dropping it silently: `^[` or `␛` in a dim style keeps the text honest and makes an attempted injection visible.

If you want colour passthrough — and for model output you usually do — **allowlist, don't blocklist**: permit `SGR` (`CSI … m`) and nothing else, and within SGR reject parameters you don't render. Reset SGR at the end of every untrusted span so an unclosed attribute can't bleed into your chrome. Everything else, including cursor motion, is dropped.

Don't write the parser. `charmbracelet/x/ansi` has both a real parser and `Strip`; `strip-ansi` is the JS equivalent; Python's `re`-based one-liners circulating in blog posts are not sufficient (they miss C1, DCS and unterminated sequences). Whatever you use, test it against a corpus of hostile strings in a pty harness (L97) and assert on the bytes that reach the terminal, not on the rendered model.

**Sanitize once, at the boundary where the data enters your model** — not at each widget, where one forgotten call is a hole. The only place that emits escape sequences is the renderer, from data structures it owns.

---

## 9. SSH and remote sessions break assumptions you can't see locally (L83, L89, L26)

Everything below is invisible on your workstation and routine for your users. A remote session is not "the same, but slower": the terminfo database, the timing, and the bandwidth are all different, and the multiplexer problems in §5 stack on top.

**Terminfo probably doesn't exist on the far side.** `$TERM` travels over SSH; the terminfo entry does not. Modern values — `xterm-ghostty`, `xterm-kitty`, `wezterm`, `foot`, `contour` — have no entry on a typical server, so ncurses-based programs on the remote host fail with `Error opening terminal: xterm-ghostty` and non-ncurses ones fall back to garbage or plain-ASCII rendering. Fixes, in order of preference:

```sh
infocmp -x | ssh host 'mkdir -p ~/.terminfo && tic -x -'   # once per host; -x keeps extended capabilities
```

or, in `~/.ssh/config`, for hosts you don't control:

```
Host legacy-box
    SetEnv TERM=xterm-256color
```

(`SendEnv TERM` has no effect: `TERM` is carried by the SSH protocol's pty request, not by the environment-passing option, so overriding it means `SetEnv` — OpenSSH 7.8+.) For **your** app the rule is: an unknown terminfo entry is a degrade, not an abort. Fall back to a built-in capability set for `xterm-256color`, or to the plain renderer (§2) — never exit with "unknown terminal type", which is exactly the failure users cannot fix from inside your program.

**Latency turns every timeout into a bug.** L89's escape timeout (full story: `interaction.md` §2) assumes the rest of a sequence arrives immediately after `ESC`; over a link with 150 ms RTT and any jitter, a multi-byte arrow key can straddle the window. Raise it to 150–250 ms or more when you detect a remote session — `$SSH_TTY` / `$SSH_CONNECTION` present — keep the env-var override, and prefer the kitty disambiguate flag so the timeout never runs at all. Reply-based capability queries need a longer deadline for the same reason — a 2-second local backstop is fine, but don't set it to 100 ms.

**Bandwidth is the frame budget.** A full 200×50 repaint with attributes is tens of kilobytes; at 60fps that is megabits per second of terminal traffic to push down a link that may be a phone tether. Cell diffing stops being an optimization and becomes the difference between usable and not, and synchronized output (mode 2026) matters more, because a partial frame that takes 300 ms to complete is visible tearing rather than a flicker. Lower the fps cap on a detected remote session (L26 says make it configurable — this is the case it exists for), and drop animation to zero.

**mosh** survives roaming and hides latency with local echo, which is why users like it, but its terminal emulator is a re-implementation with real gaps: it does not pass through OSC 52, sixel/graphics, or arbitrary DCS, and its mode coverage lags. Treat it as a terminal that answers few queries and drops passthrough — the degrade path you already need for §5.

**Nested tmux over SSH** is the common real environment: your sequences pass through the remote tmux, the ssh channel, and possibly a local tmux, and every layer in §5's table filters independently. `$TMUX` only tells you about the innermost one. Prefer a query-free degraded mode over guessing which layer ate the reply.
