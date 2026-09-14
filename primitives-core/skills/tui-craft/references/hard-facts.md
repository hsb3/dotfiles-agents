# Hard facts

Concrete values behind the laws. Verified 2026-08-01. Look here when a law says "do X" and you need the exact X.

## Escape sequences

| Purpose | Sequence |
|---|---|
| Synchronized output begin / end (L27) | `CSI ? 2026 h` / `CSI ? 2026 l` |
| Query synchronized output support | `CSI ? 2026 $ p` → DECRPM reply (below) |
| Alternate screen enter / leave (L46) | `CSI ? 1049 h` / `CSI ? 1049 l` — saves cursor and switches buffer in one sequence; leaving restores the primary buffer and the user's scrollback |
| Bracketed paste on / off (L50) | `CSI ? 2004 h` / `CSI ? 2004 l`; pasted text wrapped in `ESC[200~` … `ESC[201~` |
| Mouse tracking (L45) | `CSI ? 1000 h` press/release · `1002` cell motion · `1003` all motion · **`1006` SGR coordinates — required past 223 columns** |
| Clipboard write, works over SSH (L45) | `ESC ] 52 ; c ; <base64> BEL` |
| Kitty keyboard: query / push / pop (L51) | `CSI ? u` → `CSI ? flags u` (no reply = unsupported) · `CSI > flags u` · `CSI < u` |
| Kitty flags | `1` disambiguate (**required for Enter vs Shift+Enter**) · `2` event types · `4` alternate keys · `8` all keys as escapes · `16` associated text |
| modifyOtherKeys on / off (L51) | `CSI > 4 ; 2 m` / `CSI > 4 ; 0 m` — the xterm predecessor to the kitty protocol; mode `2` encodes *all* modified keys |
| Scroll region set / reset (L46) | `ESC [ {top} ; {bottom} r` / `ESC [ r` |
| Reverse index — scroll region down one (L46) | `ESC M` |
| Autowrap on / off | `CSI ? 7 h` / `CSI ? 7 l` — off is what stops a write to the last cell of the last row from scrolling the screen; **restore it to `h` on teardown**, DECSTR also clears it |
| Cursor shape, DECSCUSR | `CSI Ps SP q` (note the literal space before `q`): `0`/`1` blinking block · `2` steady block · `3` blinking underline · `4` steady underline · `5` blinking bar · `6` steady bar |
| Cursor position report, DSR | `CSI 6 n` → `CSI {row} ; {col} R`, 1-based. Ground truth for display width (L77) at the cost of a round trip; needs raw mode and a timeout (L80) |
| Focus reporting on / off | `CSI ? 1004 h` / `CSI ? 1004 l`; focus in = `CSI I`, focus out = `CSI O`. Use focus-out to stop animations and drop to zero idle frames (L92) |
| Hyperlink, OSC 8 | `ESC ] 8 ; ; {URI} ST {text} ESC ] 8 ; ; ST` — the empty middle field is the (optional) params list; `ST` is `ESC \`. Unsupported terminals show the text and drop the link |
| Palette query / reset, OSC 4 / OSC 104 | `ESC ] 4 ; {index} ; ? ST` → `ESC ] 4 ; {index} ; rgb:RRRR/GGGG/BBBB ST` · `ESC ] 104 ST` resets the whole palette, `ESC ] 104 ; {index} ST` one entry |

**DECRPM reply format** (for any `CSI ? {mode} $ p` query) is `CSI ? {mode} ; {value} $ y`, e.g. `CSI ? 2026 ; 2 $ y`. The value is what matters:

| Value | Meaning | Use the feature? |
|---|---|---|
| `0` | mode not recognized | **No** |
| `1` | set | Yes |
| `2` | reset | Yes — recognized, currently off |
| `3` | permanently set | Yes, but you cannot turn it off |
| `4` | permanently reset | **No** |

So the test is "reply is 1, 2 or 3", not "reply is non-zero" — `4` means the terminal knows the mode and will never honour it. No reply at all is also a no (L80: pair the query with a sentinel).

**Synchronized output is not universal** (updated 2026-08-01). Implemented: Contour, mintty, foot, WezTerm, iTerm2, kitty, notcurses, Jexer, **Alacritty (0.13.0+)**, **Ghostty (1.0+)**, tmux 3.7+. **Windows Terminal: proof-of-concept only in the tracker, not shipped. VTE/gnome-terminal: not implemented** — still one of the largest installed bases. Query, then degrade (L42, L44).

**modifyOtherKeys is the fallback where kitty's protocol is absent.** With `CSI > 4 ; 2 m` set, a terminal that supports it reports modified keys in CSI-u form — Shift+Enter arrives as `CSI 13 ; 2 u` (13 = CR, 2 = shift), the same encoding family kitty uses, so one parser handles both. tmux forwards it with `set -s extended-keys on` plus `set -s extended-keys-format csi-u`; without the format option tmux emits the older `CSI 27 ; {mod} ; {key} ~` form. Turn it off on teardown like any other mode.

**Truecolor detection has no spec.** Convention is `COLORTERM ∈ {truecolor, 24bit}` plus terminfo `RGB`/`Tc`. Render in truecolor and let the library downsample (L44).

**OSC 52 is write-reliable, read-blocked.** Most terminals disable clipboard *reads* by default; tmux needs `set -g set-clipboard on`. Design for "copy works, paste-from-query doesn't." The write path must be app-controlled: your yank key emits the sequence, and an OSC 52 arriving inside untrusted content is stripped, never forwarded (L96).

## Repaint budgets in the wild (L24–L26)

| Project | Mechanism |
|---|---|
| OpenCode | 16 ms coalescing queue, then one batched store write. Flushes immediately if idle — this is the L25 pattern. |
| Codex | `FrameRequester` actor coalescing many redraw requests into one broadcast notification, plus a frame rate limiter. |
| Bubble Tea v2 | Renderer on a fixed ticker, `defaultFPS = 60`, `maxFPS = 120`, decoupled from message arrival. |
| OpenTUI | `targetFps` 30 / `maxFps` 60, runtime-assignable; change-driven by default. |
| Textual | `MAX_FPS` / `UPDATE_PERIOD = 1/MAX_FPS`, plus in-widget coalescing in its markdown stream. |

## Stable-prefix markdown, four ways (L34–L35)

| Implementation | Boundary strategy |
|---|---|
| **Textual** (MIT — the one to port) | Keeps `_last_parsed_line`; re-parses only `splitlines(keepends=True)[cursor:]`; walks tokens **in reverse** for the last top-level one with a source `map`; advances cursor to `token.map[0]`. Patches the last block in place, mounts only new ones. Most principled — the parser's own source map picks the boundary. |
| **OpenTUI** (MIT) | Byte-prefix scan over `token.raw` with `startsWith`, then discards the last 2 matched tokens as a safety margin ("`# Hello`" may become "`# Hello World`"), re-lexes the suffix. Coarser, but exposes a stable-block count for committing finished blocks out of the live tree. |
| **Codex** (Apache-2.0) | Newline-gated collection into a FIFO of committed lines, drained by a hysteresis-based chunking policy, with a table holdback scanner. Elaborate because committed lines go to scrollback and can never be un-drawn. |
| **Crush** (FSL — read, don't port) | ~600 lines of CommonMark boundary analysis: fence parity, HTML block openers, link reference definitions, loose-list continuation, table pipes, setext underlines. |

## Framework gotchas

- **Textual** — has streaming markdown and in-app selection; **no viewport culling**, so build your own height cache (L39). Snapshot plugin last released 2025-01; verify before building a suite on it. Packaging beyond pipx is undocumented.
- **OpenTUI** — has streaming markdown, culling (render-only; per-frame layout is still O(total children)), selection, and an in-core test renderer. Node needs 26.4.0 + `--experimental-ffi`, so in practice you choose Bun. Maintainers' roadmap says v1.0 means rewriting the renderable tree in native code.
- **Bubble Tea v2** — best renderer (cell diffing + synchronized output with runtime detection) and best distribution. **No incremental markdown anywhere in the ecosystem**; budget for L34–L37 yourself. Its text area lacks undo/redo and history. Test harness lives under an `exp/` path.
- **Ratatui** — immediate mode: you own the event loop, focus, scroll state and wrap cache. Best governance and best raw perf. Scroll and wrap disagree (scroll operates on pre-wrap lines) — expect to wrap yourself and render pre-wrapped lines.
- **Ink** — no mouse, no scrollable regions, full-tree redraw, `<Static>` is append-only and immutable so it fights token streaming. Both flagship adopters forked it. Not suitable for a full-screen transcript.
- **prompt_toolkit** — anything printed to stdout while a prompt is active corrupts the display; wrap those writes in `patch_stdout()` (or route logging to a file, L48). Full-screen `Application` runs its own asyncio loop, so any blocking call in a handler freezes the UI — use `run_in_executor` or a background task and send the result back (L91).
- **tview** — all UI mutation from a goroutine must go through `Application.QueueUpdateDraw`; calling `Draw` (or touching primitive state) directly from a goroutine is a data race, and it is the single most-reported tview bug. Built on tcell, so it inherits tcell's terminal handling.

## Streaming-client contract (if the server is HTTP + SSE)

Generic, but calibrated against LangGraph-style servers.

- **Frames may use CRLF.** Split on `\n`, `\r`, and `\r\n`.
- **Comment frames are keepalives.** A `: heartbeat` every few seconds is normal; a naive line splitter chokes on it. If frames arrive in bursts matching the heartbeat interval, a proxy is buffering — send `Cache-Control: no-store` and hard-fail if `Content-Type` isn't `text/event-stream`.
- **Read timeout must be long or disabled.** A default client timeout silently kills long streams. This is the classic bug in every language.
- **Reconnect via the response's `Location` header**, switching to `GET` and dropping the body.
- **Resumption (opt-in, silent when absent), the post-window resync, and subscribe-first ordering:** full tellings in `streaming.md` § Reconnect and resync (L57, L15).
- **Namespaced events** often mangle the event name (`values|researcher|worker_a`). Split on the first delimiter and keep the namespace as part of entity identity (L20).
