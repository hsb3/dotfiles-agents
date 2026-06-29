#!/usr/bin/env bash

# PostToolUse hook: Auto-format Python files with ruff after Write/Edit
# NOTE: Do NOT use set -euo pipefail — ruff may return non-zero for lint issues

input=$(cat)

# Extract file_path from tool input JSON
file_path=$(echo "$input" | jq -r '.tool_input.file_path // empty' 2>/dev/null || echo "")

# Exit silently if no file path or not a .py file
if [ -z "$file_path" ] || [[ ! "$file_path" =~ \.py$ ]]; then
    exit 0
fi

# Exit silently if ruff not installed
if ! command -v ruff &> /dev/null; then
    exit 0
fi

# Exit silently if file doesn't exist
if [ ! -f "$file_path" ]; then
    exit 0
fi

# Format, then fix auto-fixable lint issues
ruff format "$file_path" &> /dev/null || true
ruff check "$file_path" --fix --silent &> /dev/null || true

# Check for remaining issues
remaining=$(ruff check "$file_path" 2>&1 || true)

if [ -z "$remaining" ] || ! echo "$remaining" | grep -q "Found"; then
    message="Auto-formatted $file_path with ruff."
else
    issue_count=$(echo "$remaining" | sed -n 's/.*Found \([0-9]*\).*/\1/p' | head -1)
    issue_count=${issue_count:-some}
    message="Auto-formatted $file_path with ruff. $issue_count linting issue(s) remain — run: ruff check $file_path"
fi

# Output JSON with systemMessage
if command -v jq &> /dev/null; then
    jq -n --arg msg "$message" '{systemMessage: $msg}'
else
    escaped=$(echo -n "$message" | sed 's/\\/\\\\/g; s/"/\\"/g; s/\t/\\t/g')
    cat << EOF
{
  "systemMessage": "$escaped"
}
EOF
fi

exit 0
