---
name: tui-craft
description: >-
  Design, build, and debug full-screen terminal UI apps — layering, state ownership, repaint
  discipline, key routing, retrofits. Triggers: picking a TUI framework; building a terminal
  chat or agent client; flicker, tearing, resize corruption, broken copy-paste, slow output with
  long content, a terminal left broken after exit; Textual, Rich, Ratatui, crossterm, Bubble
  Tea, Lipgloss, OpenTUI, Ink, prompt_toolkit, curses, ncurses, notcurses, tview, tcell,
  blessed, alternate screen, raw mode.
---

# TUI craft

**Start here, not at the laws.** The laws are an index for review (`references/laws.md`). What you need first is which of these situations you are in.

---

## 0. Should this be a TUI at all?

Ask this before anything else, because a non-fullscreen CLI is exempt from nearly every hard problem below — L84 has the exemption list.

A full-screen alternate-screen app earns its cost only when you need at least two of: content that updates in place, modal navigation, a persistent layout, direct manipulation, or a long-lived session.

If you need none of them, write a streaming CLI with ANSI colour and stop reading. If you need one, build inline first and keep full-screen as a flag — both major agent CLIs ship non-fullscreen as first-class.

Full decision aid with the price list: **`references/interaction.md` §0**.

Out of scope: ordinary CLI work (argument parsing, printing a table, a progress bar or spinner in a script that doesn't take the screen), browser-based terminal emulators (xterm.js and similar), and shell-prompt (PS1/starship) customization.

---

## 1. Which situation are you in?

| Situation | Read |
|---|---|
| Deciding whether to build a TUI | `interaction.md` §0 — it may save you everything else |
| Starting a new TUI | `build-order.md`, then §2 below |
| Inherited a TUI you didn't write | `retrofit.md` — start at its symptom table |
| Debugging a specific symptom | `retrofit.md` §1 — symptom → root cause → fix |
| Auditing an unfamiliar TUI quickly | `retrofit.md` §2 — a dozen runnable checks |
| Content arrives incrementally over a network | `streaming.md` |
| Fighting the terminal itself — exit state, width, resize, tmux, colour | `terminal.md` (start with its pre-ship checklist) |
| Designing keys, focus, modals, discoverability | `interaction.md` |
| Reviewing a diff | `laws.md` — cite by number |
| Need an exact escape sequence or version fact | `hard-facts.md` |

**Scope warning.** If your data is local and synchronous (file browser, git UI, process monitor), most of `streaming.md` is dead weight — its opening paragraph names the two parts that still apply. Laws are tagged `[net]`, `[new]`; untagged laws apply to any TUI.

---

## 2. Invariants — true regardless of situation

These are the ones where reading them late is too late. Each is one line here; the rationale and failure mode live with the law in `laws.md`.

- **Write the teardown before you set the first mode** — idempotent, reentrant, callable from a panic hook; runs on `SIGINT`, `SIGTERM`, `SIGHUP`, and Ctrl-Z. `L71–L73` → `terminal.md` §1
- **All logging goes to a file; enforce it with a lint rule.** `L48`
- **Treat every byte from a non-local source as data, not terminal instructions.** `L96` → `terminal.md` §8
- **`isatty` selects a different renderer, not a dimmer one** — honour `NO_COLOR`, `TERM=dumb`, `CLICOLOR_FORCE`. `L76`
- **Measure text in grapheme clusters, never bytes or codepoints.** `L77, L78`
- **Query capabilities — never infer from `$TERM` — with a sentinel and a timeout, and consume the reply before exiting.** `L42, L80, L81, L83` → `terminal.md` §5
- **Ship a kill-switch env var for every terminal protocol you opt into.** `L43`
- **Mouse capture and native text selection are mutually exclusive; ship the three mitigations.** `L45`
- **Never hardcode a colour chosen against an assumed background.** `L82`
- **State that outlives a keystroke goes in the store; state that dies with the frame stays in its widget — and never read back from a widget to make a domain decision.** `L1`
- **One writer per kind of state.** `L14`
- **Model status as an enum, not booleans.** `L22`
- **Key the render cache on `(id, revision, width)`, and invalidate everything on a width change.** `L38`
- **Never repaint per event** — ingest at arrival rate, repaint on a bounded tick, flush immediately when idle. `L24, L25`
- **Write the key-routing order down once:** escape hatches → modal stack → focus → ancestors → globals. `L86`
- **Paint the chrome before you have the data; every blocking call moves off the UI thread on day one.** `L91`
- **Two decisions are effectively irreversible: full-screen vs inline `L84`, and who owns the scrollback `L46`.** → `retrofit.md` §8

---

## 3. If you are starting fresh

Follow `build-order.md`. Its central claim: **the first four steps contain no terminal code at all.** Get the data layer right and testable before a character is drawn, because every bug you find there is cheap and every bug you find after the UI exists is not.

## 4. If you inherited it

Go to `retrofit.md`. Its ordering:

1. **Diagnose from the symptom table first.** In nearly every case the reported symptom is cosmetic and the root cause is a layer boundary — and it is not fixable inside the widget that visibly misbehaves.
2. **Audit with the greps** before proposing anything.
3. **Rank by cost.** Cheap self-contained fixes first; they buy credibility for the expensive ones.
4. **Use a ratchet, not a gate.** A CI check that fails a brownfield codebase on day one gets deleted. Record the current violation count; fail only on increase.
5. **When you do restructure: build the new path in parallel behind a flag, diff the two, then delete the old one.** Keep the parallel copy for days — codex's lasted eleven.

Cost, roughly: cheap self-contained fixes ≈ a day total, contained fixes ≈ a week, structural ≈ a rewrite — `retrofit.md` §3 has the exact lists.

Do not apply greenfield laws to an existing codebase without translating them. "Draw the layers before the first widget" is not advice to someone whose widgets shipped two years ago; `retrofit.md` gives the brownfield form of each.

