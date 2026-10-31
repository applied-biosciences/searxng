#!/usr/bin/env bash
set -euo pipefail
BASE_URL=${BASE_URL:-http://localhost:8080}
TOKEN=${WIFAQ_SEARCH_TOKEN:?Set WIFAQ_SEARCH_TOKEN}
curl -fsS "$BASE_URL/healthz" >/dev/null
curl -fsS "$BASE_URL/readyz" >/dev/null
curl -fsS -H "Authorization: Bearer $TOKEN" "$BASE_URL/v1/search?q=OpenAI&limit=3" >/dev/null
curl -fsS -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json"   "$BASE_URL/mcp"   --data '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' >/dev/null
curl -fsS -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json"   "$BASE_URL/mcp"   --data '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' >/dev/null
curl -fsS -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json"   "$BASE_URL/mcp"   --data '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"web_search","arguments":{"q":"OpenAI","limit":3}}}' >/dev/null
echo "private search REST and MCP smoke test: PASS"
