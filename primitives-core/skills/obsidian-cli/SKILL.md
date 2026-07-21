---
name: obsidian-cli
description: This skill should be used when the user asks about "obsidian cli", "command line interface for obsidian", "automate obsidian", "script obsidian vault", "obsidian terminal commands", or wants to interact with their Obsidian vault from the command line for automation, scripting, or integration purposes.
---

# Obsidian CLI

Comprehensive guidance for using the official Obsidian CLI (v1.12+) to interact with vaults, manage files, execute commands, and automate workflows from the terminal.

## Overview

The Obsidian CLI allows you to:
- Open, create, read, and modify notes from the command line
- Execute Obsidian commands and manage plugins
- Query vault metadata, tags, links, and properties
- Automate daily notes, templates, and bookmarks
- Search content and manage file structure
- Integrate Obsidian with scripts and external tools

**Prerequisite:** the Obsidian desktop app must be installed (download from
obsidian.md). The CLI is the app binary itself — resolve it per platform:

| Platform | Binary |
| --- | --- |
| macOS | `/Applications/Obsidian.app/Contents/MacOS/Obsidian` |
| Linux | `obsidian` on PATH (or the AppImage/flatpak binary) |
| Windows | `%LOCALAPPDATA%\Obsidian\Obsidian.exe` |

**CLI Access:** `<obsidian-binary> <command>` — examples below use an `obsidian` alias.

For convenience, create a shell alias (adjust the path per the table above):
```bash
# Add to ~/.zshrc or ~/.bashrc
alias obsidian="/Applications/Obsidian.app/Contents/MacOS/Obsidian"
```

## Core Concepts

### Vault Targeting

Specify which vault to operate on:

```bash
# Use default vault
obsidian <command>

# Target specific vault
obsidian vault=MyVault <command>

# Get vault info
obsidian vault
obsidian vaults           # List all known vaults
```

**Best practice:** Set up scripts with explicit `vault=` parameter for reliability.

### File Targeting

Most commands support flexible file targeting:

```bash
# By file name (searches vault)
obsidian read file=MyNote

# By explicit path
obsidian read path=folder/subfolder/note.md

# Current/active file (omit both)
obsidian read
```

### Output Formats

Many commands support multiple output formats:

```bash
# Human-readable (default)
obsidian tags

# JSON for scripting
obsidian tags format=json

# CSV/TSV for data processing
obsidian base:query format=csv
```

## Essential Commands

### File Operations

**Create notes:**
```bash
# Basic creation
obsidian create name=MyNote

# With content
obsidian create name=MyNote content="# Hello World"

# In specific folder
obsidian create name=MyNote path=folder/note.md

# From template
obsidian create name=MyNote template=default

# Open in new tab after creating
obsidian create name=MyNote newtab

# Overwrite if exists
obsidian create name=MyNote overwrite
```

**Read notes:**
```bash
# Read file content
obsidian read file=MyNote

# Read specific file by path
obsidian read path=daily/2026-02-15.md
```

**Modify notes:**
```bash
# Append content
obsidian append file=MyNote content="Additional text"

# Prepend content
obsidian prepend file=MyNote content="Top matter"

# Append inline (no newline)
obsidian append file=MyNote content="inline text" inline
```

**Move/rename:**
```bash
# Rename file
obsidian move file=OldName to=NewName.md

# Move to folder
obsidian move file=MyNote to=archive/MyNote.md
```

**Delete:**
```bash
# Move to trash
obsidian delete file=MyNote

# Permanent deletion
obsidian delete file=MyNote permanent
```

### Daily Notes

**Daily note commands:**
```bash
# Open today's daily note
obsidian daily

# Open in new tab
obsidian daily newtab

# Open in split pane
obsidian daily paneType=split

# Read daily note content
obsidian daily:read

# Append to daily note
obsidian daily:append content="- Meeting notes"

# Prepend to daily note
obsidian daily:prepend content="# Top of note"
```

### Search & Discovery

**Text search:**
```bash
# Basic search
obsidian search query="important topic"

# Case-sensitive search
obsidian search query="Exact Match" case

# Limit results
obsidian search query="keyword" limit=10

# Search in folder
obsidian search query="term" path=projects

# Show match counts
obsidian search query="term" matches

# JSON output for scripting
obsidian search query="term" format=json
```

**List files:**
```bash
# All files
obsidian files

# In specific folder
obsidian files folder=projects

# Filter by extension
obsidian files ext=md

# Get total count
obsidian files total
```

**Random note:**
```bash
# Open random note
obsidian random

# From specific folder
obsidian random folder=ideas

# Read content (don't open)
obsidian random:read
```

### Links & Backlinks

