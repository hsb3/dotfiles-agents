# The laws, indexed

The citable index. Use in review: "this violates L41." Each law is an instruction followed by the failure it prevents. Gaps in the numbering are retired laws folded into a neighbour; numbers are never reused.

**Scope tags:** untagged = any full-screen TUI · `[net]` only if content arrives incrementally over a network · `[new]` greenfield only, see `retrofit.md` for the brownfield form.

---

## Boundaries — L1–L10

**L1** **State that outlives a keystroke lives in the store; state that dies with the frame lives in the widget that owns it.** Message list, run status, connection status → store. Cursor offset, scroll position, focus ring, is-this-popup-open → the widget. Test: if a second widget must agree on it, or it must survive a resize or reconnect, it belongs in the store. The rule this protects: **never read back from a widget to make a domain decision** (`if textarea.value.startsWith("/")`). Widgets emit events; nothing queries them. A widget you can query is a second source of truth, and it will disagree with the first under load.

**L3** **If the only way to test it is to launch a terminal, the boundary is in the wrong place.** Parsing, state transitions, wrapping, and event normalization are all pure functions and belong behind a seam you can call from a unit test. What legitimately needs a terminal: capability probes, escape-sequence emission, and end-to-end snapshots (L63).

**L4** `[new]` **Name your layers before the first widget, and write down which direction dependencies flow.** For a local app that is often three: source-of-truth → view-model → widgets. For a network client it is closer to nine (`streaming.md`). The count matters less than the arrow. Brownfield: you cannot do this retroactively — find a seam instead (`retrofit.md` §5).

**L5** **Enforce the layer boundary mechanically, and have the failure message name the sanctioned escape hatch.** A rule nobody checks decays in a month. Codex's CI script checks both the manifest *and* every import line, then prints where the code should go instead. Brownfield: use a ratchet, not a gate (`retrofit.md` §6) — a gate that fails on day one gets deleted.

**L6** **When you can't remove a violation, quarantine it in one named module whose name appears at every call site.** `legacy_core::config::Config` is legible in a diff with no tooling, so the violation count is a `grep` and it only goes down. Full pattern in `retrofit.md` §6.

**L7** **If a machine-readable schema exists, generate the client from it and check the regeneration in CI.** Drift becomes a build failure instead of a runtime bug. If no schema exists — which is the common case — this law doesn't apply; don't invent one to satisfy it. Brownfield: never regenerate over a hand-tuned client without diffing first; accumulated fixes live in there.

**L8** `[net]` **Normalize every wire event into one internal enum before it reaches your domain, and give that enum an `Unknown { raw }` variant.** The enum is the seam that makes fixtures, replay, and reducer tests possible; the `Unknown` variant is what makes L59 achievable. Shown as code in `streaming.md`.

**L9** **Watch churn magnetism, not line count.** A file that attracts unrelated changes is the problem; a long file nobody touches is not. Codex names its specific offenders by path and assigns the worst one a *role* ("orchestration only") rather than a size limit. Mechanical file-splitting with no behavior change is a bad trade, especially in brownfield.

**L10** **Export the minimum.** Codex's TUI declares ~105 modules and makes 7 public. Anything public is a boundary you have to maintain.

---

## State — L12–L22

**L12** **Classify every piece of state before you decide where to put it.** Four kinds: server-authoritative (you hold a cache), stream-derived (transient, high-frequency), session/UI (yours entirely), derived/render (a cache of the other three). Full table with the survives-reconnect / survives-restart columns in `streaming.md`. Conflating them is what makes a store both slow and unserializable.

**L13** **Derived state must be reconstructible from nothing.** Ship a clear-caches command and assert the output is unchanged. Scope the assertion honestly — a frame with a spinner or a relative timestamp is not byte-identical, so assert with animations off or diff only the content region.

**L14** **One writer per kind of state.** Two writers is a race, and it presents as "sometimes the wrong item updates" — a bug you will chase in the renderer, where it isn't.

**L15** `[net]` **Reconcile server state; don't patch it hopefully.** Detect a gap by any of: a sequence number that skipped, a resume window that expired, your own overflow counter firing, or a reconnect that returned no replay. On any of them, refetch a snapshot and diff.

**L16** `[net]` **Keep the in-flight item out of the store until it finalizes.** A store dispatch per token costs you the reducer, every subscriber notification, and a repaint. Keep a tail buffer the view reads directly; promote on finalize.

