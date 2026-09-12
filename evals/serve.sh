#!/usr/bin/env bash
# Run the extender-db PocketBase instance with env-var configuration.
#
# PocketBase has no native env var for the data directory — it is set only via the
# --dir flag (its one env-native setting is the encryption key, --encryptionEnv).
# This wrapper is the env-var surface: values resolve from the environment first,
# then .claude/operations/extender-db.env, then defaults.
#
#   PB_DATA_DIR  data directory            (default: <this dir>/pb_data)
#   PB_URL       REST endpoint for eval clients           (default: http://127.0.0.1:8090)
#   PB_BIND      server bind address                      (default: 127.0.0.1:8090)
#
# Usage:
#   ./serve.sh                          # pocketbase serve --dir $PB_DATA_DIR --http $PB_BIND
#   ./serve.sh superuser create E P     # any other pocketbase subcommand, --dir appended
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(dirname "$HERE")"
ENV_FILE="$REPO/.claude/operations/extender-db.env"

if [ -f "$ENV_FILE" ]; then
  while IFS='=' read -r k v; do
    case "$k" in ''|\#*) continue ;; esac
    if [ -z "${!k:-}" ]; then
      export "$k=$v"
    fi
  done < "$ENV_FILE"
fi

PB_DATA_DIR="${PB_DATA_DIR:-$HERE/pb_data}"
PB_URL="${PB_URL:-http://127.0.0.1:8090}"
PB_BIND="${PB_BIND:-127.0.0.1:8090}"

if [ $# -eq 0 ]; then
  exec pocketbase serve --dir "$PB_DATA_DIR" --http "$PB_BIND"
else
  exec pocketbase "$@" --dir "$PB_DATA_DIR"
fi
