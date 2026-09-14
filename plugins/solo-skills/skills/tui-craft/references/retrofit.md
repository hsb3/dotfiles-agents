# Retrofit

For a TUI you did not write. Start at §1 if you have a bug report, §2 if you have a codebase and no specific complaint.

Law numbers (`L14`, `L38`) refer to `references/laws.md`. Most of them are written for a project that hasn't started. This file is how they land in one that has.

---

## 1. Diagnose before you touch anything

**The framing, because it decides where you look:** in essentially every application-level TUI bug below, the *reported* symptom is cosmetic, the *root cause* is a layer boundary — where wrapping happens, where the event stream is allowed to drop, where width is decided, who owns the history — and **none of them are fixable inside the widget that visibly misbehaves.** If you are editing the widget in the screenshot, you are in the wrong file.

| Symptom as reported | Root cause | Fix | Laws | Evidence |
|---|---|---|---|---|
| "Can't select or copy text from the chat history" | History rendered inside a framework widget, so the emulator never sees the text | Append-only log written to real terminal scrollback — see §8 before you do this | L45, L46 | codex#1672 |
| "Corruption when streaming large output" — permanently mangled paragraphs | Bounded mpsc dropped events via `try_send`. Only `TurnCompleted` was must-deliver; `AgentMessageDelta`/`ItemCompleted` were droppable — but markdown renders incrementally from those deltas | Widen the must-deliver class; blocking `send().await` for transcript-critical events | L28, L29, L30 | codex#15759: *"Dropping any of them produces permanently corrupted or incomplete paragraphs that persist for the rest of the session."* |
| "Resize corrupts the screen" / stale wrapping artifacts | Transcript wrapped for viewport width *at write time* and written to scrollback. Scrollback is immutable, so it stays shaped for the old width forever | If you don't own native scrollback, this is usually L38 alone — add width to the render-cache key. The rebuild-scrollback machinery below applies only to apps that write real terminal scrollback (L46). Otherwise: retain *source* lines, rebuild scrollback on width change, debounce, force reflow after streaming, cap replay rows per terminal (VS Code 1000, Windows Terminal 9001, WezTerm 3500, Alacritty 10000) | L38, L46, L63 | codex#18575, `resize_reflow_cap.rs` |
| Logo appears/disappears while arrowing a list; app "jumps" | Off-by-one in available-height computation; footer stays rendered when height is marginal, so layout oscillates. Only visible on short terminals | Height computation fix | L39, L63 | gemini-cli#3653 |
| **~37 separate issues containing "flicker"**, plus "jumpy terminal", "CLI stuck in middle of terminal", "scrolls through the whole chat on every letter typed", resize corruption | **One structural cause:** no `overflow: scroll` in the renderer, so large content is re-laid-out and re-emitted in full instead of clipped to a viewport | Land `overflow: scroll` in the framework; retire the interim truncation component | L24, L34, L39 | gemini-cli#7016 enumerates fourteen issues — 3653, 2428, 2877, 2959, 2646, 2941, 4077, 4075, 3959, 3750, 3920, 4335, 2859, 5072 — as downstream of one fix |
| "Last few characters of a dialog wrap to a new line" — recurring, once per new dialog | Content sized to the dialog's *outer* width. In lipgloss v2, `Width(n)` is the **total** box width; border and padding live inside it | `innerWidth := m.width - t.Dialog.View.GetHorizontalFrameSize()`; use `Padding`, never `Margin` | L63 | crush `internal/ui/AGENTS.md` |
| Text loses its color partway through a styled line | Raw strings concatenated and then wrapped in one style — an inner segment's reset code kills the outer color | Render styled segments individually, concatenate the *results* | — | crush AGENTS.md |
| "Slow / hangs while resizing a long conversation" | `list.TotalHeight` renders **every** item to get exact scrollbar geometry, called per frame during a resize drag. Separately, the chroma style and lexer are rebuilt every render | Memoize style + lexer; bounded `list.Overflows` for the "does it overflow" question; suppress the scrollbar mid-drag; prewarm on settle | L38, L39 | crush AGENTS.md |
| Code fences blank out when a streamed message finishes | Incrementally-rendered markdown is never re-parsed at completion | Re-render the whole item on `finish_stream` | L36 | oterm 0.17.2 |
| Duplicate content in the transcript | Duplicate renderable IDs in the reconciler | ID uniqueness | L20, L31 | opencode#32110 |
| Continuous redraw / CPU burn at idle | Animated logo redrawing every frame plus mouse-driven visual effects | Static branding | L24, L26 | opencode#33633 |
| Raw output below the composer, redraw artifacts, only under Zellij | Zellij doesn't constrain soft-wrapped continuation rows to the app's scroll region, so the scroll-region trick leaks | Multiplexer-specific raw path: append through the terminal, reserve blank rows for the next viewport draw | L42, L47 | codex `insert_history.rs`, codex#16578, codex#22214, codex#24593 |
| URLs not clickable; clicking copies a broken URL | Hard-wrapping inserted newlines mid-URL, breaking the emulator's link matcher | Three-path wrapper: URL-only lines kept intact, mixed lines adaptively wrapped so URL tokens stay unsplit, plain lines wrapped normally | L46 | codex#12067, codex#21760, codex#24472 |
| Cursor jumps after history is written | Writing to scrollback perturbs the backend's cached cursor position | Raw `MoveTo`, not the backend's `set_cursor_position` | L46 | codex `insert_history.rs`: *"insert_history_lines should be cursor-position-neutral"* |
| Panic, "index outside of buffer", on shrinking the terminal | Widgets computed areas without clamping to the now-smaller buffer | Clamp every render area to terminal size | L63 | ratatui#1379, codex#1758 |
| Screen flashes black on startup under a light theme | `push_screen` inside `on_mount()` runs before the theme is applied | Defer: `call_later(self.push_screen, …)` | L4 | Textual#4988 |
| Widget flickers at a size it immediately leaves | `height: auto` widget measured and rendered at an intermediate size before layout settles | Defer sizing until layout settles — don't paint the intermediate measurement | L39 | Textual#5841 |
| Infinite resize loop, scrollbars strobing | A widget with `margin` inside a scrollable container changes content size → changes scrollbar visibility → changes available width → changes content size | Break the layout→scrollbar feedback cycle by reserving scrollbar space up front, so scrollbar visibility stops perturbing available width | L39 | Textual#4141 |