**L18** **Match the store shape to the language, pick one model, and don't mix.** Owned struct plus channels is the Rust/Go default — Codex's TUI has no `Arc<Mutex<AppState>>` anywhere, and its answer to "share state with the stream task" is "send it a message." Reactive graph is the TypeScript/Python default. Shared-and-locked state (`Arc<Mutex<_>>`, arc-swap) is legitimate for small read-mostly values; what you cannot do is run both models over the same state and expect either one's invariants to hold. Brownfield: switching shapes is a rewrite of the upper half — don't, unless you're rewriting anyway.

**L19** **Make the event enum your log format, and strip credentials before serializing it.** A serialized event log turns any bug report into a replay. Unstripped, it turns your bug reports into an exfiltration channel.

**L20** **Key entities by `(namespace, id)`, not by `id`.** Sub-agents, subgraphs, panes and split views collide on bare ids, and the symptom is two sources' output merging into one item. Applies where you have more than one source of entities — multi-agent, subgraph or multi-pane clients; for a single-view local tool it is noise.

**L21** **Give mutable entities a revision counter.** It is your render-cache key (L38) and your change signal. Without it you cannot distinguish "changed" from "replaced with an equal value."

**L22** **Model status as an enum.** Two booleans is four states, three of which you never designed — and `isLoading && isError` will happen.

---

## Streaming and repaint — L24–L37 · all `[net]` except L24–L27, which apply to any live-updating UI

**L24** **Never repaint per event.** Ingest at arrival rate; repaint on a bounded tick. Otherwise your repaint cost is `O(events)` rather than `O(frames)`, and at high event rates the terminal is the bottleneck.

**L25** **Flush immediately when idle, coalesce when busy.** A fixed tick delays the first token of every response — the moment the user is watching hardest. Working loop in `streaming.md`.

**L26** **Cap the repaint rate and make it configurable.** 30–60fps. Calibration table from five projects in `hard-facts.md`.

**L27** **Wrap each repaint in synchronized output where the terminal supports it.** Half-drawn frames read as jank, not speed. Sequences and the support matrix in `hard-facts.md` — note it is *not* implemented in Windows Terminal or gnome-terminal.

**L28** **Classify every event as lossless or best-effort before you size the queue.** Transcript content and completion signals are lossless; progress and telemetry are not. A bounded channel that dropped message deltas under load produced "permanently corrupted or incomplete paragraphs that persist for the rest of the session", because the renderer assembles those deltas incrementally.

**L29** **Never drop silently.** Emit a `Lagged { skipped }` event and surface it. Silent truncation reads as "everything is fine."

**L30** **Bound every queue.** An unbounded channel is a memory leak with extra steps. What happens at the bound is L28 and L29.

**L31** **Determine replace-vs-append from a fixture, don't guess.** Capture consecutive frames for one item: if frame N+1 contains frame N as a prefix, the server is accumulating and you must replace by id. Appending an accumulating stream produces the doubled-text bug, which is the most common visible defect in streaming clients. Detection snippet in `streaming.md`.

**L32** **Deduplicate on reconnect.** Replay windows overlap by design. A bounded LRU of seen event ids is enough.

**L33** **Order by sortable id where the protocol gives you one.** If it doesn't, arrival order is all you have — say so in a comment rather than inventing an ordering.

**L34** **Freeze a prefix; re-render only the tail.** Full re-render per token is `O(n²)` over a message.

**L35** **Commit a prefix only at a boundary your parser confirms, not one you scan for.** In preference order: parser source maps (re-parse from the last committed line, walk tokens in reverse to the last top-level one, commit to its start); re-lex the tail and discard the last two tokens as a safety margin; failing both, commit only at a blank line where no fence, table, list item, or link-reference definition is open. **Never commit at a bare newline** — that is the heuristic that ships code-fence blanking.

**L36** **Re-render the whole item once on finalize.** Unterminated constructs will have lied to you during the stream — oterm's fix was titled "re-render Markdown on `finish_stream` to fix code-fence blanking."

**L37** **Hold back any construct whose layout depends on data you haven't received.** A table's column widths depend on rows that haven't arrived. Codex has a dedicated holdback scanner for exactly this.

---

## Rendering — L38–L41

**L38** **Key the render cache on `(id, revision, width)` and invalidate everything on a width change.** Omitting width is why resize shows stale wrapping.

**L39** **Never lay out every item to draw the visible ones.** Height cache first, virtualization second. Crush: a "compute exact scrollbar geometry" call rendered every item, per frame during a resize drag.

