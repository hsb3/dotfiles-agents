# Streaming clients

Law numbers (`L…`) refer to `laws.md`.

Read this when the content on screen arrives incrementally from a network source — an agent or chat client, a log tailer, a dashboard fed by SSE, WebSocket, gRPC streaming, or long-poll. The defining property is not "network" but "the thing you are drawing is still being produced while you draw it."

If your data is local and synchronous — a file browser, a git UI, a process monitor reading `/proc` — most of this does not apply. Two parts still do. **The ingest→render loop applies to any high-frequency event source**, including inotify storms, a 200Hz `/proc` poll, and a subprocess writing to a pipe: you still coalesce, you still repaint on a bounded tick, you still bound the queue. **The event enum and the four-kinds-of-state table apply** whenever more than one producer writes to your model. Everything about reconnect, resume tokens, replay dedup, replace-vs-append and stable-prefix rendering is dead weight for you; skip it.

---

## The normalized event enum (L8)

Every wire event becomes one variant of one internal enum before it reaches your domain. This is the seam the rest of the file hangs on: it is where replace-vs-append is decided, where namespaces become identity, where unknown payloads stop being dangerous, and where your fixtures replay into.

```rust
enum Event {
    // --- work lifecycle ---
    RunStarted   { run_id: Id, attempt: u32 },
    RunEnded     { run_id: Id, status: RunStatus },      // authoritative terminal signal

    // --- transcript content: the two variants that matter most ---
    ItemBegin    { key: Key, role: Role, meta: Meta },
    ItemSnapshot { key: Key, content: Content },          // REPLACE semantics
    ItemDelta    { key: Key, block: usize, text: String },// APPEND semantics
    ItemEnd      { key: Key, usage: Option<Usage> },

    // --- sub-operations ---
    OpStarted    { key: Key, name: String, args: Json },
    OpOutput     { key: Key, chunk: String },
    OpEnded      { key: Key, result: Json, is_error: bool },

    // --- state and control ---
    StateSnapshot { scope: Namespace, values: Json },
    Paused        { key: Key, payload: Json },            // needs user input to continue
    Checkpoint    { id: Id, parent: Option<Id>, step: u64 },

    // --- meta ---
    StreamError { error: ErrorInfo, retryable: bool },    // arrives after a 200 (L58)
    Lagged      { skipped: u64 },                         // you dropped things; say so (L29)
    Unknown     { kind: String, raw: Json },              // see below
}

// Identity is a pair, never a bare id (L20).
struct Key { namespace: Namespace, id: Id }
```

**`Unknown { raw }` is what makes L59 mechanical rather than aspirational.** Without it, an unrecognized `event:` name has three possible fates and two of them are bugs: a panic on an exhaustive match, a silent `continue` that loses data the user needed, or a `default` branch that has nowhere to put the payload. With it, the normalizer's fallback is total — anything it cannot classify becomes `Unknown`, the renderer registry's last resort renders pretty-printed JSON, and the user sees the data. Servers add event types faster than clients adopt them; an old client must degrade to "I don't know what this is, here it is" rather than to a crash or a blank.

**What belongs in the enum:** anything a reducer branches on. Namespace, because two sub-agents streaming into one transcript merge into one garbled bubble if you key on bare ids. The replace-vs-append distinction, resolved once here rather than re-derived in every reducer. Ordering keys, if the protocol has them.

**What does not:** wire-format artifacts. Frame boundaries, keepalive comments, CRLF vs LF, chunked-encoding details, retry hints, `Last-Event-ID` bookkeeping, protocol version differences. If your domain layer can tell whether the bytes arrived as SSE or WebSocket, the normalizer leaked. The test: your reducer test file should contain no string that appears in the wire protocol's spec.

**Make it your log format (L19).** Serialize the enum to a trace file and a bug report becomes a fixture. This is nearly free at the point you define the enum and expensive to retrofit once twenty variants exist.

---

## Four kinds of state (L12)

| Kind | Example | Who writes it | Survives reconnect? | Survives restart? | Where it lives |
|---|---|---|---|---|---|
| **1 · Server-authoritative** | message history, run status, checkpoints, thread list | The reducer, fed by the normalizer — nothing else | Yes, but **reconcile** it: refetch and diff (L15) | Refetch from the server; do not persist (L12, L15) | Store |
| **2 · Stream-derived (hot)** | the in-flight item being assembled, live sub-operation output | The ingest loop | No — it is re-driven by replay or discarded | No | A tail buffer *outside* the store, promoted on finalize (L16) |
| **3 · Session / UI** | scroll offset, focus, selected thread, open dialogs, composer draft | The shell, in response to input | Yes — it is unaffected by the network | Selectively: drafts and last-thread yes (L54), scroll offset no | Store for cross-widget state; the widget itself for per-frame state |
| **4 · Derived / render** | rendered markdown blocks, wrapped lines, height cache, syntax spans | Nobody — it is a cache | Irrelevant, it rebuilds | No — delete it freely | Cache keyed `(id, revision, width)` (L38) |

