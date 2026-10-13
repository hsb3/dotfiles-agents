# SOP feedback

## Unclear, wrong or missing

- **Step 5, an acceptance criterion that the build changes.** The SOP says to rewrite `--plan` when the work drifts, but not what to do when a criterion itself moves to another task (TASK-3's "contents entries returned" moved to Layout, because contents must show link-rewritten headings). I removed and re-added the criterion with `--remove-ac`/`--ac` and added one to TASK-5; doing that after the task commit and amending it pulled TASK-5's task file into TASK-3's commit. The SOP could say: fix criteria before the finish step, and add criteria to a later task in that later task's commit.
- **Step 3, actor-to-ghost relations.** The block shows actor relations only to the scanned container (`groma add relation <actor> <bin>-cli`). A scenario such as "the maintainer opens the preview in a browser" needs an actor to reach a planned component (`server`). `groma draft relation maintainer server --draft v1` works, but it tags the *actor* with `draft: v1`, which the SOP never mentions. `groma remove v1` in step 6 did clear it, so the only gap is the documentation.
- **Step 5, verifying a long-running command (`serve`).** Nothing says how to exercise a server command by hand in an agent's shell. A server started with `&` in one sandboxed command cannot be signalled from the next (`kill` → EPERM), so a manual check leaves a process running for the user to stop. Tests that spawn the server with `Bun.spawn` and kill it in `finally` are the safe route; the stack notes could say so next to the `Bun.spawn` row.
- **Step 3, externals that the unit never contacts.** The spec lists GitHub's content hosts and jsDelivr as systems the output *points at*, but the CLI never calls. The SOP's guidance ("an external for every outside system a request leaves for") does not cover a system that only appears in generated links; I modelled them as relations from the component that writes the URL, with technology "URL, never contacted", plus relations from the reader.
- **Decisions: keeping the frontmatter verbatim.** Filling a decision body by rewriting the whole file (heredoc) makes it easy to change the generated `date:` line by accident (I did once, to a minute-accurate equivalent). The SOP could recommend editing only below `## Context`.
- **Dates.** `groma-quality.sh set` stamps the local date (2026-10-12) while backlog records UTC (2026-10-13) for the same session, so the quality record and task timestamps disagree near midnight.
- **Stack notes, `rejects` without `await`.** `bun test` passes an un-awaited `expect(...).rejects` assertion silently; worth one line in the TypeScript-on-Bun notes.

## Worked well

- The first scan of the TypeScript skeleton took well under a second and named the container after the `bin` (`site`), exactly as the stack notes say; `--id site-cli` in the same edit as the meaning flags worked first time.
- Planning every component-to-component link as a draft relation in step 3 paid off: each derived `Calls imported function` row that appeared later (`pages -> config`, `links -> pages`, `links -> render`, `layout -> pages`) was a link the design had genuinely missed, and authoring it with a real description took one command.
- `groma lint`'s duplicate-logic gate caught two near-identical validators in the first task; the extraction it pushed towards was an improvement.
- The git-based `--modified-file` one-liner made the finish step mechanical, and the PostToolUse hook's `recorded <path> on TASK-n` lines kept the list current for file-tool edits.
- `groma remove v1` cleared every draft tag (the actor's included) and the drafts folder in one step; `groma lint --strict` and `groma view --check` gave an unambiguous finished state.
