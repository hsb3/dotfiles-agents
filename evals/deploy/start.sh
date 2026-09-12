#!/bin/sh
set -eu

data_dir=/pb/pb_data
pb_bin=${POCKETBASE_BIN:-/pb/pocketbase}
: "${PB_SUPERUSER_EMAIL:?PB_SUPERUSER_EMAIL is required}"
: "${PB_SUPERUSER_PASSWORD:?PB_SUPERUSER_PASSWORD is required}"
if output=$("$pb_bin" superuser create "$PB_SUPERUSER_EMAIL" "$PB_SUPERUSER_PASSWORD" --dir "$data_dir" 2>&1); then
  if [ -n "$output" ]; then
    printf '%s\n' "$output" >&2
    exit 1
  fi
elif printf '%s' "$output" | grep -q 'must be unique'; then
  :
else
  printf '%s\n' "$output" >&2
  exit 1
fi

exec "$pb_bin" serve --http="0.0.0.0:${PORT:-8090}" --dir "$data_dir" \
  --origins="${PB_CORS_ORIGINS:-https://invalid.local}"