To classify a new piece of state, ask in order: *Does the server have an opinion about it?* → kind 1. *Is it a partial thing that a completion event will make authoritative?* → kind 2. *Is it a pure function of the others plus terminal width?* → kind 4. *Otherwise* → kind 3.

**One writer per kind (L14).** Exactly one path writes kind 1: the reducer. Exactly one writes kind 3: the shell. When two paths write the same kind you get a race that presents as "sometimes the wrong message updates," which reads like a rendering bug and is not one.

**Kind 2 stays off the store's hot path.** If every delta dispatches through the store and notifies subscribers, you pay reducer plus notification plus re-render per token. Keep the in-flight tail in a buffer the ingest loop owns and promote it into the store once on finalize.

**Kind 4 must be reconstructible from nothing (L13).** Ship a `debug: clear render cache` command and assert the frame is unchanged afterwards. Scope the assertion honestly: a frame containing a spinner, a relative timestamp, an elapsed-time counter, or an animation is not byte-identical across a cache clear and never will be. Assert on a frame captured with animations disabled and clocks frozen, or diff only the transcript region. The invariant you are protecting is "nothing that is *only* in the cache," and it is worth a test because the failure mode — a value written into the cache and never anywhere else — is invisible until the day something clears it.

---

## The ingest → render loop (L24, L25, L30)

Three separable jobs: a producer that only pushes, a drain that produces exactly one state update per batch, and a scheduler that turns N repaint requests into one frame.

```ts
const COALESCE_MS = 16                       // one frame at 60fps
const queue = new BoundedQueue(1024)         // size per tier — classify first, see below
let lastFlush = 0, pendingFlush = null

// Producer: the network task. Touches no state, never repaints, never renders.
async function reader(stream) {
  for await (const frame of stream) {
    const ev = normalize(frame)              // wire → Event (L8); the only place wire types exist
    if (queue.tryPush(ev)) continue
    if (isLossless(ev)) await queue.push(ev) // block the reader → backpressure reaches the socket
    else queue.replaceOldest(ev, /* count */ n => Lagged({ skipped: n }))  // L29: never silent
  }
}

// Wakeup: called when the queue goes non-empty. This is the whole L25 heuristic.
function onArrival() {
  const since = now() - lastFlush
  if (since >= COALESCE_MS) flush()          // idle → flush NOW; first token is not delayed
  else if (!pendingFlush)                    // busy → one timer, not one per event
    pendingFlush = setTimeout(flush, COALESCE_MS - since)
}

// Consumer: sole writer of kind-1 and kind-2 state.
function flush() {
  pendingFlush = null
  lastFlush = now()
  const batch = queue.drainAll()             // everything waiting — not one item, not head()
  if (batch.length === 0) return
  applyBatch(state, batch)                   // ONE update for N events, not N updates
  requestRepaint()                           // request, not perform; scheduler dedupes to 1 frame
}
```

The comments in the code are the spec. L27 adds: wrap the resulting frame in synchronized output.

Calibration table: `hard-facts.md` § Repaint budgets.

30fps is a fine default and 60 is a fine ceiling; make it configurable (L26), because a user on SSH over a satellite link and a user on a local kitty want different numbers.

---

## Backpressure tiering (L28, L29, L30)

Classify every event as **lossless** or **best-effort** *before* you choose a queue size, because the classification determines what the size means. For a lossless tier the capacity is a latency/memory tradeoff and overflow blocks the reader — the queue is full, the socket stops being read, TCP applies backpressure, and the server slows down. That is correct behavior. For a best-effort tier the capacity is a drop threshold and overflow discards. Pick the number first and you will have silently decided which of these you built.

| Tier | Typically | On overflow |
|---|---|---|
| **Lossless** | transcript deltas and snapshots, completion/terminal signals, error frames, pause/interrupt events, run status transitions | Block or grow. Dropping one corrupts visible output or leaves the UI waiting on a completion signal that already fired. |
| **Best-effort** | progress percentages, telemetry, debug traces, checkpoint notifications, sub-operation output chunks that are re-fetchable | Drop oldest, count them, and emit `Lagged { skipped }` into the stream. |

A bounded channel that dropped message deltas under load produced **permanently corrupted or incomplete paragraphs that persisted for the rest of the session** — because the renderer was assembling those deltas incrementally, so a dropped delta is not a dropped frame, it is a hole in a string that nothing will ever fill. A dropped progress event costs you a stale percentage for 16ms. That asymmetry is the whole tiering argument.

