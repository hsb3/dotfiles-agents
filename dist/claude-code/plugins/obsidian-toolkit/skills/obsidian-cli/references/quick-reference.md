# Obsidian CLI Quick Reference

Fast lookup for common Obsidian CLI commands and patterns.

## Command Structure

```bash
obsidian [vault=<name>] <command> [options]
```

## File Operations

| Task | Command |
|------|---------|
| Create note | `obsidian create name=MyNote` |
| Create with content | `obsidian create name=Note content="# Title"` |
| Create from template | `obsidian create name=Note template=default` |
| Create in folder | `obsidian create path=folder/note.md` |
| Read note | `obsidian read file=MyNote` |
| Read by path | `obsidian read path=folder/note.md` |
| Append to note | `obsidian append file=Note content="Text"` |
| Prepend to note | `obsidian prepend file=Note content="Text"` |
| Move/rename note | `obsidian move file=Old to=New.md` |
| Delete note | `obsidian delete file=Note` |
| Delete permanently | `obsidian delete file=Note permanent` |
| Open note | `obsidian open file=Note` |
| Open in new tab | `obsidian open file=Note newtab` |

## Daily Notes

| Task | Command |
|------|---------|
| Open daily note | `obsidian daily` |
| Read daily | `obsidian daily:read` |
| Append to daily | `obsidian daily:append content="Text"` |
| Prepend to daily | `obsidian daily:prepend content="Text"` |
| Open in new tab | `obsidian daily newtab` |

## Search & Discovery

| Task | Command |
|------|---------|
| Search text | `obsidian search query="keyword"` |
| Case-sensitive | `obsidian search query="Word" case` |
| Search in folder | `obsidian search query="text" path=folder` |
| Limit results | `obsidian search query="text" limit=10` |
| JSON output | `obsidian search query="text" format=json` |
| List files | `obsidian files` |
| Files in folder | `obsidian files folder=projects` |
| Filter by extension | `obsidian files ext=md` |
| Count files | `obsidian files total` |
| List folders | `obsidian folders` |
| Random note | `obsidian random` |
| Random from folder | `obsidian random folder=ideas` |

## Links & Backlinks

| Task | Command |
|------|---------|
| Outgoing links | `obsidian links file=Note` |
| Backlinks | `obsidian backlinks file=Note` |
| Backlink counts | `obsidian backlinks file=Note counts` |
| Orphaned files | `obsidian orphans` |
| Dead-end files | `obsidian deadends` |
| Unresolved links | `obsidian unresolved` |

## Tags

| Task | Command |
|------|---------|
| List all tags | `obsidian tags` |
| Tags in file | `obsidian tags file=Note` |
| Tag counts | `obsidian tags counts` |
| Sort by usage | `obsidian tags sort=count` |
| Get tag info | `obsidian tag name=project` |
| Total tags | `obsidian tags total` |

## Properties (Frontmatter)

| Task | Command |
|------|---------|
| List all properties | `obsidian properties` |
| Properties in file | `obsidian properties file=Note` |
| Read property | `obsidian property:read name=status file=Note` |
| Set property | `obsidian property:set name=status value=done file=Note` |
| Set with type | `obsidian property:set name=due value=2026-12-31 type=date` |
| Remove property | `obsidian property:remove name=draft file=Note` |

## Tasks

| Task | Command |
|------|---------|
| All tasks | `obsidian tasks all` |
| Incomplete tasks | `obsidian tasks todo` |
| Completed tasks | `obsidian tasks done` |
| Tasks in file | `obsidian tasks file=Note` |
| Task count | `obsidian tasks todo total` |
| Toggle task | `obsidian task file=Note line=5 toggle` |
| Mark as done | `obsidian task file=Note line=5 done` |

## Templates

| Task | Command |
|------|---------|
| List templates | `obsidian templates` |
| Read template | `obsidian template:read name=meeting` |
| Resolve variables | `obsidian template:read name=meeting resolve` |
| Insert template | `obsidian template:insert name=meeting` |

## Plugins

| Task | Command |
|------|---------|
| List all plugins | `obsidian plugins` |
| Community plugins | `obsidian plugins filter=community` |
| Enabled plugins | `obsidian plugins:enabled` |
| Get plugin info | `obsidian plugin id=dataview` |
| Enable plugin | `obsidian plugin:enable id=dataview` |
| Disable plugin | `obsidian plugin:disable id=dataview` |
| Install plugin | `obsidian plugin:install id=dataview` |
| Install & enable | `obsidian plugin:install id=dataview enable` |
| Uninstall plugin | `obsidian plugin:uninstall id=dataview` |
| Reload plugin | `obsidian plugin:reload id=my-plugin` |

## Commands

| Task | Command |
|------|---------|
| List commands | `obsidian commands` |
| Filter commands | `obsidian commands filter=editor` |
| Execute command | `obsidian command id=app:open-settings` |
| List hotkeys | `obsidian hotkeys` |
| Get hotkey | `obsidian hotkey id=app:open-vault` |

## Vault Info

| Task | Command |
|------|---------|
| Vault info | `obsidian vault` |
| Vault name | `obsidian vault info=name` |
| Vault path | `obsidian vault info=path` |
| File count | `obsidian vault info=files` |
| Folder count | `obsidian vault info=folders` |
| List vaults | `obsidian vaults` |
| Version info | `obsidian version` |

## Bookmarks

