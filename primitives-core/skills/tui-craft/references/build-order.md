# Build order

Law numbers (`L…`) refer to `laws.md`.

The dependency order says what depends on what. The build order says what to write first so each step is verifiable on its own. Read this before starting a new terminal app.

Steps 1–4 contain no terminal code at all — on either track. That is the point: be certain the data layer is right before a single character is drawn. There are two tracks through those four steps, because "the data layer" means something different depending on where your data comes from. Step 5 onward is shared.

## `[net]` — content arrives incrementally over a connection

| # | Build | Done when |
|---|---|---|
| 1 | Config + transport + a `cat`-style CLI that dumps raw frames. No TUI, no parsing. | You hold a connection through a long operation and see the keepalives. |
| 2 | Generated API client. Wire the regenerate-and-diff CI job now (L7). | `main` fails CI if someone hand-edits generated code. |
| 3 | Capability probe + normalizer + **the fixture recorder** (L61). | You can replay a recorded session from disk in under a second. |
| 4 | Domain reducers against the fixtures (L8, L12). | Reducer tests pass with no network and no terminal. |

## `[local]` — data is local and synchronous (file browser, git UI, process monitor)

| # | Build | Done when |
|---|---|---|
| 1 | Identify the source of truth, plus a dump/`cat`-style capture of the underlying command's or API's raw output. No TUI, no parsing. | You can capture a representative run to disk on demand. |
| 2 | Pure view-model — parse, wrap, sort, filter — as functions with unit tests. No terminal in sight. | View-model tests pass with no terminal and no live subprocess. |
| 3 | Recorded command-output fixtures, plus one synthetic large fixture. | You can replay a recorded capture from disk in under a second. |
| 4 | Reducers / state transitions against the fixtures (L8, L12). | Reducer tests pass with no subprocess and no terminal. |

## 5 onward — shared

| # | Build | Done when |
|---|---|---|
| 5 | Minimal shell: one scroll region, one composer or list, plain text, no markdown. | First moment you can actually use it. |
| 6 | Stable-prefix streaming render + finalize re-render (L34–L37). `[net]` mainly, but applies to any high-frequency `[local]` update stream too. | A long response with a code fence and a table renders correctly at full rate. |
| 7 | Height cache + virtualization (L38–L39). | 5,000 synthetic items scroll smoothly (L64). |
| 8 | Failure paths: reconnect, resync, cancel, unknown payloads (L56–L59) for `[net]`; process-gone, permission-denied, partial-read for `[local]`. | You can kill the network (or the underlying process) mid-stream and recover without a restart. |
| 9 | Everything that makes it pleasant: palette, themes, multi-session, discoverability (L52–L53). | — |

## Fixtures to record at step 3

**`[net]`** — the canonical 9-item recording list lives in `streaming.md` § Wire your fixtures first.

**`[local]`** — two fixtures cover it: one representative capture of the underlying command's or API's real output, and one synthetic large fixture (thousands of rows or entries) to catch scaling and virtualization bugs before a user's machine does.

## Decisions that must happen before step 5

Ranked by cost to reverse. Two are universal; two are `[net]`-only.

1. **Native scrollback vs alternate screen** (L46) — universal. Not retrofittable; L46 has the cost list.
2. **The normalized event enum** (L8) — `[net]`-only. Everything above it is written against it. Getting replace-vs-append wrong here means fixing it in twenty places later.
3. **Store shape** (L18) — universal. Switching between owned-struct and reactive-graph means rewriting the whole upper half.
4. **Language / SDK** — `[net]`-only. Determines whether your SDK handles reconnect for you, which is the single largest chunk of undifferentiated work in this kind of app.
5. **Framework** — universal. If layers are drawn properly this is a large fraction of the code — genuinely the least consequential of the five.
