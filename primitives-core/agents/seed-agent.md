---
name: seed-agent
description: Harness seed agent that exercises the type:agent assembly path (roster -> plugin agents/ tree). A fixture-scale placeholder proving the marketplace assembler ships agent members; replaced when the first real agent primitive lands.
---

# Seed agent

This is a minimal, identity-neutral agent primitive whose only job is to exercise the
`type: agent` assembly path in `scripts/gen_marketplace.py` — it is copied verbatim from
`primitives-core/agents/seed-agent.md` into `plugins/<bundle>/agents/seed-agent.md`, the same
way skill and hook members are assembled into their bundle trees.

It carries no real workflow behavior. It exists so the roster ↔ generated-tree drift guard has
an agent member to bind, and is expected to be removed once a real agent member ships.