**L41** **Check whether your renderer is thread-safe before calling it from two tasks.** Most markdown and syntax-highlighting renderers hold parser state. The corruption looks like a parser bug and isn't.

---

## The terminal as a device — L42–L48, L71–L83, L96

Full detail and a ten-minute pre-ship checklist in `terminal.md`.

**L42** **Query capabilities; don't infer them from `$TERM`.** A multiplexer rewrites `TERM`, and emulator-name lists are wrong the day a new emulator ships.

**L43** **Ship a kill-switch env var for every protocol you opt into.** These protocols are actively churning; when one breaks on a user's terminal you need them to be able to turn it off without a release.

**L44** **Degrade, don't detect-and-refuse** — but choose the colours you degrade *from*. For content, render truecolor and let the library downsample; losing precision in a syntax-highlighted diff is acceptable. For chrome — borders, status line, selection, focus ring — use the 16 indexed ANSI colours plus default foreground/background, so the user's theme governs. Downsampling a hand-picked truecolor palette silently picks nearest neighbours that were never checked against the user's background, which is the L82 failure arriving by another route.

**L45** **Mouse capture and native text selection conflict; ship all three mitigations.** With mouse tracking on, drag events go to you and the terminal's own selection stops working. (a) Tell the user "hold Shift to select" in the footer or help — the terminal-side override is near-universal: xterm reserves Shift to bypass mouse tracking, and kitty, Ghostty, WezTerm, iTerm2 and Windows Terminal honour it. XTSHIFTESCAPE (`CSI > Ps s`) lets an application claim Shift back — don't. (b) Bind a mouse-mode toggle key; zellij and helix both ship one. (c) Copy via OSC 52 behind an explicit yank key. Unfixed at the framework layer: open since 2021 in Bubble Tea, still open in Ratatui, filed against Codex and Claude Code.

**L46** `[new]` **Decide who owns the scrollback before the first widget: the terminal, or you.** Native scrollback buys real mouse scroll, real selection, and real copy. It costs you a commit queue, a drain policy, holdback logic, and reflow handling, because a committed line can never be un-drawn. Codex switched to it once, lost streaming for three weeks (including a same-day revert), and has paid terminal-specific fixes ever since. Not retrofittable — see `retrofit.md` §8.

**L47** **Your primary test matrix is terminal emulators; your secondary one is operating systems.** Emulators is where most bugs are, but Windows conpty, key encoding, and the absence of SIGWINCH are real (L71–L83, `terminal.md` §7).

**L48** **All logging goes to a file.** One stray print corrupts the screen — and if you own the scrollback (L46), corrupts it permanently. Enforce it: Codex uses `#![deny(clippy::print_stdout)]`.

**L71** **Install terminal teardown before you set the first mode.** Make it idempotent, reentrant, and callable from a panic hook. Leaving a user's shell in raw mode with the cursor hidden is the worst thing a TUI can do, and it cannot be fixed from inside your program.

**L72** **Restore on `SIGINT`, `SIGTERM` and `SIGHUP`.** Convert the signal into a quit message so exactly one teardown path runs.

**L73** **Treat Ctrl-Z as an exit path — starting with the fact that in raw mode it isn't a signal at all.** Raw mode clears `ISIG` (`cfmakeraw` does this), so Ctrl-Z never generates `SIGTSTP`; you receive byte `0x1A` in the input stream. Either keep `ISIG` enabled, or bind `0x1A` and raise `SIGTSTP` yourself — Bubble Tea does the latter. Only then does the rest run: restore, then stop the process group; on `SIGCONT`, re-claim the terminal with retries and force a full repaint. This is the restoration path people forget, and the user lands in a broken shell.

**L74** **Print crash output with `\r\n`.** You are writing it while raw mode may still be on, and `\n` alone gives you a staircase.

**L75** **Restore the terminal first in the panic hook, then chain to the previous hook.** Restoring after the backtrace prints means the backtrace is unreadable.

**L76** **`isatty` selects a different renderer, not a dimmer one.** Honour `NO_COLOR`, `TERM=dumb`, and `CLICOLOR_FORCE` in that precedence. Users pipe your output into `grep` and run it in CI on day one.

**L77** **Measure text in grapheme clusters** — never in bytes, codepoints, or per-codepoint `wcwidth`. This is what actually destroys box-drawing alignment and truncation.