---

## 2. Audit an unfamiliar TUI in ten minutes

Set `UI=` to the UI package/crate root first. Every command is runnable as written. Read the "a hit means" column before believing a count.

**Logging into the screen (L48).**
```bash
rg -n --glob '!**/*test*' -e 'console\.(log|error|warn)\(' -e '\bprintln!\(' -e '\beprintln!\(' -e '\bfmt\.Print' -e '^\s*print\(' "$UI"
```
A hit means the next stray call corrupts a frame — and with native scrollback (L46) corrupts it permanently, because a committed line cannot be un-drawn. High false-positive rate: non-fullscreen subcommands, `--version`, and the crash handler legitimately print. Confirm each hit is outside the render loop's lifetime, not just outside the render loop.

**Capability inference (L42).**
```bash
rg -n -e '\bTERM\b\s*==' -e 'TERM_PROGRAM' -e 'env::var\("TERM"' -e 'getenv\("TERM"' -e 'os\.Getenv\("TERM"' -e "environ\[.TERM" "$UI"
```
Any hit is a hardcoded emulator list waiting to be wrong. Multiplexers rewrite `$TERM` and lie about capabilities, which is why the codex Zellij row above exists. Query, don't infer.

**Unbounded or silently-dropping queues (L29, L30).**
```bash
rg -n -e 'unbounded_channel\(\)' -e 'mpsc::unbounded' -e 'channel::unbounded' -e 'try_send\(' -e '\.send\([^)]*\)\.ok\(\)' -e 'make\(chan [^,)]*\)'
```
`unbounded*` is a memory leak with extra steps. `try_send` / `.ok()` is the codex#15759 bug verbatim: the drop is invisible and the corruption is permanent. Go's `make(chan T)` without a capacity is *unbuffered*, not unbounded — different failure (a stalled producer), still worth reading. If you find a drop path, check immediately whether anything emits a `Lagged { skipped }`-style event; silent truncation reads to the user as "everything is fine."