**Analyze links:**
```bash
# Outgoing links from file
obsidian links file=MyNote

# Backlinks to file
obsidian backlinks file=MyNote

# Backlink counts
obsidian backlinks file=MyNote counts

# Orphaned files (no incoming links)
obsidian orphans

# Dead-end files (no outgoing links)
obsidian deadends

# Unresolved links
obsidian unresolved
```

### Tags & Properties

**Tag management:**
```bash
# List all tags
obsidian tags

# Tags in specific file
obsidian tags file=MyNote

# Tag usage counts
obsidian tags counts

# Sort by usage
obsidian tags sort=count

# Get specific tag info
obsidian tag name=project
```

**Properties (frontmatter):**
```bash
# List all properties
obsidian properties

# Properties in file
obsidian properties file=MyNote

# Read property value
obsidian property:read name=status file=MyNote

# Set property
obsidian property:set name=status value=done file=MyNote

# Set with type
obsidian property:set name=due value=2026-12-31 type=date file=MyNote

# Remove property
obsidian property:remove name=draft file=MyNote
```

### Plugin Management

**Plugin operations:**
```bash
# List all plugins
obsidian plugins

# Only community plugins
obsidian plugins filter=community

# Only enabled plugins
obsidian plugins:enabled

# Get plugin info
obsidian plugin id=dataview

# Enable plugin
obsidian plugin:enable id=dataview

# Disable plugin
obsidian plugin:disable id=dataview

# Install community plugin
obsidian plugin:install id=dataview

# Install and enable
obsidian plugin:install id=dataview enable

# Uninstall plugin
obsidian plugin:uninstall id=dataview

# Reload plugin (development)
obsidian plugin:reload id=my-plugin
```

### Command Execution

**Run Obsidian commands:**
```bash
# List all commands
obsidian commands

# Filter by prefix
obsidian commands filter=editor

# Execute command
obsidian command id=app:open-settings

# Common command IDs:
# - app:open-settings
# - app:reload
# - editor:toggle-bold
# - workspace:split-vertical
```

**Hotkeys:**
```bash
# List all hotkeys
obsidian hotkeys

# Get hotkey for command
obsidian hotkey id=app:open-vault
```

### Templates

**Template operations:**
```bash
# List templates
obsidian templates

# Read template
obsidian template:read name=meeting

# Read with variables resolved
obsidian template:read name=meeting resolve title="Team Sync"

# Insert template into active file
obsidian template:insert name=meeting
```

## Advanced Features

### Dataview Bases

Query Dataview database views:

```bash
# List all base files
obsidian bases

# List views in base
obsidian base:views file=Projects

# Query base
obsidian base:query file=Projects view=Active

# Different output formats
obsidian base:query file=Projects format=json
obsidian base:query file=Projects format=csv

# Create entry in base
obsidian base:create name="New Item" content="Description"
```

### Bookmarks

**Bookmark management:**
```bash
# List bookmarks
obsidian bookmarks

# Add file bookmark
obsidian bookmark file=MyNote

# Bookmark with heading
obsidian bookmark file=MyNote subpath="#Section"

# Bookmark folder
obsidian bookmark folder=projects

# Bookmark URL
obsidian bookmark url="https://example.com" title="Example"
```

### Tasks

**Task operations:**
```bash
# List all tasks
obsidian tasks

# Tasks in file
obsidian tasks file=MyNote

# Only incomplete tasks
obsidian tasks todo

# Only completed tasks
obsidian tasks done

# Toggle task status
obsidian task file=MyNote line=5 toggle

# Mark as done
obsidian task file=MyNote line=5 done
```

### Version History

**File history:**
```bash
# List versions
obsidian history file=MyNote

# Read specific version
obsidian history:read file=MyNote version=3

# Restore version
obsidian history:restore file=MyNote version=3

# Open recovery UI
obsidian history:open file=MyNote
```

**Sync history (if using Obsidian Sync):**
```bash
# Sync status
obsidian sync:status

# Pause/resume sync
obsidian sync off
obsidian sync on

# List sync versions
obsidian sync:history file=MyNote

# Read sync version
obsidian sync:read file=MyNote version=2

# Restore sync version
obsidian sync:restore file=MyNote version=2
```

## Scripting Patterns

### Shell Script Integration

**Daily note automation:**
```bash
#!/bin/bash
# Append daily standup template

STANDUP=$(cat <<EOF
## Standup $(date +%Y-%m-%d)

### Yesterday
-

### Today
-

### Blockers
-
EOF
)

obsidian daily:append content="$STANDUP"
```

**Batch file creation:**
```bash
#!/bin/bash
# Create project notes from list

while IFS= read -r project; do
  obsidian create \
    name="$project" \
    path="projects/$project.md" \
    template=project-template \
    silent
done < projects.txt
```

### JSON Processing

