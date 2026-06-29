#!/bin/bash
# Dev Focus: inject focus principles + capture session ID for summary

# Persist session ID so Stop hook can find the session JSONL
if [ -n "$CLAUDE_SESSION_ID" ] && [ -n "$CLAUDE_ENV_FILE" ]; then
    echo "SESSION_SUMMARY_SESSION_ID=$CLAUDE_SESSION_ID" >> "$CLAUDE_ENV_FILE"
fi

cat <<'EOF'
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "Dev Focus plugin active. Core rules: (1) Decompose broad tasks into concrete steps before starting. (2) Push back on scope creep — default action is CUT. (3) Keep generated files organized with consistent naming. (4) Checkpoint progress on multi-step work. (5) Before ending, surface any loose ends."
  }
}
EOF