**L78** **Never put fixed-width chrome around user-supplied non-ASCII text; re-measure per terminal instead.** Enable width-reporting protocols where offered, and let the box grow to what you measured. *Terminals disagree about the width of the same emoji by up to four cells, so any border you sized from your own `wcwidth` is misaligned on someone else's emulator.*

**L79** **`SIGWINCH` is a hint to re-measure, never a measurement.** Re-query the size on the main loop and throttle repaints to 50–100ms on the trailing edge, or a window drag becomes a resize storm.

**L80** **Pair every capability query with a sentinel the terminal always answers, plus a timeout.** Some terminals never reply. An unanswered query must not become a permanent downgrade.

**L81** **Consume every query reply before exiting**, or it lands in the user's shell prompt as garbage.

**L82** **Never hardcode a colour chosen against an assumed background.** Fall back to default foreground/background plus faint or bold, and ship a theme override. A dim grey invisible on light backgrounds is among the most common TUI bug reports.

**L83** **Assume a multiplexer sits between you and the terminal.** It rewrites `TERM`, silently drops sequences it can't parse, and gates passthrough behind an option that is off by default — which means capability *querying* is not automatically safer than sniffing.

**L96** **Treat every byte from a non-local source as data, not terminal instructions.** Strip or visibly escape C0/C1 controls and all CSI/OSC/DCS sequences from model output, tool output, file contents, log lines and VCS metadata before they reach the renderer; allowlist SGR only if you want colour passthrough. *An agent transcript is an injection vector: an ESC in model output can reposition the cursor, rewrite the window title, write the clipboard via OSC 52, point an OSC 8 link somewhere other than its label, and — under native scrollback (L46) — corrupt permanently.* Sanitizer shape and the sequence classes to strip are in `terminal.md` §8.

---

## Input and interaction — L49–L54, L84–L94

Full detail in `interaction.md`.

**L84** `[new]` **Decide full-screen versus inline before the first widget, and make full-screen justify itself.** If it's close, ship both behind one flag; both major agent CLIs ship non-fullscreen as first-class. A non-fullscreen CLI is exempt from nearly every hard problem in this skill — no alternate screen, no scroll regions, no mouse-versus-selection conflict (L45), native scrollback and copy for free, and pipes just work. Decision aid in `interaction.md` §0.

**L49** **Don't write a text area, and don't adopt one blind.** Test the candidate first: multi-line editing with soft wrap that survives resize; undo/redo grouped per word; bracketed paste arriving as one edit; grapheme-cluster cursor movement and double-width handling; history that preserves the in-progress draft on arrow-up; Enter versus Shift+Enter with a non-kitty fallback. Every item is a rewrite to retrofit. Fails two or more → write your own and plan weeks. Codex hand-wrote one; Gemini CLI's is 62KB of source against 162KB of tests.

**L50** **Distinguish a paste burst from fast typing.** Users paste multi-line text and expect one edit, not N keystrokes. Enable bracketed paste and use a timing threshold as the fallback.

**L51** **Enter versus Shift+Enter needs an extended-key protocol — kitty's, or xterm's modifyOtherKeys/CSI-u.** Query kitty's disambiguate flag first; fall back to modifyOtherKeys mode 2 (`CSI > 4 ; 2 m` on, `CSI > 4 ; 0 m` off), which produces the same `CSI 13;2u` encoding and which tmux forwards when its extended-keys setting is `csi-u`. Note the asymmetry: kitty's protocol is push/pop and queryable, modifyOtherKeys is set/reset with no query — so you set it blind and must reset it on teardown. Ship a fallback binding for terminals with neither, because there the two keys are indistinguishable.

**L52** **Bindings are discoverable in context, not on a help screen.** One key shows every action valid *right now*, with the invalid ones shown greyed and explained. lazygit's is the benchmark.

**L53** **Generate keybinding and settings docs from the keymap and schema.** Hand-written ones diverge within a month.

**L54** **Never lose a draft.** Persist composer contents across restarts. This is a five-line fix and the bug it prevents is the one users remember.

**L86** **Write the key-routing order down once: escape hatches → modal stack → focus → ancestors → globals.** One place decides. Two places deciding is how a key fires twice.

**L87** **Give child components a boolean-returning "consumed" guard, not a full nested model.** The parent keeps control of ordering. It cannot be done half-way: as long as any child owns part of the routing, the parent can't decide the order.

**L88** **Never bind an unmodified printable key globally.** Text inputs legitimately own them, and the bug is "my keybinding works everywhere except where I'm typing."

