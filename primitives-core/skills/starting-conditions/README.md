# starting-conditions

Set a project's starting conditions before the code exists: what is being built, in what
language, and which quality rules a machine will refuse to let through. It interviews you
first and writes second, ending in a `RULES.md` contract, one gate command that proves the
contract, and a measured baseline of what that gate says about the tree today.

## When it triggers

Reach for it on "set this up properly", "define done", "what gates should this repo have",
"write me a RULES.md", or "how do I keep agents from making a mess in this repo". It fits
an existing repo too, when the quality conventions live only in someone's head and every
review re-litigates them.

Not for repo layout standards (`repo-meta-structure`) or for filling in missing
meta-structure (`mise-en-place-scaffold`). Building the rig the contract calls for is
handed to the `rig-builder` agent, which ships in the same bundle.

## Install

```
claude plugin install code-desk@dotfiles-agents
```
