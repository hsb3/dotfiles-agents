#!/bin/sh
set -eu

data_dir=${PB_DATA_DIR:-/pb/pb_data}
pb_bin=${POCKETBASE_BIN:-/pb/pocketbase}
package_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
: "${PB_SUPERUSER_EMAIL:?PB_SUPERUSER_EMAIL is required}"
: "${PB_SUPERUSER_PASSWORD:?PB_SUPERUSER_PASSWORD is required}"
if output=$("$pb_bin" superuser create "$PB_SUPERUSER_EMAIL" "$PB_SUPERUSER_PASSWORD" --dir "$data_dir" 2>&1); then
  :
elif printf '%s' "$output" | grep -q '^.*failed to create new superuser account: email: Value must be unique\.$'; then
  :
else
  printf '%s\n' "$output" >&2
  exit 1
fi

exec "$pb_bin" serve --http="${PB_BIND:-0.0.0.0}:${PORT:-8090}" --dir "$data_dir" \
  --hooksDir="$package_dir/pb_hooks" --publicDir="$package_dir/pb_public" \
  --origins="${PB_CORS_ORIGINS:-https://invalid.local}"
