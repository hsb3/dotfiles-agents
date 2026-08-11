#!/usr/bin/env bash
# mint-mcp-token.sh <base-url> — prints a Kaneo MCP access token for the agent
# whose API key is in $MINT_KEY.
#
#   MINT_KEY=<agent-api-key> \
#     "${CLAUDE_PLUGIN_ROOT}/skills/kaneo/scripts/mint-mcp-token.sh" \
#     https://kaneo.example.com
#
# MINT_KEY must be the repo's AGENT key, never the owner key: the token's
# identity is whoever owns the key. The agent key itself cannot be minted from
# here — it needs owner credentials and the instance's workspace id, so the
# owner supplies it (see references/configuration.md).
#
# Token = better-auth session row, 30-day expiry, no refresh — on expiry
# re-mint, update KANEO_MCP_TOKEN in this repo's .claude/settings.local.json,
# and restart the session (env expands at session start). Token goes to stdout;
# progress to stderr, so `MINT_KEY=... mint-mcp-token.sh <url> > token.txt` is
# safe.
#
# Depends only on its argument, $MINT_KEY, curl, openssl, and python3 — no
# instance config, no repo-local state.
set -euo pipefail
BASE=${1:?usage: MINT_KEY=<agent-api-key> mint-mcp-token.sh <base-url>}
: "${MINT_KEY:?usage: MINT_KEY=<agent-api-key> mint-mcp-token.sh <base-url>}"
BASE=${BASE%/}
REDIRECT=http://localhost:9999/cb

echo "1/4 register client" >&2
CLIENT_ID=$(curl -sf -X POST "$BASE/api/mcp/register" -H 'Content-Type: application/json' \
  -d "{\"redirect_uris\":[\"$REDIRECT\"],\"client_name\":\"kaneo-agent-mcp\"}" | python3 -c 'import json,sys;print(json.load(sys.stdin)["client_id"])')

VERIFIER=$(openssl rand -hex 32)
CHALLENGE=$(printf '%s' "$VERIFIER" | openssl dgst -sha256 -binary | openssl base64 -A | tr '+/' '-_' | tr -d '=')

echo "2/4 authorize" >&2
CONSENT=$(curl -sf -o /dev/null -w '%{redirect_url}' \
  "$BASE/api/mcp/authorize?client_id=$CLIENT_ID&redirect_uri=$REDIRECT&response_type=code&code_challenge=$CHALLENGE&code_challenge_method=S256&state=xyz")
REQUEST_ID=$(python3 -c "from urllib.parse import urlparse,parse_qs;import sys;print(parse_qs(urlparse(sys.argv[1]).query)['request_id'][0])" "$CONSENT")

echo "3/4 approve consent as agent" >&2
CB=$(curl -sf -X POST "$BASE/api/mcp/authorize/request/$REQUEST_ID" \
  -H "x-api-key: $MINT_KEY" -H "Origin: $BASE" -H 'Content-Type: application/json' \
  -d '{"approved":true}' | python3 -c 'import json,sys;print(json.load(sys.stdin)["redirect"])')
CODE=$(python3 -c "from urllib.parse import urlparse,parse_qs;import sys;print(parse_qs(urlparse(sys.argv[1]).query)['code'][0])" "$CB")

echo "4/4 token exchange" >&2
curl -sf -X POST "$BASE/api/mcp/token" -H 'Content-Type: application/x-www-form-urlencoded' \
  -d "grant_type=authorization_code&code=$CODE&code_verifier=$VERIFIER&client_id=$CLIENT_ID&redirect_uri=$REDIRECT" \
  | python3 -c 'import json,sys;print(json.load(sys.stdin)["access_token"])'
