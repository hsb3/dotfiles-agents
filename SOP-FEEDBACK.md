# SOP feedback

## Unclear, wrong or missing

- **Step 3, actor-to-ghost relations.** The block shows actor relations only to the scanned container (`groma add relation <actor> <bin>-cli`). A scenario such as "the maintainer opens the preview in a browser" needs an actor to reach a planned component (`server`). `groma draft relation maintainer server --draft v1` works, but it tags the *actor* with `draft: v1`, which the SOP never mentions; step 6 has to clear that tag too, and nothing says how.
- **Step 3, externals that the unit never contacts.** The spec lists GitHub's content hosts and jsDelivr as systems the output *points at* but the CLI never calls. The SOP's guidance ("an external for every outside system a request leaves for") does not cover a system that only appears in generated links; I modelled them as relations from the component that writes the URL, with technology "URL, never contacted", plus reader-side relations.
- **Step 5, `expect(...).rejects` without `await`.** Not an SOP issue as such, but the stack notes could warn that `bun test` passes an un-awaited `rejects` assertion silently.

## Worked well

- The first scan of the TypeScript skeleton took well under a second and named the container after the `bin` (`site`), exactly as the stack notes say; `--id site-cli` in the same edit as the meaning flags worked first time.
- `groma lint`'s duplicate-logic gate caught two near-identical validators in the first task; the extraction it pushed towards was an improvement.