**Surface the drop.** `Lagged { skipped }` is a real enum variant the UI handles, not a log line — show "⚠ 47 events dropped" in the status bar, and treat it as a resync trigger for anything server-authoritative (L15). Silent truncation reads as "everything is fine" when it very much is not, and it converts a diagnosable performance problem into an unreproducible correctness complaint.

Bound every queue regardless of tier. An unbounded channel in front of a slow consumer is a memory leak with extra steps, and it fails at 3am with an OOM rather than at noon with a visible stutter.

---

## Replace vs append, and how to find out which you have (L31)

The rule: if the server accumulates and sends the whole item each frame, **replace by id**. If it sends deltas, **append**. This is a property of the wire format, not a judgment call, and it is resolved exactly once — in the normalizer, by emitting `ItemSnapshot` or `ItemDelta`.

**How to determine it.** Do not read the docs and guess; protocols routinely do both on different modes, and some do one for text and the other for tool arguments. Record a fixture of one message, then diff consecutive frames:

```python
frames = [f for f in load_fixture("plain-response.jsonl") if f.item_id == target]
texts  = [f.content for f in frames]
accumulating = all(texts[i+1].startswith(texts[i]) for i in range(len(texts) - 1))
# accumulating → server sends snapshots → REPLACE by id
# not         → server sends deltas    → APPEND
```

If frame N+1 contains frame N as a prefix, the server is accumulating. Run this per content channel — text, reasoning, tool-call arguments — because they can differ within one protocol. Keep the check as a test; a server upgrade that flips the mode is otherwise a silent corruption.

Wrong, when the server accumulates:

```ts
case "item_chunk":
  item.content += ev.content        // "HelloHello worldHello world!" — the doubling bug
```

Right:

```ts
case "item_snapshot":               // normalizer decided this, from the fixture evidence
  item.content = ev.content         // wholesale replace
  item.revision += 1                // revision is the render-cache key (L21, L38)
```

The doubled-text bug is the most common visible defect in streaming clients, and it hides well: with fast tokens and a narrow terminal, the first few frames look like ordinary streaming. It becomes obvious only in long responses, by which point the reflex is to suspect the renderer.

**Order by sortable id where one exists (L33)** — time-sortable ids, or a monotonic sequence number — because out-of-order arrival across namespaces is normal, not exceptional. Where the protocol emits no such key, arrival order is all you have; say so in a comment rather than inventing a fake key.

---

## Stable-prefix rendering (L34–L37)

Re-rendering a whole message per token is O(n) per token and O(n²) per message; at 4,000 tokens that is where the frame budget goes. Freeze a prefix, re-render only the tail:

1. Track `stable_upto` per in-flight item — a line offset or token index.
2. Cache the render of `[0, stable_upto)`. It can never change.
3. Re-render only `[stable_upto, end)` per flush.
4. Advance `stable_upto` only to a boundary your parser confirms.
5. Re-render the whole item once on finalize.

**Step 4 is the hard one, and the answer is not to scan for it yourself.** In order of preference: **parser source maps** — the parser picks the boundary, you never reason about syntax (Textual's approach, MIT, the one to port); **re-lex the tail with a two-token safety margin** — coarser, cheap, works with any lexer (OpenTUI's approach); failing both, **commit only at a blank line with no open fence, table, list continuation, or link-reference definition**. Implementation detail, four ways: `hard-facts.md` § Stable-prefix markdown.

**Never commit at a bare newline.** A newline inside a fenced block, a table, or a list is not a boundary, and committing there is what produces code-fence blanking — the fence opens, the tail renders as code, the closing fence arrives after you have already committed the wrong interpretation. Under native scrollback (L46) the committed line cannot even be un-drawn.

**The finalize re-render is not optional.** oterm's fix was titled *"re-render Markdown on `finish_stream` to fix code-fence blanking."* Budget the full re-render at finalize from the start; it costs one pass per message and removes an entire class of bug.

**Hold back constructs whose layout depends on data you have not received (L37).** Tables above all: column widths are a function of rows that have not arrived, so a table committed early reflows — or worse, cannot reflow. Keep the active table in the mutable tail until it closes. The same reasoning applies to anything width-derived: aligned lists, box-drawn panels, right-aligned columns.

**Cache keyed `(id, revision, width)`, invalidated wholesale on resize (L38), and check whether your markdown renderer is thread-safe before calling it from both the ingest task and the UI task (L41).** Most are not, and the corruption looks exactly like a parser bug.

---

## Two state machines (L56)

Connection lifecycle and work lifecycle fail independently. Enumerate both before writing the reader loop; a boolean pair expresses neither (L22).

```
Connection:  connecting → live → degraded(retrying, attempt n, next in Ns)
                              → resuming(from event id)
                              → resyncing(snapshot refetch)
                              → dead(cause)

Work:        idle → starting → running → paused(needs input) → resuming → running
                                       → done | failed(cause) | cancelled
```

