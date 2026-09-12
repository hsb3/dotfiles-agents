# Development workflows

Use this page to choose a current marketplace plugin for the work at hand. Read the
linked plugin guide before relying on its skills, hooks, agents, or integrations; source
presence alone does not establish installation, authentication, or runtime availability.

## Choose a workflow

| Stage | Current marketplace plugin(s) | Choose them when |
| --- | --- | --- |
| Start a project | [code-desk](../plugins/code-desk/README.md), [mise-en-place](../plugins/mise-en-place/README.md), [solo-skills](../plugins/solo-skills/README.md) | Use code-desk to establish a quality contract and gate; use mise-en-place where the repository tree is the system of record; use solo-skills for independent repo setup and engineering guidance. |
| Plan and track | [board-desk](../plugins/board-desk/README.md), [mise-en-place](../plugins/mise-en-place/README.md), [atelier](../plugins/atelier/README.md) | Use board-desk to author and triage work items, mise-en-place for source-grounded plans over a tracker, and atelier when the plan needs a delegated wave. |
| Implement | [bun](../plugins/bun/README.md), [carbon](../plugins/carbon/README.md), [pocketbase](../plugins/pocketbase/README.md), [obsidian-toolkit](../plugins/obsidian-toolkit/README.md), [solo-skills](../plugins/solo-skills/README.md) | Choose the topical plugin for Bun projects, Carbon UI, PocketBase backends, or Obsidian development; use solo-skills for standalone API, TUI, or engineering work. |
| Review and test | [code-desk](../plugins/code-desk/README.md), [atelier](../plugins/atelier/README.md), [pocketbase](../plugins/pocketbase/README.md), [solo-skills](../plugins/solo-skills/README.md) | Use code-desk for the quality contract and pull-request findings, atelier for a reviewed multi-agent cycle, pocketbase for backend design review, and solo-skills to assess whether tests actually prove behavior. |
| Documentation and visuals | [diagrams](../plugins/diagrams/README.md), [code-desk](../plugins/code-desk/README.md), [solo-skills](../plugins/solo-skills/README.md) | Use diagrams for structural diagrams, code-desk for README proof and presentations, and solo-skills for chart design. |
| Release | [code-desk](../plugins/code-desk/README.md) | Use its contract and pull-request-finding workflow before release. A project's own release runbook performs publication; no current marketplace plugin publishes arbitrary projects. |
| Report a plugin issue | [plugin-feedback](../plugins/plugin-feedback/README.md) | Draft a bug or feature report for this marketplace, review its destination and contents, and file only with explicit authorization. |
| Session continuity | [atelier](../plugins/atelier/README.md) | Use its activation and handoff guidance when a project needs durable continuation across sessions or delegated work. |

## Practical starts

### Start a project

1. Read [code-desk](../plugins/code-desk/README.md), then start with its
   <code>starting-conditions</code> skill to define the quality contract and gate.
2. If the repository tree is the system of record, read
   [mise-en-place](../plugins/mise-en-place/README.md) before applying its structure,
   audit, or scaffold workflow.

### Plan and track

1. Read [board-desk](../plugins/board-desk/README.md), then use <code>task-authoring</code>
   for executable work items and <code>board-triage</code> for a prioritization pass.
2. Read [mise-en-place](../plugins/mise-en-place/README.md) before using
   <code>planning-desk</code> for a source-grounded plan.
3. For a delegated wave, read [atelier](../plugins/atelier/README.md) and begin with
   <code>delegation</code>.

### Implement

1. Pick the topical guide: [bun](../plugins/bun/README.md),
   [carbon](../plugins/carbon/README.md), [pocketbase](../plugins/pocketbase/README.md),
   or [obsidian-toolkit](../plugins/obsidian-toolkit/README.md).
2. If no topical guide fits, read [solo-skills](../plugins/solo-skills/README.md) and
   select the independent skill whose documented trigger matches the work.

### Review and test

1. Read [code-desk](../plugins/code-desk/README.md) and apply the project contract before
   treating a check as sufficient; use its <code>pull-request</code> skill for review findings.
2. Use [solo-skills](../plugins/solo-skills/README.md)'s <code>test-quality</code> skill when
   adding or judging tests. For PocketBase design, read
   [pocketbase](../plugins/pocketbase/README.md) and use
   <code>pocketbase-best-practices</code>.
3. When the work is a multi-agent module cycle, follow
   [atelier](../plugins/atelier/README.md)'s <code>layer-cycle</code> guidance.

### Documentation and visuals

1. Read [diagrams](../plugins/diagrams/README.md) and choose its documented diagram
   format for structural relationships.
2. Read [code-desk](../plugins/code-desk/README.md) for README proof or presentations;
   read [solo-skills](../plugins/solo-skills/README.md) for data-visualization guidance.

### Release

1. Read [code-desk](../plugins/code-desk/README.md) and resolve contract or pull-request
   findings that affect the release.
2. Follow the consuming project's release runbook for publication and its required proof.

### Report a plugin issue

1. Read [plugin-feedback](../plugins/plugin-feedback/README.md) and use its reporter's
   <code>--draft</code> mode to prepare the report.
2. Check the destination and report contents, then obtain explicit authorization before filing.

### Session continuity

1. Read [atelier](../plugins/atelier/README.md), including its project activation setup,
   before enabling its workflow in a project.
2. Use <code>handoff</code> at a session boundary; use <code>compact-handoff</code> when its
   documented persistence and runtime conditions apply.

## Separate and upstream tools

These entries are recorded in [externals.yaml](../externals.yaml), not shipped as marketplace
plugins. Install or configure them separately when their own documentation calls for it.

| Tool | Status in this marketplace | Use alongside |
| --- | --- | --- |
| <code>kata</code> | Reference-only companion plugin | board-desk and mise-en-place tracker workflows |
| <code>langchain-skills</code> | Reference-only upstream plugin | LangChain, LangGraph, and Deep Agents work |
| <code>langsmith-skills</code> | Reference-only upstream plugin | LangSmith traces, datasets, and evaluators |
| <code>cmux</code> | Reference-only upstream skill set | A separately installed cmux environment |

<code>carbon-builder</code> is upstream-derived content inside the
[carbon](../plugins/carbon/README.md) plugin, whose hosted MCP access requires the documented
IBM-approved account and authentication. <code>pocketbase-best-practices</code> is
upstream-derived content inside the [pocketbase](../plugins/pocketbase/README.md) plugin.
Neither is a standalone marketplace plugin.
