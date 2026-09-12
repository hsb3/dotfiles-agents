#!/bin/sh
set -eu

data_dir=/pb/pb_data
if [ -n "${PB_SUPERUSER_EMAIL:-}" ] || [ -n "${PB_SUPERUSER_PASSWORD:-}" ]; then
  : "${PB_SUPERUSER_EMAIL:?PB_SUPERUSER_EMAIL is required with PB_SUPERUSER_PASSWORD}"
  : "${PB_SUPERUSER_PASSWORD:?PB_SUPERUSER_PASSWORD is required with PB_SUPERUSER_EMAIL}"
  if output=$(/pb/pocketbase superuser create "$PB_SUPERUSER_EMAIL" "$PB_SUPERUSER_PASSWORD" --dir "$data_dir" 2>&1); then
    :
  elif printf '%s' "$output" | grep -q 'must be unique'; then
    :
  else
    printf '%s\n' "$output" >&2
    exit 1
  fi
fi

exec /pb/pocketbase serve --http="0.0.0.0:${PORT:-8090}" --dir "$data_dir" \
  --origins="${PB_CORS_ORIGINS:-https://invalid.local}"
