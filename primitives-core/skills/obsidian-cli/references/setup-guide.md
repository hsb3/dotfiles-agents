# Obsidian CLI Setup Guide

Quick start guide for setting up and using the Obsidian CLI (v1.12+).

## Prerequisites

- **Obsidian Desktop** version 1.12.0 or later
- **macOS** system

## Installation

The Obsidian CLI is built into Obsidian Desktop 1.12+ — no separate installation required!

### Verify Installation

Check your Obsidian version:

```bash
/Applications/Obsidian.app/Contents/MacOS/Obsidian version
```

If you see a version number (1.12.0+), you're ready to go!

## Shell Alias Setup

Add to `~/.zshrc` (zsh) or `~/.bashrc` (bash):

```bash
# Obsidian CLI alias
alias obsidian="/Applications/Obsidian.app/Contents/MacOS/Obsidian"
```

Apply changes:
```bash
source ~/.zshrc  # or ~/.bashrc
```

## Verify Setup

Test the alias:

```bash
obsidian help
obsidian version
obsidian vaults
```

You should see Obsidian CLI output!

## First Commands

### List Your Vaults

```bash
obsidian vaults
```

This shows all known vaults with their names and paths.

### Set Default Vault Context

Most commands work on the currently active vault in Obsidian. To target a specific vault:

```bash
# Specify vault for single command
obsidian vault=MyVault files

# Or use an environment variable
export OBSIDIAN_VAULT="MyVault"
```

### Basic Operations

Try these essential commands:

```bash
# Show vault info
obsidian vault

# List files
obsidian files

# Search content
obsidian search query="important"

# Open daily note
obsidian daily

# Read a note
obsidian read file=MyNote
```

## Shell Completion (Optional)

### Zsh Completion

The CLI supports completions. To enable:

```bash
# Add to ~/.zshrc
eval "$(/Applications/Obsidian.app/Contents/MacOS/Obsidian __completions zsh)"
```

### Bash Completion

```bash
# Add to ~/.bashrc
eval "$(/Applications/Obsidian.app/Contents/MacOS/Obsidian __completions bash)"
```

After enabling, you can tab-complete commands and options!

## Configuration Tips

### Environment Variables

Set these for convenience:

```bash
# Default vault
export OBSIDIAN_VAULT="MyVault"

# CLI path (if not using alias)
export OBSIDIAN_CLI="/Applications/Obsidian.app/Contents/MacOS/Obsidian"
```

### Shell Functions

Create custom functions in your shell profile:

```bash
# Quick daily note append
dnote() {
  obsidian daily:append content="$*"
}

# Quick capture to inbox
capture() {
  obsidian create name="$(date +%Y%m%d-%H%M)-capture" path="inbox/$(date +%Y%m%d-%H%M)-capture.md" content="$*" newtab
}

# Search and open
so() {
  obsidian search query="$*"
  obsidian open file="$(obsidian search query="$*" | head -1 | sed 's/^- //')"
}
```

Usage:
```bash
dnote "Completed project review"
capture "Meeting idea: new feature"
so "project planning"
```

## Common Workflows

### Morning Routine

```bash
#!/bin/bash
# morning.sh - Start your day

obsidian daily
obsidian daily:prepend content="# $(date '+%A, %B %d, %Y')"
obsidian daily:append content="## Tasks
- [ ]

## Notes
"
```

### Quick Search & Edit

```bash
# search-edit.sh - Find and edit a note
#!/bin/bash

query="$1"

# Search for note
results=$(obsidian search query="$query" limit=5)

# Show results
echo "Search results:"
echo "$results"

# Get first result
file=$(echo "$results" | head -1 | sed 's/^- //')

# Open in editor
obsidian open file="$file" newtab
```

### Batch Export

