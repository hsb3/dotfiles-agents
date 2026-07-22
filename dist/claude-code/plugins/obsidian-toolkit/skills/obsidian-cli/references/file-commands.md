# File Commands Reference

Complete reference for file operations in Obsidian CLI.

## File Information

### `file` - Get file metadata

**Syntax:**
```bash
obsidian file [file=<name>] [path=<path>]
```

**Returns:**
- File path
- Size
- Created/modified timestamps
- Extension

**Example:**
```bash
obsidian file file=MyNote
obsidian file path=projects/proposal.md
```

## File Listing

### `files` - List files in vault

**Syntax:**
```bash
obsidian files [folder=<path>] [ext=<extension>] [total]
```

**Options:**
- `folder=<path>` - List files in specific folder
- `ext=<extension>` - Filter by extension (e.g., `md`, `pdf`)
- `total` - Show only count

**Examples:**
```bash
# All markdown files
obsidian files

# Files in folder
obsidian files folder=projects

# PDFs only
obsidian files ext=pdf

# Count total files
obsidian files total
```

### `folders` - List folders

**Syntax:**
```bash
obsidian folders [folder=<path>] [total]
```

**Examples:**
```bash
# All folders
obsidian folders

# Subfolders of specific folder
obsidian folders folder=projects

# Count folders
obsidian folders total
```

### `folder` - Get folder info

**Syntax:**
```bash
obsidian folder path=<path> [info=files|folders|size]
```

**Examples:**
```bash
# File count in folder
obsidian folder path=projects info=files

# Subfolder count
obsidian folder path=projects info=folders

# Total size
obsidian folder path=projects info=size
```

## File Creation

### `create` - Create new file

**Syntax:**
```bash
obsidian create [name=<name>] [path=<path>] [content=<text>] [template=<name>] [overwrite] [silent] [newtab]
```

**Options:**
- `name=<name>` - File name (searches for unique location)
- `path=<path>` - Explicit path including filename
- `content=<text>` - Initial content
- `template=<name>` - Template to use
- `overwrite` - Replace existing file
- `silent` - Don't show notification
- `newtab` - Open in new tab after creation

**Examples:**
```bash
# Simple creation
obsidian create name=MyNote

# With initial content
obsidian create name=MyNote content="# Welcome"

# In specific folder
obsidian create path=inbox/capture.md content="Quick note"

# From template
obsidian create name=Meeting template=meeting-notes

# Overwrite existing
obsidian create name=Scratch overwrite silent

# Create and open
obsidian create name=Draft newtab
```

**Use cases:**
- **Quick capture:** Create inbox notes with content
- **Templated workflows:** Generate consistent note structures
- **Scripted generation:** Batch create project notes
- **Scratch pads:** Overwrite temporary working notes

## File Reading

### `read` - Read file contents

**Syntax:**
```bash
obsidian read [file=<name>] [path=<path>]
```

**Examples:**
```bash
# Read active file
obsidian read

# By name
obsidian read file=MyNote

# By path
obsidian read path=projects/proposal.md

# Redirect to file
obsidian read file=MyNote > copy.md

# Process with tools
obsidian read file=MyNote | grep "TODO"
```

**Use cases:**
- **Export content:** Pipe to external processors
- **Search/filter:** Use with grep, sed, awk
- **Backup:** Save specific note versions
- **Validation:** Check note content in scripts

## File Modification

### `append` - Append content

**Syntax:**
```bash
obsidian append [file=<name>] [path=<path>] content=<text> [inline]
```

**Options:**
- `content=<text>` - Text to append (required)
- `inline` - No newline before content

**Examples:**
```bash
# Append with newline
obsidian append file=MyNote content="New paragraph"

# Append inline (same line)
obsidian append file=MyNote content=" continued text" inline

# Multi-line append
obsidian append file=Log content="$(cat <<EOF
## New Section

Content here
EOF
)"

# Append to daily note
obsidian daily:append content="- Task completed at $(date)"
```

### `prepend` - Prepend content

**Syntax:**
```bash
obsidian prepend [file=<name>] [path=<path>] content=<text> [inline]
```

**Examples:**
```bash
# Add header
obsidian prepend file=MyNote content="# Title"

# Prepend timestamp
obsidian prepend file=Log content="[$(date '+%Y-%m-%d %H:%M')] " inline
```

**Use cases:**
- **Logging:** Add timestamped entries to top
- **Metadata:** Inject frontmatter or headers
- **Banners:** Add warning/info blocks
- **Chronological notes:** Most recent first

## File Movement

### `move` - Move or rename file

**Syntax:**
```bash
obsidian move [file=<name>] [path=<path>] to=<path>
```

**Options:**
- `to=<path>` - Destination path (required)

**Examples:**
```bash
# Rename file
obsidian move file=OldName to=NewName.md

# Move to folder
obsidian move file=MyNote to=archive/MyNote.md

# Move and rename
obsidian move file=Draft to=final/Complete.md

# Move from path
obsidian move path=inbox/capture.md to=processed/2026-02-15.md
```

**Behavior:**
- Updates all internal links automatically
- Preserves file content and metadata
- Creates destination folder if needed
- Fails if destination exists

**Use cases:**
- **Archiving:** Move completed notes
- **Organization:** Restructure vault
- **Renaming:** Update note names
- **Workflows:** Move through stages (inbox → processing → archive)

