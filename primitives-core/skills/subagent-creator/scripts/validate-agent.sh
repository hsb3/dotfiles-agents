#!/bin/bash
# Validates Claude Code sub-agent YAML structure and required fields

AGENT_FILE="$1"

if [ -z "$AGENT_FILE" ]; then
  echo "Usage: validate-agent.sh <agent-file.md>"
  exit 1
fi

if [ ! -f "$AGENT_FILE" ]; then
  echo "Error: File not found: $AGENT_FILE"
  exit 1
fi

# Check for YAML frontmatter
if ! head -1 "$AGENT_FILE" | grep -q "^---"; then
  echo "✗ Missing YAML frontmatter start (---)"
  exit 1
fi

# Extract frontmatter
FRONTMATTER=$(sed -n '/^---$/,/^---$/p' "$AGENT_FILE" | head -n -1 | tail -n +2)

# Check required fields
if ! echo "$FRONTMATTER" | grep -q "^name:"; then
  echo "✗ Missing required field 'name'"
  exit 1
fi

if ! echo "$FRONTMATTER" | grep -q "^description:"; then
  echo "✗ Missing required field 'description'"
  exit 1
fi

# Validate name format (lowercase, hyphens, numbers only)
NAME=$(echo "$FRONTMATTER" | grep "^name:" | sed 's/name: *//')
if ! echo "$NAME" | grep -qE "^[a-z0-9-]+$"; then
  echo "✗ Invalid name format: $NAME"
  echo "  Name must use lowercase letters, numbers, and hyphens only"
  exit 1
fi

# Check filename matches name
FILENAME=$(basename "$AGENT_FILE" .md)
if [ "$FILENAME" != "$NAME" ]; then
  echo "⚠ Warning: Filename ($FILENAME) doesn't match name field ($NAME)"
fi

# Success
echo "✓ Agent file is valid"
echo "  Name: $NAME"
echo "  File: $AGENT_FILE"
exit 0
