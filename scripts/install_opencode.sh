#!/usr/bin/env sh
# Install the opencode lane from this repo (ADR 0017: generated at install time, never tracked).
#
# From a clone (fresh or pulled):
#   scripts/install_opencode.sh --global            # ~/.config/opencode/{skills,agents}/
#   scripts/install_opencode.sh --project <dir>     # <dir>/.opencode/{skills,agents}/
#
# Builds the laydown into a tempdir via gen_opencode.py (stdlib-only python3), then runs the
# generated installer with the arguments given. Re-run after `git pull` to update.
set -eu
HERE="$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
python3 "$HERE/gen_opencode.py" --out "$TMP/lane"
"$TMP/lane/install.sh" "$@"