**The cross-product is the point.** "Stream dead, work still running" is a real, common cell, because servers usually default to continuing on disconnect — closing a laptop lid should not kill an agent run. It needs different copy from "run failed": *"Disconnected — the run is still going on the server. Reconnecting…"* versus *"The run failed: <cause>."* Telling a user their work failed when it is still executing costs them a duplicate submission; telling them it is still running when it died costs them a wait that never ends.

For each connection state, specify three things before you build the UI:

| Connection state | Status line | Input accepted? | Interrupt key does |
|---|---|---|---|
| `connecting` | "Connecting to <host>…" | Yes — buffer it, send on connect | Cancel the connection attempt |
| `live` | Nothing, or a quiet indicator | Yes | Cancel the running work (round-trip to the server) |
| `degraded(n, t)` | "Reconnecting… attempt n, retrying in t" | Yes — queue locally, do not fail the send | Stop retrying and go to `dead(user)` |
| `resuming(id)` | "Resuming from <id>…" | Yes, queued | Abandon resume, go to `dead(user)` |
| `resyncing` | "Re-syncing…" | Yes, queued | Abandon, go to `dead(user)` |
| `dead(cause)` | "Disconnected: <cause>" + a retry key | Yes — typing is fine, sending shows the error | Nothing to interrupt; offer reconnect |

Note that input is accepted in every state. A composer that greys itself out during a reconnect loses a user's typing to a network blip, which is the least forgivable small bug in a chat client (L54). Queue the send, show it as pending.

**Detect completion two ways.** Some pause mechanisms emit no payload at all — a static breakpoint or a policy hold may only be visible as a status field on a subsequent poll. If you only listen for the pause event, those hang your UI in `running` forever. Cross-check against the authoritative status whenever the stream ends without a terminal event.

---

## Reconnect and resync (L32, L15, L57)

**Dedup on replay.** Reconnect windows overlap by design — the server replays from your last acknowledged id, and "last acknowledged" is approximate. Keep a bounded LRU of seen event ids (10,000 is a reasonable, field-tested size) and drop repeats at the normalizer. Without it you get duplicated messages that look like a rendering bug and are not.

**Resumption is often opt-in and fails silently.** A typical shape: a per-request `resumable` flag defaulting to false, a `Last-Event-ID` header, and a retention window measured in minutes. If the flag is off, the server emits **no event ids at all** — so there is nothing to resume with, no error is raised, and the failure only appears as "the transcript is missing a chunk" much later. Assert on the presence of event ids in a test against a real fixture. The absence is the failure signal and it is silent.

**Model the post-window path as a state, not an error.** When you fall outside the resume window, when a sequence cursor falls behind the server's ring buffer, or when your own best-effort tier overflowed: enter `resyncing`, refetch a state snapshot, diff it against your cache, and apply the difference. Show it in the status line. This is a normal path, it will happen on every laptop lid close longer than the window, and if it is coded as an error the user's only recovery is a restart.

**Subscribe first, snapshot second.** Open the stream, *then* fetch the bootstrap snapshot. The reverse order leaves a gap between "snapshot taken" and "stream attached" into which events fall permanently. Subscribing first means you may buffer events that the snapshot also contains — which is fine, because you already have dedup, and which is exactly why dedup comes first.

**Retry is not idempotency (L15).** If the protocol has no idempotency key, a retried submit can produce two runs. Reconcile — refetch and check whether the work already started — before retrying anything that creates server state.

---

## Wire your fixtures first (L61)

Record real sessions to disk in week one, from the raw frames, before the normalizer exists. The corpus is the highest-return artifact in the project: once you can replay a 4,000-token streaming response with three sub-operations and a mid-stream error, from a file, in 50ms, every subsequent bug becomes a regression test, and the normalizer, reducers, and stable-prefix renderer are all testable with no network and no terminal.

Record at minimum:

1. A plain response — your replace-vs-append evidence lives here.
2. One with tool calls or sub-operations, including one that fails.
3. One that pauses mid-run for user input.
4. One that pauses via a *different* mechanism, if the protocol has one — these often carry no payload and are the easiest thing in this file to miss.
5. One with nested namespaces or sub-agents streaming concurrently.
6. One that errors mid-stream, after HTTP 200 (L58).
7. One where you kill the network and reconnect *inside* the resume window.
8. One where you kill the network and reconnect *outside* it — the path everyone forgets, and the one that proves your resync state exists.
9. A pathological one: a long response containing an unterminated code fence, a wide table, and CJK or emoji text.

Store the raw frames, not the normalized events — normalized events are a derived artifact and re-deriving them is how you test the normalizer. Keep them in the repo, not in a cache directory; they are source, not state.
