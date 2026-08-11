---
id: TASK-064
title: Three gaps the first mcp primitive exposed in the gates
status: To Do
assignee: []
created_date: '2026-08-11 08:33'
labels:
  - gates
dependencies: []
priority: medium
type: bug
ordinal: 43000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
Adding the roster's first mcp-type primitive (TASK-061) surfaced three places where the gates are narrower than the roster's own type vocabulary. None blocked that work; all three are silent when they bite, which is why they are worth a card rather than a note.

1. gen_opencode.py would SILENTLY DROP an mcp entry that targets opencode. translation.yaml already carries a 'type: mcp -> treatment: render' row, and the type passes the ptype filter, but build() only has branches for skill and agent. A render-treated mcp entry reaching that point is shipped as neither and recorded as neither - it just vanishes. No subject exists today because the one rostered mcp entry targets claude-code, so a test would have to build the fixture. The script's own comment says every roster type reaches treatment_for() so that an absent type is never a silent skip; render is the case where that promise does not hold.

2. check_catalog.py's Contents vocabulary is closed at skill|agent|hook|command, and its counts derive from plugins/<id>/{skills,agents,hooks,commands}/. An mcp primitive is a .mcp.json at the plugin root, so a plugin shipping an MCP server cannot say so in the catalog. kaneo's row currently omits it and mentions the server in the prose cell instead, which is correct per the gate's stated contract but under-reports a shipped surface.

3. check_plugin_diagrams.py MISCOUNTS NODES when a dotted edge carries an inline label. _node_ids() blanks bracket labels and pipe labels, but the '-.text.->' form is neither, so every word of the label counts as a node id. Measured on the kaneo README: an 11-node diagram was reported as 31 and then 26, and only passed after rewriting every dotted edge to the '-.->|label|' form. Both forms are valid Mermaid. The failure mode is a false positive on the ceiling check, which is loud rather than silent - but it pushes an author toward rewriting a correct diagram to appease the parser, which is the wrong pressure.
<!-- SECTION:DESCRIPTION:END -->

## Acceptance Criteria
<!-- AC:BEGIN -->
- [ ] #1 A roster mcp entry targeting opencode either renders into the lane fragment or is recorded as an explicit exclusion - never dropped without a trace - and a test proves it by building the fixture
- [ ] #2 A plugin shipping an MCP server can declare it in the README catalog Contents cell, with the count derived from the assembly on disk like every other unit
- [ ] #3 check_plugin_diagrams.py counts a dotted edge with an inline label the same as the pipe form; a fixture diagram using '-.label.->' proves the count matches the pipe-form equivalent
- [ ] #4 make ci exits 0
<!-- AC:END -->
