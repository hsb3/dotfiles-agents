---
name: atelier-parity-gate-after-skill-edits
description: Any PR touching an atelier doctrine skill leaves the opencode peer repo silently red; run its parity gate as a coordinator step and port in the same wave
metadata:
  type: feedback
---

After any PR that edits `primitives-core/skills/{delegation,waves,layer-cycle,deletion-pass,handoff,rubric-panel}/`, run `bun gate/parity.ts` in `~/Developer/dotfiles-agents-oc` and port the drift before calling the wave done.

**Why:** the doctrine is one text with two copies (`docs/atelier-parity.md`), and the only gate lives in the other repo, so nothing here goes red. Measured 2026-09-06: two merged PRs (#464, #465) left nine files drifting and no manager brief had mentioned it; the port became a fifth chain after the wave was "done".

**How to apply:** when briefing a manager for atelier skill work, name the port as part of the definition of done, or reserve it as a coordinator step right after the merge. Descriptions are carried by hand too (frontmatter is not compared). Related: [[opencode-deferred-not-abandoned]].
