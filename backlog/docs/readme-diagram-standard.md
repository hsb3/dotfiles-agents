# The plugin-README diagram standard — one visual per plugin, and what it must show

_Authoring rule. Provenance: backlog task-51 (owner request 2026-08-07 — "at least one
visual per plugin README so it's easier to understand what the plugin does"). Enforced by
`scripts/check_plugin_diagrams.py`, wired into `make check`._

## The problem it solves

A "What you get" table names the pieces one at a time. It cannot show what makes each piece
fire, in what order, or what comes out — so a reader deciding whether to install has to
assemble the relationships in their own head. Every plugin README therefore carries a
diagram that draws exactly the thing the table cannot.

## Format: inline Mermaid, never a rendered asset

A fenced ` ```mermaid ` block in the README itself. No `.svg`, no `.png`, no `.mmd` source.

- **[ADR 0017](../decisions/0017-pointer-based-marketplace.md) forbids tracked generated
  artifacts.** A committed SVG rendered from a diagram source is precisely that, and it
  would need a regen step nobody would run.
- Mermaid renders natively on GitHub, which is the surface these READMEs are read on — both
  the `dev` tree and the published `main` branch.
- It diffs like code, so a diagram that goes stale surfaces in review rather than rotting.

The cost, stated plainly: the terminal plugin browser shows the fence as text rather than a
picture. GitHub is the reading surface; the fence stays legible either way.

## Placement: one canonical slot

Heading `## How it fits together`, after the lede paragraph and immediately before the first
section that enumerates the pieces (`## What you get`, or whatever that plugin calls it).

The diagram answers "how do these relate" *before* the table answers "what is each one".
Putting it after the table is too late — the reader has already done the assembly work.

## The content rule

> **Draw the trigger and the flow, never the inventory.** A diagram must answer: what makes
> each piece fire, in what order, and what comes out. If the arrows can be deleted without
> losing anything, it is the wrong diagram — it is the table again, drawn.

A box per skill with no meaningful edges fails this rule no matter how tidy it looks.

Two shapes cover the collection:

| Shape | Fits | Draw |
|---|---|---|
| **Lifecycle** | pieces that fire at points along a loop | The loop itself, with each primitive hung off the moment it fires. Dashed edges for "this guard watches that step". |
| **Router** | a menu of independent skills over one domain | The *selection*. Edge labels are the question that routes you; nodes are the skill that answers it. Selection is the real user problem for a grab-bag. |

When a plugin has too many members to draw (an aggregate), do not draw a subset and do not
fan out its table headings. Draw the **rule that governs membership** instead — that is what
a reader cannot infer from the list.

## Constraints

- The `mermaid` skill's **house rule** applies: no `( ) { } [ ] # ; " < > &` inside any node
  or edge label, and no Mermaid reserved word (`end`, `class`, `subgraph`, `state`, `click`,
  `graph`, `style`) as a bare node id. Give the node its own id and keep the real word as
  the label — `load --> fin[end]`, never `load --> end`.

  Not every character in that set breaks every renderer today (`&` currently renders fine).
  The rule is deliberately wider than one renderer's present tolerance so that GitHub, IDE
  previews, and mermaid-cli all agree; the skill's position is to avoid the characters
  rather than paper over them with quoted labels or HTML entities.
- **No hardcoded colors.** No `style ... fill:` or `classDef ... fill:`. Hardcoded light
  fills go invisible on dark GitHub.
- **Node budget:** aim for 15 or fewer; the gate refuses above 20. Past that it has become a
  second table.
- Every node that names a primitive uses that primitive's **exact id**, and that primitive
  must actually be a member of the plugin whose README it is in.
- The plugin READMEs ship to users, so they are in `scripts/check_identity.py`'s scope:
  no name, org, repo, issue number, or machine-tied path in a diagram.

## Proving one

**A malformed diagram fails silently on GitHub** — it renders blank, and reading the source
will not tell you. A render pass is the only real check.

**`mermaid-cli` exits 0 when the render fails.** Measured 2026-08-07: a `(` in a node label
and `load --> end` each produced no file at all, and the process still reported success.
Checking `$?` will tell you everything is fine. Assert on the **output file** instead:

```sh
npx -y @mermaid-js/mermaid-cli -i diagram.mmd -o /tmp/out.svg
test -s /tmp/out.svg || echo "FAILED to render"
```

Stronger still, and worth it for a diagram going to consumers: confirm every label survived
into the SVG, since a partial render is also possible. Never conclude a diagram is correct
by reading it.

## What the gate checks

`scripts/check_plugin_diagrams.py` (in `make check`, therefore in `make ci`):

1. **Presence** — every `plugins/<id>/README.md` carries at least one mermaid fence.
2. **House rule** — no banned character in any node or edge label.
3. **Reserved word as a bare node id** — caught by adjacency to an arrow, so a legitimate
   `end` closing a subgraph is left alone.
4. **Theme safety** — no hardcoded fill color.
5. **Node ceiling** — at most 20 nodes per fence.
6. **No ghost primitives** — every node label naming a known primitive names one this plugin
   actually ships. This is the check that earns the script's keep: a renamed or retired
   primitive leaving a stale node in a picture nobody re-read is the `foreman`→`atelier`
   class of bug, and no other gate looks at diagram bodies.

The gate is stdlib-only, so it does **not** render anything — checks 2 and 3 are static
stand-ins for the render pass, not a replacement for it.

The gate does not judge whether a diagram is *good*. "Draw the trigger and the flow, never
the inventory" is a human call at review time — a tidy, well-formed diagram that is just the
table redrawn passes every one of these five checks.
