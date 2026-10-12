#!/usr/bin/env bash
# Usage: render.sh <in.mmd> <out.svg|out.png> [extra mermaid-cli args...]
# Renders with mermaid-cli, first making sure the chrome-headless-shell that
# mermaid-cli's own puppeteer expects is cached (it ships none). One offline-first
# npx resolution runs both steps, so the browser matches the mmdc that renders.
set -euo pipefail

in=${1:?usage: render.sh <in.mmd> <out.svg|out.png> [mermaid-cli args...]}
out=${2:?usage: render.sh <in.mmd> <out.svg|out.png> [mermaid-cli args...]}
shift 2
export PUPPETEER_CACHE_DIR=${PUPPETEER_CACHE_DIR:-$HOME/.cache/puppeteer}

[ -d "$PUPPETEER_CACHE_DIR/chrome-headless-shell" ] ||
  echo "mermaid render: installing chrome-headless-shell into $PUPPETEER_CACHE_DIR (one-time download)" >&2
# ponytail: the install always runs (a no-op when cached), so no version-aware
# presence check. Ceiling: add one if that cost matters per render.
exec npx -y --prefer-offline -p @mermaid-js/mermaid-cli bash -c \
  'puppeteer browsers install chrome-headless-shell >&2 && exec mmdc -i "$1" -o "$2" "${@:3}"' \
  render.sh "$in" "$out" "$@"
