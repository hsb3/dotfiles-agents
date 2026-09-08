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

1. **Write the spec** — a YAML or JSON file in a dated batch dir under the project's
   batch root: `<batch-root>/YYYY-MM-DD-<topic>/signoff.yaml`. Ask for the root instead
   of assuming it (from the project root):

   ```bash
   python3 <skill-dir>/scripts/build_signoff.py --batch-root
   ```

   It prints the root and builds nothing: `_meta/signoff` unless the project sets a
   `signoff:` key in `.claude/owner-signoff.local.md` (project-relative; blank, absent,
   or outside the project root leaves the default in force). Schema below. Never
   hand-write the HTML.
2. **Build the form** (foreground, so validation errors surface immediately):

   ```bash
   python3 <skill-dir>/scripts/build_signoff.py <batch-dir>/signoff.yaml
   ```

   Validates the spec and writes `index.html` next to it; on schema errors it prints
   every problem and exits 1 — fix the spec and rerun.
3. **Start the one-shot server** as a background Bash task (`run_in_background: true`):

   ```bash
   python3 <skill-dir>/scripts/serve_signoff.py <batch-dir> [port]
   ```

   Default port 8737; the script walks forward to the next free port if taken —
   **read the first line of its output for the actual URL** before opening.
4. **Open it**: `open "http://localhost:<port>/"`. Tell the owner it's open and list
   the items in one line each.
5. **Wait — do not poll.** The server accepts exactly one POST `/save`, writes
   `answers.json` next to `index.html`, then exits. Its exit is the background-task
   notification: when it fires, Read `answers.json` and act.
6. **Fallback**: if the server is gone when he submits (much-later submit, reopened
   tab), the page downloads `*-answers-*.json` to `~/Downloads` and tells him to say
   so — pick it up there.

## Spec schema

YAML needs PyYAML on the system python3; JSON always works. Unknown keys are
rejected (they're almost always typos).

```yaml
title: Sign-off — plugin restructure          # required
project: dotfiles-agents                      # optional, shown in the header
date: 2026-08-26                              # optional, shown in the header
summary:                                      # optional "where things stand" block
  done: ["Roster migrated", "CI green"]
  waiting: ["The three items below"]
items:                                        # required, 1+ items
  - question: Delete the legacy branch?       # required
    context: Why this needs the owner — one or two plain sentences.   # required
    recommendation: The recommended call and why, one sentence.       # required
    category: Cleanup                         # optional, default "Decision"
    id: A                                     # optional; auto A/B/C… ("Z" reserved)
    choices: [Approve, Modify (note below)]   # optional; first one is preselected
    text_field: New name…                     # optional free-text input, this is its
                                              # placeholder; answers key <id>_text
```

Every item automatically gets a notes textarea; a general-notes section (`Z`) is
always appended. Answers come back keyed by item id:
`{"items": {"A": {"choice": "...", "text": "...", "notes": "..."}}}`.

## Content rules (what makes these work)

- **All-defaults must be one click**: `recommendation` is preselected as the first
  choice, so agreeing with everything is Submit with no other interaction.
- Include the `summary` block when he may have lost the thread; keep it scannable.
- Explanatory register, plain language, no jargon fragments. Spell out file paths and
  consequences ("I copy X as uncommitted changes; you review and commit").
- Only include items that genuinely need him — if nothing is blocked on an item, it
  is a `summary` line, not a question.
- Never put secrets in the spec, the form, or the answers file.

## After pickup

- Convert answers into their proper records immediately — via the project's tracker: a
  board issue, a GitHub issue, or a decision record (decisions, docs, task updates) —
  and report back what was executed vs what remains the owner's. The records are the
  trail: **do not keep `answers.json` or `index.html`** — delete the batch dir once the
  records land.
- Notes fields may contain new facts that contradict prior findings — correct the
  affected documents in place, dated, when they do.

## Mechanics worth knowing

- The template's JS posts to a **relative** `/save`, so it works on whatever port the
  server picked; it needs no external resources.
- One batch dir per sign-off, dated, never reused — a resubmit after server exit goes
  through the download fallback by design (last file wins; say which you're using).
- The server binds 127.0.0.1 only.