**Export tag statistics:**
```bash
#!/bin/bash
# Get tag counts as JSON and process with jq

obsidian tags counts format=json \
  | jq -r '.[] | "\(.count)\t\(.tag)"' \
  | sort -rn > tag-stats.tsv
```

**Find files by property:**
```bash
#!/bin/bash
# Find all files with status=in-progress

obsidian search query="status: in-progress" format=json \
  | jq -r '.[].path'
```

### Automation Examples

**Auto-archive completed tasks:**
```bash
#!/bin/bash
# Move files with all completed tasks to archive

for file in $(obsidian tasks done format=json | jq -r '.[] | .file' | sort -u); do
  # Check if file has any incomplete tasks
  incomplete=$(obsidian tasks todo file="$file" total 2>/dev/null | grep -o '[0-9]*')

  if [ "$incomplete" = "0" ]; then
    echo "Archiving $file (all tasks complete)"
    obsidian move file="$file" to="archive/$file"
  fi
done
```

**Sync external data:**
```bash
#!/bin/bash
# Fetch external data and update note

data=$(curl -s https://api.example.com/status)

obsidian append \
  file="API Status" \
  content="## $(date)
$data

---"
```

## Developer Features

### JavaScript Evaluation

```bash
# Execute JavaScript in Obsidian context
obsidian eval code="app.vault.getName()"

# Access app object
obsidian eval code="app.workspace.getActiveFile()?.path"
```

### Chrome DevTools Protocol

```bash
# Attach debugger
obsidian dev:debug on

# Query DOM
obsidian dev:dom selector=".workspace-leaf"

# Inspect CSS
obsidian dev:css selector=".markdown-preview-view"

# Console messages
obsidian dev:console

# Errors
obsidian dev:errors

# Screenshot
obsidian dev:screenshot path=screenshot.png
```

### Mobile Emulation

```bash
# Toggle mobile view
obsidian dev:mobile on
obsidian dev:mobile off
```

## Integration Patterns

### CI/CD Integration

**Automated testing:**
```bash
#!/bin/bash
# Verify vault structure in CI

obsidian vault=TestVault files folder=tests total
if [ $? -ne 0 ]; then
  echo "Vault test files missing"
  exit 1
fi
```

### External Tool Integration

**Export to static site:**
```bash
#!/bin/bash
# Export all markdown files with resolved templates

mkdir -p export

obsidian files ext=md format=json | jq -r '.[].path' | while read -r file; do
  content=$(obsidian read path="$file")
  echo "$content" > "export/$file"
done
```

### Alfred/Raycast Workflows

**Quick note creation:**
```bash
#!/bin/bash
# Create quick capture note (for Alfred/Raycast)

title="$1"
content="${2:-}"

obsidian create \
  name="$title" \
  path="inbox/$title.md" \
  content="$content" \
  newtab \
  silent
```

## Best Practices

### Performance

- Use `silent` flag to suppress UI updates for batch operations
- Leverage `format=json` for programmatic processing
- Use `total` flag when you only need counts
- Target specific folders with `folder=` to reduce search scope

### Error Handling

Always check command exit codes:

```bash
if ! obsidian create name=MyNote; then
  echo "Failed to create note"
  exit 1
fi
```

### Vault Safety

- Use `vault=` parameter explicitly in scripts
- Avoid `permanent` deletion in automated scripts
- Test scripts on test vaults first
- Keep backups before bulk operations

### Idempotency

Design scripts to be re-runnable:

```bash
# Check if note exists before creating
if obsidian file file=MyNote 2>/dev/null; then
  echo "Note already exists"
else
  obsidian create name=MyNote
fi
```

## Troubleshooting

### Common Issues

**Command not found:**
```bash
# Create alias in shell profile
alias obsidian="/Applications/Obsidian.app/Contents/MacOS/Obsidian"
```

**Vault not found:**
```bash
# List available vaults
obsidian vaults verbose

# Use full vault name
obsidian vault="My Vault" <command>
```

**File not found:**
```bash
# Use path instead of name
obsidian read path=folder/note.md

# List files to verify path
obsidian files
```

## Additional Resources

### Reference Files

For detailed command references:
- **`references/quick-reference.md`** - Fast lookup for common commands and patterns
- **`references/file-commands.md`** - Complete file operation commands
- **`references/setup-guide.md`** - Setup and quick start (v1.12+)

### Examples

Working examples in `examples/`:
- **`daily-automation.sh`** - Daily note workflows
- **`vault-reports.sh`** - Generate vault statistics

### Official Documentation

- [Obsidian CLI Help](https://help.obsidian.md/cli)
- [Obsidian Changelog](https://obsidian.md/changelog/)

## Next Steps

After mastering the CLI:
1. Integrate with other skills using MCP servers (`obsidian-mcp-server`)
2. Build plugin automation with `obsidian-api-basics`
3. Create vault workflows with template scripts