**L89** **Query the kitty disambiguate flag; fall back to an Escape timeout of 50–100ms, env-overridable, and expect to raise it over SSH.** Esc is both "cancel" and the prefix byte of every escape sequence. Shipped values, the protocol, and what breaks: `interaction.md` §2.

**L90** **Bind `alt+esc` alongside `esc` everywhere.** `ESC ESC` arrives as Alt+Escape, and the second press does nothing.

**L91** **Nothing blocks the UI thread: paint the chrome before you have the data, do no IO or expensive work in the event handler, and have the task send a message back rather than mutate state.** Time-to-first-frame is what users judge, and an interrupt key that stops working during output is worse than no interrupt key. Every blocking call moves off the UI path on day one, not as an optimization later.

**L92** **Idle frames should be zero.** Instrument frame count and phase timings before you profile — the time is almost always in layout, not draw, and an animation you forgot is the usual culprit.

**L93** **Ship a bug-report command as a feature, not a wiki page.** Capture the log ring buffer and the terminal environment; gate any attachment on consent.

**L94** **Detect binding conflicts in a test.** No framework does it for you, and the collision surfaces as "that key stopped working" months later.

---

## Failure — L56–L59 · `[net]`

**L56** **Work lifecycle and connection lifecycle are two state machines. Enumerate the connection states and make each renderable before you write the reader loop.** `connecting → live → degraded(attempt n, next in Ns) → resuming(from id) → resyncing → dead(cause)`, tracked separately from whether the work is still running. For each connection state, define three things: what the status line says, whether input is accepted, and what the interrupt key does. Most servers default to continue-on-disconnect, so losing the connection tells you nothing about the work — "the stream dropped but the run is still going server-side" is the most common real state, and a boolean expresses none of it.

**L57** **If resumption is opt-in, assert on the resume token's presence in a test.** Its absence is the failure signal, and it is silent — you get no ids, no error, and no way to reconnect.

**L58** **Errors arrive after a 200.** Handle "success status, failed stream."

**L59** **Unknown payloads render; they don't crash.** Leave a raw-data escape path the user can reach. The `Unknown { raw }` variant from L8 is what makes this cheap.

---

## Testing — L61–L64, L97

**L61** **Record real sessions to fixtures early and replay them forever.** Highest-return hour in the project. Brownfield technique differs — tee the live process rather than instrument it (`retrofit.md`).

**L62** **Assert on your render model where you can, on bytes where you must.** Model assertions survive a restyle; byte assertions catch what the model can't see. Use both, deliberately.

**L63** **Snapshot at fixed widths — one narrow (40–60), 80, 120, 200 — plus the degenerate cases: a single column, and a size below your declared minimum.** Resize is where layout dies, and a single-width suite proves nothing. Two of the shrink-related panics in `retrofit.md`'s symptom table are subtractions that go negative when the frame is smaller than the chrome.

**L64** **Prove virtualization against a synthetic large transcript before you have a real one.** The threshold where naive layout stops working is lower than you think.

**L97** **Drive the real binary under a pty in at least one test, and fuzz the input parser.** *Model-level assertions (L62) cannot catch a broken teardown, a hung capability query, or a parser that panics on malformed escape input — and all three ship.* Harnesses: node-pty, pexpect, expectrl, or plain `script -q`; parse the output with pyte, vt10x, or termwiz. Framework-agnostic option if you want no harness dependency at all: `tmux new-session -d`, drive it with `send-keys`, assert on `capture-pane -p`.

---

## Shipping — L66–L69

L68 and L69 are client/transport requirements rather than TUI laws proper; agent-client builders hit both immediately. If you are building a local tool with no server, skip them.

**L66** **Choose the directory by who owns the file, not by what's in it.** *config* — the user writes it, you only read it; write back and you reformat their file and delete their comments. *state* — you write it, losing it is annoying but recoverable (drafts, history, geometry, resume tokens). *cache* — you write it, and `rm -rf` on it mid-run must be harmless. Resolve paths with a library, not hardcoded strings: macOS and Windows do not follow XDG. Test by deleting the cache directory while the app runs — if anything but latency changes, you mislabeled something.

**L67** **Never write a secret into a config file.** Reference an env var or a keychain.

**L68** `[net]` **"No auth" is a valid configuration, not an error.** Local model servers, dev servers, and air-gapped deployments all have none, and treating it as a misconfiguration blocks a legitimate setup.

**L69** `[net]` **Accept free-form header maps.** You cannot enumerate someone else's auth scheme.

