---
name: subagent-creator
description: Creates well-structured Claude Code sub-agents with validated YAML configuration and clear system prompts. Use when designing new sub-agents, setting up project-specific specialized agents, need guidance on sub-agent architecture, or want to automate agent creation for specific tasks (code review, data engineering, debugging, analysis). Validates frontmatter, ensures proper naming, and provides templates for common agent patterns.
---

# Sub-Agent Creator

Create effective Claude Code sub-agents following official conventions.

## Agent File Structure

Markdown file with YAML frontmatter:

```markdown
---
name: agent-name                   # lowercase, hyphens only
description: |
  When to use this agent...
  Include trigger phrases...
tools: Read, Grep, Glob           # Optional
model: sonnet                      # Optional: sonnet|opus|haiku|inherit
permissionMode: acceptEdits        # Optional
---

# Agent Title

System prompt guiding behavior...
```

## Required Fields

**name**: Lowercase, hyphens, numbers only. Must match filename.

**description**: Critical for delegation. Include:
- What agent does
- When to use it
- Trigger phrases users would say
- Specific scenarios

Example:
```yaml
description: |
  Specializes in CMS data pipelines. Converts PDFs to markdown,
  creates JSON dictionaries, generates BigQuery ETL.
  Use when: processing CMS dataset, convert documentation, load to BigQuery.
  Triggers: "process CMS data", "create data dictionary"
```

## Storage Locations

**Project agents** (`.claude/agents/`):
- Share with team
- Commit to git
- Project-specific

**Personal agents** (`~/.claude/agents/`):
- All your projects
- Not in git

**Recommendation**: Use `.claude/agents/` for project-specific agents.

## Common Patterns

### Read-Only Analyst
```yaml
tools: Read, Grep, Glob, Bash
model: haiku
permissionMode: dontAsk
```

### Data Engineer
```yaml
tools: Read, Grep, Glob, Bash, Edit, Write
model: sonnet
permissionMode: acceptEdits
```

### Careful Reviewer
```yaml
tools: Read, Grep, Glob
model: inherit
permissionMode: default
```

## Creating an Agent

1. **Define responsibility**: One clear task
2. **Write description**: Include trigger phrases
3. **Choose tools**: Minimum needed
4. **Select model**: haiku (fast), sonnet (balanced), opus (complex)
5. **Set permissions**: Match work type
6. **Write system prompt**: Clear workflow and conventions
7. **Validate**: Use `scripts/validate-agent.sh`
8. **Save**: `.claude/agents/{name}.md`

## Validation

```bash
bash scripts/validate-agent.sh .claude/agents/my-agent.md
```

Checks:
- YAML frontmatter present
- Required fields exist
- Name format (lowercase, hyphens)
- Field values valid

## Templates

See `assets/templates/`:
- `data-engineer-template.md`
- `code-reviewer-template.md`
- `debugger-template.md`

Copy and customize.

## Example: CMS Data Engineer

Created agent at `.claude/agents/cms-data-engineer.md`:
- **Responsibility**: CMS dataset processing (PDF→markdown→JSON→ETL)
- **Tools**: Read, Grep, Glob, Bash, Edit, Write
- **Model**: sonnet
- **Permission**: acceptEdits (generates code)
- **System prompt**: CMS conventions, naming rules, config precedence
- **Status**: ✅ Working (processed ACO County successfully)

## Quick Reference

| Aspect | Guideline |
|--------|-----------|
| Naming | lowercase-with-hyphens |
| Responsibility | One clear task |
| Description | Include trigger phrases |
| Tools | Minimum needed |
| Model | haiku (fast), sonnet (balanced), opus (complex) |
| Permissions | Match work type |
| Location | `.claude/agents/` for projects |

## Validation Script

Use `scripts/validate-agent.sh` to check agent files before use.
