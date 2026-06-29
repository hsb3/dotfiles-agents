#!/usr/bin/env bash

# Stop hook: Remind about Python quality checks before stopping
# Only fires if Python files (.py) were in scope during the session

set -euo pipefail

input=$(cat)

# Extract project dir
project_dir="${CLAUDE_PROJECT_DIR:-}"

# Quick check: is this a Python project?
is_python=false
if [ -n "$project_dir" ]; then
    if [ -f "$project_dir/pyproject.toml" ] ||
       [ -f "$project_dir/setup.py" ] ||
       [ -f "$project_dir/requirements.txt" ] ||
       find "$project_dir" -maxdepth 2 -name "*.py" -print -quit 2>/dev/null | grep -q .; then
        is_python=true
    fi
fi

# Not a Python project — approve silently
if [ "$is_python" = false ]; then
    echo '{"decision": "approve"}'
    exit 0
fi

# Python project — approve but surface the reminder
message="If Python files (.py) were created or modified during this session, check before stopping: (1) Were type errors checked? If not, suggest running /ty-check. (2) Were linting issues checked? If not, suggest running ruff check. (3) If test files exist, were tests run? If not, suggest running uv run pytest. Only remind about checks that were NOT already done in this session."

if command -v jq &> /dev/null; then
    jq -n --arg msg "$message" '{decision: "approve", reason: $msg}'
else
    escaped=$(echo -n "$message" | sed 's/\\/\\\\/g; s/"/\\"/g; s/\t/\\t/g')
    cat << EOF
{
  "decision": "approve",
  "reason": "$escaped"
}
EOF
fi

exit 0