## File Deletion

### `delete` - Delete file

**Syntax:**
```bash
obsidian delete [file=<name>] [path=<path>] [permanent]
```

**Options:**
- `permanent` - Skip trash, delete immediately

**Examples:**
```bash
# Move to trash
obsidian delete file=OldNote

# Permanent deletion
obsidian delete file=Temp permanent

# Delete by path
obsidian delete path=scratch/temp.md permanent
```

**⚠️ Warning:**
- Default behavior moves to `.trash` folder
- `permanent` flag deletes immediately (cannot undo)
- Links to deleted files become unresolved
- No confirmation prompt

**Use cases:**
- **Cleanup scripts:** Remove generated temporary files
- **Maintenance:** Clear old files matching criteria
- **Testing:** Reset test vaults

**Best practices:**
```bash
# Safe deletion - confirm first
obsidian file file=OldNote
read -p "Delete this file? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
  obsidian delete file=OldNote
fi

# Permanent deletion - double check
obsidian read file=Temp > backup.md
obsidian delete file=Temp permanent
```

## File Opening

### `open` - Open file in Obsidian

**Syntax:**
```bash
obsidian open [file=<name>] [path=<path>] [newtab]
```

**Options:**
- `newtab` - Open in new tab (default: current tab)

**Examples:**
```bash
# Open in current tab
obsidian open file=MyNote

# Open in new tab
obsidian open file=MyNote newtab

# Open by path
obsidian open path=projects/proposal.md
```

## Recent Files

### `recents` - List recently opened files

**Syntax:**
```bash
obsidian recents [total]
```

**Examples:**
```bash
# Recent files
obsidian recents

# Count only
obsidian recents total
```

## Word Count

### `wordcount` - Count words and characters

**Syntax:**
```bash
obsidian wordcount [file=<name>] [path=<path>] [words] [characters]
```

**Options:**
- `words` - Show only word count
- `characters` - Show only character count

**Examples:**
```bash
# Both counts
obsidian wordcount file=MyNote

# Words only
obsidian wordcount file=MyNote words

# Characters only
obsidian wordcount file=MyNote characters

# Active file
obsidian wordcount
```

**Use cases:**
- **Writing goals:** Track progress
- **Reports:** Generate statistics
- **Validation:** Check minimum lengths
- **Analytics:** Vault-wide metrics

## File Outline

### `outline` - Show headings structure

**Syntax:**
```bash
obsidian outline [file=<name>] [path=<path>] [format=tree|md] [total]
```

**Options:**
- `format=tree` - Tree view (default)
- `format=md` - Markdown list
- `total` - Count headings only

**Examples:**
```bash
# Tree view
obsidian outline file=MyNote

# Markdown list
obsidian outline file=MyNote format=md

# Count headings
obsidian outline file=MyNote total
```

**Use cases:**
- **Navigation:** Quick TOC generation
- **Structure analysis:** Verify heading hierarchy
- **Export:** Generate table of contents
- **Validation:** Check heading levels

## Diff & Versions

### `diff` - Show differences between versions

**Syntax:**
```bash
obsidian diff [file=<name>] [path=<path>] [from=<n>] [to=<n>] [filter=local|sync]
```

**Options:**
- `from=<n>` - Source version number
- `to=<n>` - Target version number
- `filter=local` - Local history only
- `filter=sync` - Sync history only

**Examples:**
```bash
# List all versions
obsidian diff file=MyNote

# Compare versions
obsidian diff file=MyNote from=2 to=1

# Local history versions
obsidian diff file=MyNote filter=local
```

## Automation Examples

### Daily Backup Script

```bash
#!/bin/bash
# Backup all markdown files

backup_dir="backups/$(date +%Y-%m-%d)"
mkdir -p "$backup_dir"

obsidian files ext=md | while read -r file; do
  # Get file path
  path=$(echo "$file" | sed 's/^- //')

  # Create directory structure
  dir=$(dirname "$backup_dir/$path")
  mkdir -p "$dir"

  # Copy file
  obsidian read path="$path" > "$backup_dir/$path"
done
```

### Archive Old Files

```bash
#!/bin/bash
# Archive files not modified in 90 days

cutoff_date=$(date -v-90d +%s)

obsidian files | while read -r file; do
  # Get modification time
  mod_time=$(obsidian file file="$file" | grep Modified | cut -d: -f2)
  mod_epoch=$(date -j -f "%Y-%m-%d" "$mod_time" +%s)

  if [ "$mod_epoch" -lt "$cutoff_date" ]; then
    echo "Archiving old file: $file"
    obsidian move file="$file" to="archive/$file"
  fi
done
```

### Generate File Report

```bash
#!/bin/bash
# Generate vault file statistics report

report="vault-report-$(date +%Y-%m-%d).md"

cat > "$report" <<EOF
# Vault Report - $(date +%Y-%m-%d)

## Statistics

- **Total Files:** $(obsidian files total)
- **Total Folders:** $(obsidian folders total)
- **Markdown Files:** $(obsidian files ext=md total)
- **Orphaned Files:** $(obsidian orphans total)
- **Dead Ends:** $(obsidian deadends total)

## Recent Files

$(obsidian recents)

## Unresolved Links

$(obsidian unresolved total) unresolved links found.
EOF

echo "Report saved to $report"
```