**Repaint driven by events (L24).**
```bash
rg -n -c -e 'terminal\.draw\(' -e 'screen\.refresh\(\)' -e 'requestRender\(' -e 'forceRender\('
```
One or two call sites means a single draw loop. A dozen means repaint is event-driven and every burst of stream events is a burst of frames. Then check what's *inside* the handler:
```bash
rg -n -U -e '(?s)Update\(msg tea\.Msg\).{0,2500}?(os\.(Open|ReadFile)|http\.|exec\.Command|time\.Sleep)' "$UI"
```
crush's hardest rule: *"Never do IO or expensive work in `Update`; always use a `tea.Cmd`. Never change the model state inside of a command."*

**Bracketed paste (L50).**
```bash
rg -n -e '\?2004' -e 'BracketedPaste' -e 'bracketed_paste' -e 'bracketedPaste' "$UI"
```
Zero hits is only a finding if the framework doesn't do it for you — Textual and Bubble Tea enable it; raw crossterm/tcell/blessed apps do not. Zero hits plus a raw input loop means a pasted 40-line block arrives as 40 keystrokes and probably 40 repaints.

**Cache keys missing width (L38).**
```bash
rg -n -A3 -e '(cache|memo)[A-Za-z_]*\.(get|set|insert|entry)\(' "$UI"
```
Read the key tuple in each hit. A key of `(id)` or `(id, revision)` with no `width` produces stale wrapping the first time the terminal resizes — and the resize row in §1 is that bug at scrollback scale. Also grep the inverse: `rg -n 'fn render\(|func .*Render\(' -A1 "$UI"` and check that anything taking `width` is either uncached or width-keyed.

**Boolean pairs where an enum belongs (L22).**
```bash
rg -n -e '\b(is|has|should)[A-Z][A-Za-z]*\??: *boolean' -e '^\s*(pub )?is_[a-z_]+: *bool' -e '^\s+[A-Z][A-Za-z]* +bool$' "$UI"
```
Group hits by struct. Two booleans about the same subject is four states, of which you designed two. `isLoading` + `isConnected` cannot express "stream dropped but the run is still executing server-side" — the most common real state in a streaming client, and the one users report as a hang.

**UI → engine imports (L5). This is your ratchet baseline, not a bug list.**
```bash
rg -n -c -e 'use +codex_core' -e 'codex_core::' -e "from '\.\./\.\./core" "$UI" | sort -t: -k2 -rn
```
Substitute your engine's name. Sort descending: the top three files are where the boundary actually is, and they are the ones to fix first. Record the total — §6 turns it into a ratchet.

**Raw ANSI handled as bytes.**
```bash
rg -n --glob '!**/ansi/**' -e '\\x1b\[' -e '\\033\[' -e '\\u001b\[' "$UI"
```
crush: *"Use the `charmbracelet/x/ansi` package for any string manipulation that might involve ANSI codes. Do not manipulate ANSI strings at byte level!"* Escape literals outside the one module that owns them means someone is slicing styled strings by index, which is also how width computation goes wrong (`len()` is not display width — CJK, emoji, ZWJ sequences and combining marks all break it).

**Full layout to draw a viewport (L39).**
```bash
rg -n -A6 -e 'TotalHeight|totalHeight|measureAll|contentHeight\(\)' "$UI"
```
If it loops all items, it runs per frame, and resize-drag is a quadratic storm. crush's fix is the shape to copy: a bounded `Overflows()` for the yes/no question, exact geometry computed only when someone actually needs the scrollbar.

**Hand-edited generated client (L7).**
```bash
git log --oneline -20 -- "$(rg -l 'DO NOT EDIT|@generated' "$UI" | head -1)"
```
Commits that aren't "regenerate" mean a regeneration will destroy real fixes. Do not regenerate to prove a point — see the tier-2 note in §3.

---

## 3. Rank fixes by cost and blast radius

### Tier 1 — an afternoon, no architectural change
L21 (revision counters), L29 (surface drops instead of swallowing them), L38 (add `width` to cache keys), L43 (kill-switch env var per protocol you opt into), L48 (route logging to a file), L50 (bracketed paste), L51 (kitty-protocol fallback binding), L54 (persist the draft), L59 (render unknown payloads instead of crashing).

