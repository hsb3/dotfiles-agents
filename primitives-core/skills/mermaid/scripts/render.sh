#!/usr/bin/env bash
# Usage: render.sh <in.mmd> <out.svg|out.png> [extra mermaid-cli args...]
# Renders with mermaid-cli, first making sure the chrome-headless-shell that
# mermaid-cli's own puppeteer expects is cached (it ships none, and the
# failure reads like a diagram syntax error).
set -euo pipefail

in=${1:?usage: render.sh <in.mmd> <out.svg|out.png> [mermaid-cli args...]}
out=${2:?usage: render.sh <in.mmd> <out.svg|out.png> [mermaid-cli args...]}
shift 2
cache=${PUPPETEER_CACHE_DIR:-$HOME/.cache/puppeteer}
export PUPPETEER_CACHE_DIR=$cache

[ -d "$cache/chrome-headless-shell" ] ||
  echo "mermaid render: installing chrome-headless-shell into $cache (one-time download)" >&2
# ponytail: always run the install; measured ~2s when already cached (a no-op),
# so no version-aware presence check. Ceiling: add one if that cost matters per render.
npx -y -p @mermaid-js/mermaid-cli puppeteer browsers install chrome-headless-shell >&2
npx -y @mermaid-js/mermaid-cli -i "$in" -o "$out" "$@"
