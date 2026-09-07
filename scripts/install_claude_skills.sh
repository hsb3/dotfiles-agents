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
SEEN=0
n=$#
while [ "$n" -gt 0 ]; do
  case "$1" in
    --only)
      # A ${2:?} bail would exit 0 here — the EXIT trap's rm resets $? under macOS sh.
      [ "$SEEN" -eq 0 ] || { echo "--only given twice; combine ids: --only a,b" >&2; exit 2; }
      [ $# -ge 2 ] || { echo "usage: --only <id>[,<id>]" >&2; exit 2; }
      ONLY="$2"; SEEN=1; shift 2; n=$((n - 2)) ;;
    *) set -- "$@" "$1"; shift; n=$((n - 1)) ;;
  esac
done

if [ "$SEEN" -eq 1 ]; then
  python3 "$HERE/gen_claude_skills.py" --out "$TMP/lane" --only "$ONLY"
else
  python3 "$HERE/gen_claude_skills.py" --out "$TMP/lane"
fi
"$TMP/lane/install.sh" "$@"
