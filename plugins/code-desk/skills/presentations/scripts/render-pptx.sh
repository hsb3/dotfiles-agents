#!/usr/bin/env bash
# Preserve the authored render entry point; Python handles paths and converter arguments.
set -euo pipefail
exec python3 "$(dirname "$0")/render.py" "$@"
