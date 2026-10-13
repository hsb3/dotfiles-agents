# SOP feedback

## Unclear, wrong or missing

- **Step 3 block, shell portability.** Factoring the shared ghost flags into a variable (`D="--parent … --draft v1"; groma draft component "X" $D …`) fails under zsh, the macOS default shell, because zsh does not word-split unquoted parameters: every call failed with `unknown option '--parent agent-harness-cli --draft v1 …'`. A shell function wrapping `groma draft component` worked. A note in the block that the flags must be repeated (or wrapped in a function) would save a round trip.
- **Step 3, a store whose natural ID equals a planned component's.** The spec names the ledger both as a data store (`results.jsonl`) and as the thing a `ledger.ts` component writes. Declaring the store as `Ledger` took the ID `ledger`, which the ghost (and the scanner's file-stem match) needs. Nothing in the skill warns that store and component IDs share one namespace; I renamed the store with `groma edit ledger --id results-ledger` before drafting the ghost. Suggest: "name data stores so their kebab ID differs from every planned file stem".
- **Step 4, task dependencies vs. shared types.** Several adapters implement one interface owned by a registry component. The SOP's "one task per independently reviewable slice" plus `--dep` leaves open where a shared type goes when the type's owner is built in a later task than its first user; I folded the registry and the first adapter into one task. A sentence on that (build the interface owner first, or together with its first implementer) would help.
- **Scaffold vs. spec.** The init scaffold had `typescript` under `peerDependencies`, while the spec's Stack section wants it as an exact devDependency. The skills do not say whether to treat scaffold drift as in scope for the first task; I fixed it in TASK-1 and noted it there.

## Worked well

- The first scan was instant and the `--id` rename of the scanned container kept everything (`replaced:` line made it obvious nothing was lost).
- `groma draft relation` for every planned link, including to externals and declared stores by ID, made the planned map complete before any code existed; `groma lint` was clean straight after planning.
- The PostToolUse hook recording file-tool edits on the In Progress task removes most of the `--modified-file` bookkeeping; a small `git diff`-based script covers shell-written files before finishing.
