# atelier parity — the Claude Code side

Atelier ships from two repos, one per harness: this one for Claude Code, and
`dotfiles-agents-oc` for opencode. **The doctrine prose is one text with two copies**, peers
rather than upstream-and-fork.

**The canonical contract is `docs/atelier-parity.md` in `dotfiles-agents-oc`.** This file is
the pointer, so that the next author editing atelier here knows the other copy exists.

## The transform, in four lines

- **Frontmatter is harness-owned** and not compared — each repo's own gates own its shape.
  That includes `description`, so a description change has to be carried across by hand. Both
  harnesses' descriptions carry model-tier advice, each in its own vocabulary — this side names
  the per-dispatch override, the other names the workload band its fixed `tier:` is set for — so
  the exclusion is a real hole, not an empty one.
- **opencode namespaces every artifact `atelier-<name>`**; here the name is bare, or
  plugin-qualified as `atelier:<name>`. The normalizer deletes `atelier-` or `atelier:`
  wherever it immediately precedes a roster name.
- **Harness-specific passages live in tagged blocks** —
  `<!-- harness:claude-code -->` … `<!-- /harness -->` and the `harness:opencode` twin,
  markers on their own lines. The normalizer strips the whole block from both sides. A file
  may only carry blocks tagged for its own harness, and there is no silent substitution
  table: a sentence naming a tool, path, or capability only one harness has goes in a block.
- **Whitespace and line wrapping are not compared.** Reflowing a paragraph is free; changing
  a word is not.

## The check does not run in this repo's CI

Parity is enforced by `bun gate/parity.ts` in `dotfiles-agents-oc`, which reads this
checkout from `$ATELIER_CC_REPO` — falling back to the first of `~/Developer/_hsb3/dotfiles-agents`
and `~/Developer/dotfiles-agents` that exists — and fails loudly when the sibling is missing.

It cannot run here. GitHub CI has no sibling checkout, and this repo tracks nothing generated
(ADR 0017), so there is no Claude-Code-side copy for CI to compare against. **A doctrine
change landed only in this repo goes undetected until someone runs that gate.**

## The rule

A doctrine change lands in **both** repos in the same wave. There is no "port it later" — the
gate is the only thing standing between one text and two, and the port that gets deferred is
the drift discovered a year later as a merge conflict of ideas.

Derive a parity card from the PR's full changed-file list, including deletions and renames,
not its title or headline file. Account for each shared artifact and each deliberately
one-sided change before declaring the paired wave complete.

## Deliberately one-sided

| Artifact | Side | Why |
|---|---|---|
| `agents/strategist.md` | opencode only | It is `mode: primary`, the session's own agent. A Claude Code plugin ships subagents only, so there is no surface to register it against — the position this repo already states at `primitives-core/agents/README.md:6-8`. |
| `commands/handoff.md` | opencode only | Here a command **silently replaces** a same-named skill in the same plugin (`primitives-core/commands/README.md:17-27`), and atelier ships a `handoff` skill. That is also why the command is named `activate`, not `activation`. |
| `skills/delegation/references/model-tiers.md`, `tier-cutoff-log.md` | opencode only | opencode has no per-dispatch model override: tiers are fixed in agent frontmatter, so a reference table and a measured cutoff log are the only knobs. This harness overrides the model per call and needs neither. |
| `primitives-core/**/README.md` | Claude Code only | The per-primitive provenance convention, read by the roster guard. opencode has no equivalent and should not grow one. |
| `skills/activation/scripts/`, `skills/activation/examples/` | Claude Code only | The auditor imports this harness's Python hook modules; opencode's hooks are TypeScript and its copy is an independent parser. The policy template is shared across native and `.agents` placement. |
| `skills/delegation/scripts/` | Claude Code only | Python, like every other skill-owned helper here; the port's tooling is TypeScript and would write its own. The doctrine the helper serves is neutral and IS shared — only the invocation sits in a `harness:claude-code` block. Like the activation scripts, this row is documentation and not an allow-list entry: `artifacts()` in the gate emits `agents/*.md`, `commands/*.md`, `skills/*/SKILL.md` and `skills/*/references/**.md`, so a `scripts/` path can never reach a comparison. |
| the `protected-branches:` activation key | Claude Code only | Read by one hook that exists only here, `worker-git-scope-guard`. opencode's activation parser reads `enforce`, `protected`, `isolate`, `worktreeBaseRef` and `handoff` and nothing else (`plugins/atelier/activation.ts` in `dotfiles-agents-oc`), and that bundle ships no guard on a worker's git at all, so the key would be read by nobody there. Do not confuse it with `protected:`, config-custody's file globs, which **is** shared. Being one-sided, its doctrine prose lives in a `harness:claude-code` block, never in neutral text. |

Atelier's primitives are rostered `targets: [claude-code]` for the same reason:
`scripts/gen_opencode.py` no longer emits them, because a generated second copy would compete
with the hand-authored one.
