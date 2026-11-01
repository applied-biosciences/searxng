# Wifaq Private Search API

This deployment runs SearXNG privately on AWS and exposes only the authenticated gateway to Wifaq.

- Keep SearXNG on the internal Docker network.
- Store WIFAQ_SEARCH_TOKEN in AWS Secrets Manager or the approved runtime secret store.
- Do not publish SearXNG directly.
- Replace the placeholder SearXNG secret key at deployment time.
- Pin image digests before production rollout.

API endpoints: GET /healthz, GET /readyz, GET /v1/search?q=... with Authorization: Bearer <token>.

The gateway caps queries at 500 characters, pages at 3, results at 20, and backend time at 10 seconds. It returns normalized results and does not provide arbitrary URL fetching.

SearXNG remains licensed under AGPL-3.0-or-later. Keep source and attribution notices with the deployment.

Stage 2 MCP is available at POST /mcp on the authenticated gateway. It exposes only the read-only web_search tool and supports initialize, tools/list, and tools/call. Use the same Bearer token as the REST API. For local verification, publish the gateway on 127.0.0.1:8080 and configure WIFAQ_PRIVATE_SEARCH_URL=http://localhost:8080.
