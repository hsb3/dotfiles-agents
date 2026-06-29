#!/usr/bin/env bash

# SessionStart hook: Detect Python projects and check tool/config availability
# Merges ty plugin detection with python-project-standards enforcement

set -euo pipefail

# Detect Python project
is_python_project=false
if [ -f "$CLAUDE_PROJECT_DIR/pyproject.toml" ] ||
   [ -f "$CLAUDE_PROJECT_DIR/setup.py" ] ||
   [ -f "$CLAUDE_PROJECT_DIR/requirements.txt" ] ||
   find "$CLAUDE_PROJECT_DIR" -maxdepth 2 -name "*.py" -print -quit 2>/dev/null | grep -q .; then
    is_python_project=true
fi

# Not a Python project — exit silently
if [ "$is_python_project" = false ]; then
    exit 0
fi

issues=()
passing=()

# --- pyproject.toml checks ---
if [ -f "$CLAUDE_PROJECT_DIR/pyproject.toml" ]; then
    passing+=("pyproject.toml exists")
    pyproject_content=$(cat "$CLAUDE_PROJECT_DIR/pyproject.toml")

    for section in "\[project\]" "\[tool\.uv\]" "\[tool\.ruff\]" "\[tool\.ty\]"; do
        clean_name=$(echo "$section" | sed 's/\\//g')
        if echo "$pyproject_content" | grep -q "$section"; then
            passing+=("$clean_name section present")
        else
            issues+=("pyproject.toml missing $clean_name section")
        fi
    done
else
    issues+=("pyproject.toml not found — run: uv init")
fi

# --- Tool availability ---
for tool in uv ty ruff; do
    if command -v "$tool" &> /dev/null; then
        version=$("$tool" --version 2>/dev/null | head -n1 || echo "unknown")
        passing+=("$tool installed ($version)")
    else
        issues+=("$tool not installed")
    fi
done

# --- Virtual environment ---
if [ -d "$CLAUDE_PROJECT_DIR/.venv" ]; then
    passing+=("virtual environment (.venv) exists")
else
    issues+=("no virtual environment — run: uv venv")
fi

# --- Build context message ---
if [ ${#issues[@]} -eq 0 ]; then
    context="Python project detected. All standards met.\nPassing: $(IFS=', '; echo "${passing[*]}")"
else
    context="Python project detected — issues found.\n\nPassing: $(IFS=', '; echo "${passing[*]}")\n\nNeeds attention: $(IFS=', '; echo "${issues[*]}")\n\nInform the user about these issues and suggest fixes."
fi

# --- Output JSON ---
if command -v jq &> /dev/null; then
    jq -n --arg ctx "$context" '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $ctx}}'
else
    escaped=$(echo -n "$context" | sed 's/\\/\\\\/g; s/"/\\"/g; s/\t/\\t/g')
    cat << EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "$escaped"
  }
}
EOF
fi

exit 0