| Task | Command |
|------|---------|
| List bookmarks | `obsidian bookmarks` |
| Bookmark file | `obsidian bookmark file=Note` |
| Bookmark heading | `obsidian bookmark file=Note subpath="#Section"` |
| Bookmark folder | `obsidian bookmark folder=projects` |
| Bookmark URL | `obsidian bookmark url="https://example.com" title="Site"` |

## History & Versions

| Task | Command |
|------|---------|
| File history | `obsidian history file=Note` |
| Read version | `obsidian history:read file=Note version=3` |
| Restore version | `obsidian history:restore file=Note version=3` |
| Diff versions | `obsidian diff file=Note from=2 to=1` |

## Sync (Obsidian Sync)

| Task | Command |
|------|---------|
| Sync status | `obsidian sync:status` |
| Pause sync | `obsidian sync off` |
| Resume sync | `obsidian sync on` |
| Sync history | `obsidian sync:history file=Note` |
| Read sync version | `obsidian sync:read file=Note version=2` |
| Restore sync | `obsidian sync:restore file=Note version=2` |

## Metadata

| Task | Command |
|------|---------|
| List aliases | `obsidian aliases` |
| Aliases in file | `obsidian aliases file=Note` |
| File outline | `obsidian outline file=Note` |
| Outline as tree | `obsidian outline file=Note format=tree` |
| Outline as markdown | `obsidian outline file=Note format=md` |
| Word count | `obsidian wordcount file=Note` |
| Character count | `obsidian wordcount file=Note characters` |

## Dataview Bases

| Task | Command |
|------|---------|
| List bases | `obsidian bases` |
| List views | `obsidian base:views file=Projects` |
| Query base | `obsidian base:query file=Projects view=Active` |
| Query as JSON | `obsidian base:query file=Projects format=json` |
| Create entry | `obsidian base:create name="Item" content="Text"` |

## Developer

| Task | Command |
|------|---------|
| Eval JavaScript | `obsidian eval code="app.vault.getName()"` |
| Dev tools | `obsidian devtools` |
| Query DOM | `obsidian dev:dom selector=".workspace"` |
| Console logs | `obsidian dev:console` |
| Errors | `obsidian dev:errors` |
| Screenshot | `obsidian dev:screenshot path=shot.png` |
| Mobile mode | `obsidian dev:mobile on` |
| Attach debugger | `obsidian dev:debug on` |

## Common Flags

| Flag | Purpose |
|------|---------|
| `vault=<name>` | Target specific vault |
| `file=<name>` | Target file by name |
| `path=<path>` | Target file by path |
| `format=json` | Output as JSON |
| `format=csv` | Output as CSV |
| `format=tsv` | Output as TSV |
| `silent` | No UI notifications |
| `newtab` | Open in new tab |
| `total` | Show count only |
| `verbose` | Detailed output |
| `overwrite` | Replace existing |
| `permanent` | Skip trash |

## Scripting Patterns

### Basic Script Template

```bash
#!/bin/bash
set -e  # Exit on error

OBSIDIAN="/Applications/Obsidian.app/Contents/MacOS/Obsidian"
VAULT="MyVault"

run_obsidian() {
  $OBSIDIAN vault="$VAULT" "$@"
}

# Your commands here
run_obsidian files
```

### Error Handling

```bash
if ! obsidian create name=Note; then
  echo "Failed to create note"
  exit 1
fi
```

### JSON Processing

```bash
obsidian tags format=json | jq -r '.[] | .tag'
```

### Heredoc Content

```bash
content=$(cat <<'EOF'
# Multi-line
Content here
EOF
)

obsidian create name=Note content="$content"
```

### Loop Through Files

```bash
obsidian files ext=md | sed 's/^- //' | while read -r file; do
  # Process each file
  echo "Processing: $file"
done
```

### Conditional Operations

```bash
# Check if note exists
if obsidian file file=MyNote &>/dev/null; then
  echo "Note exists"
else
  echo "Note not found"
fi
```

## Common Use Cases

### Daily Capture
```bash
obsidian daily:append content="- $(date +%H:%M) $*"
```

### Quick Search
```bash
obsidian search query="$1" limit=5
```

### Batch Create
```bash
for name in Note1 Note2 Note3; do
  obsidian create name="$name" template=default silent
done
```

### Export to Directory
```bash
mkdir -p export
obsidian files ext=md | while read -r file; do
  obsidian read path="$file" > "export/$file"
done
```

### Tag Statistics
```bash
obsidian tags counts format=json | jq -r '.[] | "\(.count)\t\(.tag)"' | sort -rn
```

### Task Dashboard
```bash
echo "Incomplete: $(obsidian tasks todo total)"
echo "Completed: $(obsidian tasks done total)"
```

## Environment Variables

```bash
# Set in ~/.zshrc or ~/.bashrc
export OBSIDIAN_VAULT="MyVault"          # Default vault
export OBSIDIAN_CLI="/path/to/obsidian"  # CLI path
export EDITOR="vim"                       # Editor for --editor flag
```

## Shell Aliases

```bash
# Add to ~/.zshrc or ~/.bashrc
alias ob="obsidian"
alias obd="obsidian daily"
alias obf="obsidian files"
alias obs="obsidian search query="
alias obc="obsidian create name="
```

## Keyboard Shortcuts (with Alfred/Raycast)

Create quick launchers:

```bash
# Daily note
obsidian daily newtab

# Quick capture
obsidian create path="inbox/$(date +%Y%m%d-%H%M).md" content="$*" newtab

# Search and open
obsidian open file="$(obsidian search query="$*" | head -1 | sed 's/^- //')"
```
