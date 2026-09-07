#!/usr/bin/env sh
# Install individual Claude Code skills from this repo, with no marketplace
# (ADR 0017: generated at install time, never tracked).
#
# From a clone (fresh or pulled):
#   scripts/install_claude_skills.sh --global                    # ~/.claude/skills/
#   scripts/install_claude_skills.sh --project <dir>             # <dir>/.claude/skills/
#   scripts/install_claude_skills.sh --only mermaid,diagrams --project <dir>
#
# Builds the laydown into a tempdir via gen_claude_skills.py (stdlib-only python3), then runs
# the generated installer with the remaining arguments. Re-run after `git pull` to refresh;
# it overwrites only directories carrying its own .laydown marker.
set -eu
HERE="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# --only is ours, not the installer's: rotate it out of "$@" so quoting survives.
ONLY=""
n=$#
while [ "$n" -gt 0 ]; do
  case "$1" in
    --only) ONLY="${2:?usage: --only <id>[,<id>]}"; shift 2; n=$((n - 2)) ;;
    *) set -- "$@" "$1"; shift; n=$((n - 1)) ;;
  esac
done

if [ -n "$ONLY" ]; then
  python3 "$HERE/gen_claude_skills.py" --out "$TMP/lane" --only "$ONLY"
else
  python3 "$HERE/gen_claude_skills.py" --out "$TMP/lane"
fi
"$TMP/lane/install.sh" "$@"
