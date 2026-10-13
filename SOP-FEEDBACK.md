# SOP feedback

## Unclear, wrong or missing

- **Step 2, a second application in one package.** The spec has two runnable parts in one `package.json`: the `bin` CLI and a Vite UI under `ui/`. The first scan made a container only for the `bin` entry and put `ui/src/main.tsx` directly under the system as component `main`. The skill covers only one entry point. What worked: `groma draft container "Toolbox UI" --parent evals --draft v1`, then `groma edit main --parent toolbox-ui` while `main` was still empty, then drafting the UI ghosts with `--parent toolbox-ui`. The skill could name this case (Vite/SPA root without its own `package.json`).
- **Step 3, runtime containers no scanner can see.** The PocketBase service is code (`pb_migrations/*.js`, `pb_hooks/*.pb.js`), but the configured scanners include only `*.ts`/`*.tsx`, so no scan will ever create or match it. The skill and the structure guide describe `groma add container` only for data stores; I used it for the service as well, since a drafted container would never match. Saying so explicitly would remove the doubt.
- **Step 2's example is Go-first.** The TypeScript skeleton (`export {};`) was already committed by `init`, so step 2 was only "scan"; the block's `mkdir -p cmd/<bin>` lines are noise for this stack. The stack-notes table carries the TypeScript case, but one has to cross-read.
- **Step 3, planned relations to a ghost container.** `groma add relation toolbox-reader toolbox-ui` (actor to a drafted container) is accepted as a current authored row before the container has code; the skill does not say whether that is intended or whether it should be a draft row.

## Worked well

- `groma edit evals-container --id evals-cli …` renamed and described in one call, printing exactly what moved.
- Drafting every ghost and planned relation up front, then `groma scan && groma lint`, gave a clean lint with 43 relationships before any code existed.
