#!/bin/bash
# Generate session summary on stop (requires config file to exist)
# The Python script checks enabled flag internally and exits cleanly if disabled

# Quick gate: config file must exist to avoid unnecessary uv overhead
if [ ! -f ".claude/dev-focus.local.md" ] && [ ! -f "$HOME/.claude/dev-focus.local.md" ]; then
    exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
uv run "$SCRIPT_DIR/scripts/session-summary.py" >/dev/null 2>&1 || true