```bash
# export.sh - Export all notes to directory
#!/bin/bash

export_dir="exports/$(date +%Y-%m-%d)"
mkdir -p "$export_dir"

obsidian files ext=md | sed 's/^- //' | while read -r file; do
  dir=$(dirname "$export_dir/$file")
  mkdir -p "$dir"
  obsidian read path="$file" > "$export_dir/$file"
done

echo "Exported to: $export_dir"
```

## Scripting Best Practices

### Error Handling

Always check command success:

```bash
if ! obsidian create name=MyNote; then
  echo "Failed to create note"
  exit 1
fi
```

### JSON Output

Use JSON for programmatic processing:

```bash
#!/bin/bash

# Get tags as JSON and process with jq
obsidian tags format=json | jq -r '.[] | .tag'

# Search with JSON output
obsidian search query="todo" format=json | jq -r '.[].path'
```

### Silent Operations

Use `silent` flag for batch operations:

```bash
# Batch create without notifications
for project in project1 project2 project3; do
  obsidian create name="$project" template=project silent
done
```

### Vault Safety

Always specify vault explicitly in automation:

```bash
#!/bin/bash

VAULT="MyVault"

obsidian vault="$VAULT" files
obsidian vault="$VAULT" create name=Note
```

## Troubleshooting

### Command Not Found

If `obsidian: command not found`:

1. Check Obsidian version: `1.12.0+` required
2. Verify path to Obsidian.app
3. Reload shell config: `source ~/.zshrc`
4. Use full path temporarily: `/Applications/Obsidian.app/Contents/MacOS/Obsidian help`

### Permission Denied

If you get permission errors:

```bash
# macOS: Grant Terminal full disk access
# System Settings → Privacy & Security → Full Disk Access → Add Terminal
```

### Vault Not Found

If "vault not found":

```bash
# List vaults to see correct name
obsidian vaults verbose

# Use exact vault name (case-sensitive)
obsidian vault="My Vault Name" files
```

### File Not Found

If file operations fail:

```bash
# Use path instead of name
obsidian read path=folder/note.md

# List files to verify path
obsidian files folder=folder
```

## Security Considerations

### Credentials

Never commit scripts with sensitive data:

```bash
# BAD: Hardcoded credentials
obsidian create content="API_KEY=secret123"

# GOOD: Use environment variables
obsidian create content="API_KEY=$API_KEY"
```

### Permanent Deletion

Be careful with `permanent` flag:

```bash
# Safe: Move to trash
obsidian delete file=OldNote

# Dangerous: Permanent deletion
obsidian delete file=OldNote permanent  # Cannot undo!
```

### Script Safety

Test destructive operations on test vaults first:

```bash
#!/bin/bash

# Use test vault for development
VAULT="TestVault"

# Test script here
obsidian vault="$VAULT" <commands>

# When ready, switch to production vault
# VAULT="ProductionVault"
```

## Next Steps

1. **Explore Commands:** Run `obsidian help` to see all available commands
2. **Read Documentation:** Check the SKILL.md for comprehensive command reference
3. **Try Examples:** Run the example scripts in `examples/` directory
4. **Build Workflows:** Create custom automation for your needs
5. **Integrate Tools:** Combine with other CLI tools (jq, fzf, etc.)

## Quick Reference

### Essential Commands

```bash
obsidian help                    # List all commands
obsidian vault                   # Vault info
obsidian vaults                  # List vaults
obsidian files                   # List files
obsidian search query="text"     # Search content
obsidian create name=Note        # Create note
obsidian read file=Note          # Read note
obsidian open file=Note          # Open note
obsidian daily                   # Open daily note
obsidian tags                    # List tags
obsidian tasks todo              # Incomplete tasks
```

### Useful Flags

```bash
vault=<name>      # Target specific vault
format=json       # JSON output
silent            # No UI notifications
newtab            # Open in new tab
total             # Show count only
```

## Resources

- [Obsidian CLI Official Docs](https://help.obsidian.md/cli)
- [Obsidian Changelog](https://obsidian.md/changelog/)
- [Example Scripts](../examples/)
- [Command Reference](./file-commands.md)