These share a property: each is local, each is independently revertible, and each has an observable pass/fail. Do all of them before touching anything below — they cost a day total and they remove noise that would otherwise be blamed on the architecture.

### Tier 2 — a week, contained blast radius
L24–L27 (repaint scheduling: one loop, bounded tick, immediate flush when idle, synchronized output), L28+L30 (bound the queues and classify events lossless vs best-effort), L34–L37 (stable-prefix rendering and finalize re-render), L39 (height cache then virtualization), L22 (booleans → status enum), L45 (mouse capture vs native selection, plus OSC 52 and a yank key), L61 (retrofit fixtures — record from live traffic, replay in tests), L7 (generated wire types — see Seam B).

Each touches one subsystem and one set of call sites. They are a week because the *tests* are the week, not the change. Do them one at a time and keep `main` shippable; there is no ordering dependency between them except that L28/L30 should precede L24–L27 (no point scheduling repaints of events you're dropping).

**Not on this list, deliberately:** L9 (module size). Mechanical file-splitting with no behavior change burns the entire change budget of a brownfield project and lands zero user-visible improvement. codex's own version of the rule is not a line count — it names *churn magnets* (`tui/src/app.rs`, `chatwidget.rs`, `bottom_pane/mod.rs`) and assigns the worst one a role instead of a size: *"Avoid adding new standalone methods to `chatwidget.rs` unless trivial; keep it focused on orchestration."* Apply it to new code only.

### Tier 3 — effectively a rewrite
L4 (the layer stack), L8 (a normalized event enum, if none exists), L18 (store shape — owned-struct-plus-channels vs reactive graph), L46 (native scrollback vs alternate screen).

**The pain threshold.** All four are worth it only when all of these hold:

1. **A single structural cause provably accounts for a cluster of open issues, and you can list them.** gemini-cli#7016 named fourteen issue numbers as downstream of one missing `overflow: scroll`. If you cannot write that list, you have one bug, not an architecture problem.
2. **The fix cannot be expressed in the current layer at all** — not "is hard," not "is ugly." If a workaround exists that isn't a hack, take the workaround.
3. **You can afford to regress the flagship feature for weeks.** codex#1672 shipped with *"It also disables streaming responses, which we'll do our best to bring back in a later PR."* Streaming took three attempts over three weeks to return.
4. **A parallel path plus a flag is achievable**, so the fork window is days. codex's was 11 (§4). If the two implementations must coexist for a quarter, you will be merging into both for a quarter.

Fewer than four? Not yet.

---

## 4. The migration playbook

`openai/codex` decoupled its TUI from `codex-core` in this order. Follow it.

1. **Build the new transport first and prove it on your simplest consumer, not the TUI.** codex#14005 (2026-03-09) added an in-process app server and wired *`codex exec`* — the headless one — to it. The TUI was the second client, four days later (codex#14512). A headless consumer gives you a failure signal that isn't confounded by rendering.
2. **Boot the existing UI on the new transport with the old paths still live** (codex#14512). No behavior change; you're proving the transport survives the real workload.
3. **Fork the whole UI directory behind a feature flag.** codex#14717: *"This PR replicates the `tui` code directory and creates a temporary parallel `tui_app_server` directory. It also implements a new feature flag `tui_app_server` to select between the two tui implementations."* For a transport or framework swap this beats in-place refactor, because every commit on either side is independently shippable.
4. **Delete the loser fast.** codex#15922 (2026-03-27): *"This part simply deletes the existing `tui` directory and marks the `tui_app_server` feature flag as removed."* Then codex#16104 renamed the survivor back. **The parallel period was 11 days.** A short fork is the whole reason the technique works; a long one doubles your maintenance and you will start merging fixes into both.
5. **Only now draw the boundary, and draw it as a pure no-op.** codex#17399 (2026-04-11), 26 days after the parallel TUI existed and 15 after the old one was deleted, introduced the `legacy_core` quarantine plus the CI check: *"The TUI still depended on `codex-core` directly in a number of places, and we had no enforcement from keeping this problem from getting worse"* — and — *"no functional change in this PR — just changes to import targets."* Import-target-only diffs are reviewable in minutes and hard to revert by accident. Fence what leaked, after the cutover; you cannot know what leaked before it.
6. **Drain by category, not by module, and expect months.** codex went `test_support` → `telemetry` → `windows sandbox` → `exec-policy`: codex#18605/codex#18631 (04-20, the trivial re-exports), codex#26711/codex#27484/codex#27487/codex#27490 (06-09→11), codex#31179 (07-06). Nearly three months after the boundary existed (codex#17399, 04-11) it was still not empty. Categorical draining gives each PR one reviewable theme; "remove legacy_core" gives you a PR nobody can review.

**If users are on the old path,** say so in the product. opencode commit `446510a6`: *"Users who were migrated to the new interface will now see a dismissible notice in Settings explaining the old interface was phased out…"*

---

## 5. Seams — where you can cut without a rewrite

**Seam A — behind a client/transport interface.** `codex-rs/app-server-client/` exports `InProcessAppServerClient` and `RemoteAppServerClient` behind one surface; the same client works in-process, over stdio, over a socket, or over UDS (codex#22414). The only cut that also buys you a second frontend for free — that app server now serves the TUI, `codex exec`, and the desktop app. Right cut when you want the UI runnable without the engine in-process, or a second frontend is plausible. Not free: it turns every event into a queued message, which is exactly where codex#15759's drops came from. Classify events (L28) as part of the same change.

**Seam B — behind a generated wire/event type.** opencode's `packages/protocol` plus `packages/httpapi-codegen`; commit `43e39d7f` is `fix(tui): use generated event union (opencode#34118)`. For a JS/TS codebase this is what to extract first: generate the wire types so protocol drift is a build failure rather than a runtime bug. Right cut when the same shapes are hand-declared in three places and they disagree.

**Seam C — behind a rendering interface (strangler-fig renderer).** crush `internal/ui/AGENTS.md`: *"The UI uses a **hybrid rendering** approach: 1. **Screen-based (Ultraviolet)**: the top-level `UI` model creates a `uv.ScreenBuffer`, and components draw into sub-regions using `uv.NewStyledString(str).Draw(scr, rect)`. 2. **String-based**: sub-components like `list.List` and `completions` render to strings, which are painted onto the screen buffer. 3. **`View()`** creates the screen buffer, calls `Draw()`, then `canvas.Render()` flattens it to a string for Bubble Tea."* The new cell-buffer renderer went in *underneath* the old string renderer, and the adapter is one line:
```go
func (m *Chat) Draw(scr uv.Screen, area uv.Rectangle) {
    uv.NewStyledString(m.list.Render()).Draw(scr, area)
}
```
Components move from `Render(width int) string` to `Draw(scr, area)` one at a time and **both interfaces are documented as legitimate**, so there is no deadline and no half-migrated embarrassment. Right cut when you need cell-level control (clipping, z-order, partial damage) but cannot re-author every component.

**Seam D — extract a headless core, drive multiple renderers.** opencode: `packages/core` + `packages/ui` + `packages/sdk` shared, with `packages/tui` (`@opentui/solid`) and `packages/session-ui` (DOM, `solid-js` + `@kobalte/core`) as two renderers over one reactive graph. crush does the same in Go: `internal/server` + `internal/client` + `internal/proto` + `internal/ui`. Right cut when a web or desktop surface is actually planned — it is a large cut that pays only if the second renderer ships.

**Seam E — collapse the nested-model hierarchy. The anti-seam.** crush abandoned Bubble Tea's own composition model: *"The `UI` model is the **sole Bubble Tea model**. Sub-components (`Chat`, `List`, `Attachments`, `Completions`) do not participate in the standard Elm architecture message loop… **`Chat`** and **`List`** have no `Update` method at all. **`Attachments`** and **`Completions`** have non-standard `Update` signatures (e.g. returning `bool` for 'consumed') that act as guards, not as full Bubble Tea models. **Sidebar** is not its own model: it's a `drawSidebar()` method on `UI`."* Their prescription for new components: expose imperative methods rather than `Update(tea.Msg)`, return `tea.Cmd` when side effects are needed, render via `Render(width)` or `Draw(scr, area)`, and let `UI.Update()` decide when to call in. They accept the cost out loud: a giant `switch msg.(type)` where *"message routing happens, focus and UI state is managed, layout calculations are performed, dialogs are orchestrated."*

**This one cannot be done incrementally, and the reason is categorical:** the message loop is a single dispatch point. As long as *any* child still owns part of the routing, the parent cannot make routing decisions — it doesn't know whether the child consumed the key. There is no state in which half the components are converted and focus behaves correctly. Convert the whole subtree in one change, or don't start.

---

## 6. Quarantine and ratchets

### The quarantine module

```rust
/// Transitional access to core-only embedded app-server types.
///
/// New TUI behavior should prefer the app-server protocol methods. This
/// module exists so clients can remove a direct `codex-core` dependency
/// while legacy startup/config paths are migrated to RPCs.
pub mod legacy_core {
    pub mod config {
        pub use codex_core::config::*;
        pub mod edit { pub use codex_core::config::edit::*; }
    }
}
```

Three properties do the work:

- **It re-exports, it does not wrap.** Zero adapter code, so adopting it is mechanical and the adopting PR reviews as a no-op (codex#17399 again). A wrapper would need behavior review and would never land.
- **The namespace is the label.** Every call site reads `crate::legacy_core::config::Config`. A violation is legible in a plain diff with no tooling, by a reviewer who has never heard of the migration.
- **It is deliberately narrow** — only `config` and `config::edit`. The surface *is* the remaining debt, and it shrinks by deletion, not by refactor.

Same idea, named differently: `codex-rs/tui/src/permission_compat.rs` — *"Compatibility projections from the canonical permission profile model into legacy shapes still required by older or remote app-server APIs."* It names the direction (canonical → legacy) and the reason it persists (older or remote peers), which is the exit condition.

**Quarantine by issue tracker doesn't work.** gemini-cli#7016 declares a shipped component temporary: *"Once this is verified to be robust for users we should remove the interim MaxSizedBox solution."* `packages/cli/src/ui/components/shared/MaxSizedBox.tsx` is still there and has grown a derivative, `SlicingMaxSizedBox.tsx`. The marker wasn't in the code, so the debt grew a second implementation.

### Gates vs ratchets

**A gate fails a brownfield codebase on day one and gets deleted within a week.** Nobody merges a PR that turns `main` red for reasons unrelated to their change; the fastest path to green is `rm ci/check.py`. A ratchet records the current violation count in a committed baseline file and fails only on *increase*.

```bash
#!/usr/bin/env bash
# ci/ratchet.sh — fails only if violations grow.
set -euo pipefail
BASE=ci/baseline/ui_core_imports.txt
rg -c --no-heading -e 'codex_core::' -e 'use +codex_core' codex-rs/tui/src | sort > /tmp/now.txt
join -t: -a1 -a2 -o 0,1.2,2.2 -e 0 "$BASE" /tmp/now.txt | awk -F: '$3 > $2 {
  printf "%s: %d -> %d\n", $1, $2, $3; bad=1 } END { exit bad ? 1 : 0 }' || {
    echo "codex-tui must not add direct codex-core imports."
    echo "Use the app-server protocol/client boundary; temporary embedded startup"
    echo "gaps belong behind codex_app_server_client::legacy_core."
    exit 1; }
cmp -s "$BASE" /tmp/now.txt || { cp /tmp/now.txt "$BASE"; echo "ratchet tightened"; }
```

Two details that matter more than the script:

- **Key the baseline per file, not as one total.** A scalar lets someone delete a violation in `app.rs` and add one in `chatwidget.rs` for free — which is exactly the churn-magnet behavior you're trying to stop.
- **The failure message names the sanctioned escape hatch.** codex's `verify_tui_core_boundary.py` prints *"Use the app-server protocol/client boundary instead; temporary embedded startup gaps belong behind `codex_app_server_client::legacy_core`."* Without that line, a blocked contributor invents their own workaround and the quarantine erodes into three quarantines.

**The trick that makes a real gate affordable.** `verify_tui_core_boundary.py` is a hard gate with **no exception list** — it checks the manifest (every dependency table, including `target.*.*`) *and* every source line, and there is exactly one legal route. That's only possible because the quarantine had already relabelled every remaining violation. The quarantine module is what converts an ungateable count into a gateable one *without doing the work first*: after codex#17399 the direct-import count is zero and the debt is now `grep -c legacy_core`, monotonically decreasing by construction. **Ratchet the thing you can't fix today; gate the thing the quarantine already absorbed.** And put the number in the PR title — codex's changelog is the burn-down chart.

---

## 7. Strangler-fig for the hard ones

For a normalized event enum (L8), a store (L18), or a stable-prefix renderer (L34–L37) in a running app:

1. **Build the new path beside the old one.** Don't touch the old path at all — new module, new types, no shared mutable state. codex forked an entire directory (codex#14717) rather than edit in place, precisely so the old path stayed green.
2. **Drive both from the same input.** Feed the recorded fixtures (L61) or a tee of the live event stream into both. If you have no fixtures, this step is where you record them; it's an hour and it is the highest-return hour in a retrofit too.
3. **Diff the two outputs in a test, not in production.** Assert on the render model, not on bytes (L62), at fixed widths (L63) — 80/120/200 is where the disagreements actually are. The diff *is* the spec of what the old path was really doing, including the accidents you'd otherwise reimplement or lose.
4. **Cut over behind a flag,** default off, then default on. Keep the flag boolean and global; per-user or per-surface flags make the fork long-lived, which is the failure mode.
5. **Delete the old path and the flag in the same PR** (codex#15922 did both). Then rename the survivor back to the original name (codex#16104) so the git history of the new code is continuous with the old name.

Two rules of thumb from the timeline: the fork window should be measured in days (codex: 11), and steps 1–3 should produce *zero* user-visible change, so any regression during them is unambiguously yours.

---

## 8. When incremental fails

Only one class of change resists all of the above: **who owns the scrollback.**

`codex-rs/tui/src/insert_history.rs`: *"Codex uses the terminal scrollback itself for finalized chat history, so inserting a history cell is an escape-sequence operation rather than a normal ratatui render."*

They changed it once, in codex#1672, to fix "can't select text": *"replaces the previous ratatui history widget with an append-only log so that the terminal can handle text selection and scrolling. **It also disables streaming responses, which we'll do our best to bring back in a later PR.**"*

Getting streaming back took three weeks and three attempts — `Stream model responses (codex#1810)` 08-05, `Streaming markdown (codex#1920)` 08-08, `Revert "Streaming markdown (codex#1920)" (codex#1981)` **the same day**, `Re-add markdown streaming (codex#2029)` 08-13. At this layer you don't get partial credit: you get a working terminal or a broken one.

The permanent tax is larger than the regression. Because scrollback is append-only and emulator-owned, every subsequent feature had to be re-derived through escape sequences — wrapping (codex#1685), URL clickability (codex#12067), Zellij redraws (codex#16578), reflow on resize (codex#18575), and ten more through codex#34204. A year of terminal-specific work. They never changed it again. gemini-cli hit the same wall from the other side (gemini-cli#7016) and chose to change the *framework* rather than the app.

**Contrast: a major framework version bump does not force any of this.** lazygit's tcell v2→v3 (lazygit#5562) — **widen the abstraction first, swap the dependency last, every intermediate commit green.** *"Refactor code to introduce a `Key` type in gocui that bundles the keyName and a rune, so that we don't have to pass these around separately everywhere"* — eight commits, the bump last. Every preparatory commit is valid against tcell v2, so the tree is shippable at each step. Same sequence one level down in `jesseduffield/gocui`: string-instead-of-rune cell content with proper unicode segmentation (2025-11-22) → replace go-runewidth with uniseg (11-24) → cache width in the cell struct (11-30) → bump tcell (12-03) → adapt `Snapshot` to the new API (12-13). No parallel tree, no feature flag and no rewrite, because the swap was preceded by refactors that made the *old* code express the *new* model.

**Say plainly which kind of change you're facing before you plan it:**

| | Scrollback ownership (L46) | Framework major version |
|---|---|---|
| Can the old code be made to express the new model? | No — a committed line can never be un-drawn | Yes — that's the whole technique |
| Intermediate commits shippable? | No | Yes, all of them |
| Correct method | Parallel path + flag, short fork, accept a feature regression | Widen abstraction, bump last |
| Reversible? | In principle; nobody has | Trivially, it's one commit |

If your change is the left column, budget for the regression and get explicit agreement on it before the first commit. If it's the right column and someone is proposing a parallel tree, they're overpaying.
