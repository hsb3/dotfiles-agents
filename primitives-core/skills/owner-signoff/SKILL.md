---
name: owner-signoff
description: Present a batch of decisions, approvals, or questions to the project owner as a local HTML form in their browser instead of asking in chat. Use when multiple items need the owner's input (sign-offs, dispositions, priorities, open questions), when the owner asks "what do you need from me", or asks for a summary/quiz they can react to. Answers flow back to a JSON file the session picks up automatically.
---

# Owner sign-off form (HTML Q/A loop)

Standing pattern (owner-ratified 2026-07-18: "this is a good pattern to adopt in
general — will help us go faster"). Instead of a wall of chat questions, serve a
form; the owner answers inline at their own pace; the answers land in a file; the
session is notified the moment they submit.

## The loop

1. **Build the form** — copy `assets/template.html` into a dated batch dir inside the
   project's working area (convention: `_meta/signoff/YYYY-MM-DD-<topic>/index.html`;
   any project-appropriate dir works). Fill in the sections (rules below).
2. **Start the one-shot server** as a background Bash task (`run_in_background: true`):

   ```bash
   python3 <skill-dir>/scripts/serve_signoff.py <batch-dir> [port]
   ```

   Default port 8737; the script walks forward to the next free port if taken —
   **read the first line of its output for the actual URL** before opening.
3. **Open it**: `open "http://localhost:<port>/"`. Tell the owner it's open and list
   the items in one line each.
4. **Wait — do not poll.** The server accepts exactly one POST `/save`, writes
   `answers.json` next to `index.html`, then exits. Its exit is the background-task
   notification: when it fires, Read `answers.json` and act.
5. **Fallback**: if the server is gone when he submits (much-later submit, reopened
   tab), the page downloads `*-answers-*.json` to `~/Downloads` and tells him to say
   so — pick it up there.

## Form rules (what makes these work)

- **One section per item**, each with: a short context paragraph (why this needs him),
  an explicit **recommendation preselected** as the first radio, a "Modify"/alternative
  option, and a per-item notes `<textarea>`. Free-text `<input type="text">` for
  things like names. Radios are grouped by the section's `data-id`.
- **All-defaults must be one click**: if he agrees with every recommendation, Submit
  with no other interaction is a valid, complete answer.
- Add a read-only **summary block at the top** when he may have lost the thread
  ("where things stand" — done / decided / waiting-on-you). Keep it scannable.
- End with a **general-notes section** (`data-id="Z"`).
- Explanatory register, plain language, no jargon fragments. Spell out file paths and
  consequences ("I copy X as uncommitted changes; you review and commit").
- Only include items that genuinely need him — if nothing is blocked on an item, it
  is a status line in the summary, not a question.
- Never put secrets in the form or the answers file.

## After pickup

- Convert answers into their proper records immediately — in a Backlog.md project, via
  the backlog CLI (decisions, docs, task updates) — and report back what was executed
  vs what remains the owner's. The records are the trail: **do not keep `answers.json`
  or `index.html`** — delete the batch dir once the records land.
- Notes fields may contain new facts that contradict prior findings — correct the
  affected documents in place, dated, when they do.

## Mechanics worth knowing

- The template's JS posts to a **relative** `/save`, so it works on whatever port the
  server picked; it needs no external resources.
- One batch dir per sign-off, dated, never reused — a resubmit after server exit goes
  through the download fallback by design (last file wins; say which you're using).
- The server binds 127.0.0.1 only.
