#!/usr/bin/env bash
# Render a .pptx to PDF and per-slide JPEGs for visual QA.
#
# Usage: render-pptx.sh deck.pptx [output-dir]
#
# Produces: <output-dir>/<deck-name>.pdf and <output-dir>/slide-01.jpg, slide-02.jpg, ...
# Default output-dir: directory of the input file.
#
# Conversion engine, in preference order:
#   1. soffice (LibreOffice) if on PATH — headless, no GUI flash
#   2. Microsoft PowerPoint via AppleScript (macOS) — renders with the real
#      target application, so font substitution shows up exactly as a viewer
#      would see it. PowerPoint will briefly open; first run may require an
#      Automation permission grant.
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 deck.pptx [output-dir]" >&2
  exit 2
fi

INPUT="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
[[ -f "$INPUT" ]] || { echo "No such file: $INPUT" >&2; exit 2; }
OUTDIR="${2:-$(dirname "$INPUT")}"
mkdir -p "$OUTDIR"
OUTDIR="$(cd "$OUTDIR" && pwd)"
BASE="$(basename "$INPUT" .pptx)"
PDF="$OUTDIR/$BASE.pdf"

command -v pdftoppm >/dev/null || { echo "pdftoppm not found (brew install poppler)" >&2; exit 1; }

SOFFICE="$(command -v soffice || true)"
[[ -z "$SOFFICE" && -x "/Applications/LibreOffice.app/Contents/MacOS/soffice" ]] \
  && SOFFICE="/Applications/LibreOffice.app/Contents/MacOS/soffice"

if [[ -n "$SOFFICE" ]]; then
  "$SOFFICE" --headless --convert-to pdf --outdir "$OUTDIR" "$INPUT" >/dev/null
elif [[ "$(uname)" == "Darwin" && -d "/Applications/Microsoft PowerPoint.app" ]]; then
  osascript <<EOF
tell application "Microsoft PowerPoint"
  open POSIX file "$INPUT"
  set pres to active presentation
  save pres in POSIX file "$PDF" as save as PDF
  close pres saving no
end tell
EOF
else
  echo "No converter found: install LibreOffice (soffice) or Microsoft PowerPoint." >&2
  exit 1
fi

[[ -f "$PDF" ]] || { echo "PDF conversion failed: $PDF was not created." >&2; exit 1; }

rm -f "$OUTDIR/slide-"*.jpg
pdftoppm -jpeg -r 150 "$PDF" "$OUTDIR/slide"
echo "Rendered: $PDF"
ls "$OUTDIR"/slide-*.jpg
