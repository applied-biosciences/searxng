import json
import os
import time
import uuid
from typing import Any
import httpx
from fastapi import FastAPI, Header, HTTPException, Query, Request

app = FastAPI(title="Wifaq Private Search API", version="1.1.0")
SEARXNG_URL = os.environ["SEARXNG_URL"].rstrip("/")
TOKEN = os.environ["WIFAQ_SEARCH_TOKEN"]
TIMEOUT = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "10"))


def _authorized(authorization: str | None) -> None:
    if authorization != f"Bearer {TOKEN}":
        raise HTTPException(status_code=401, detail="invalid credentials")


async def _perform_search(q: str, language: str, time_range: str | None, safe_search: int, category: str, page: int, limit: int, request_id: str) -> dict[str, Any]:
    started = time.perf_counter()
    params: dict[str, Any] = {"q": q, "format": "json", "language": language, "safesearch": safe_search, "categories": category, "pageno": page}
    if time_range:
        params["time_range"] = time_range
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"{SEARXNG_URL}/search", params=params)
            response.raise_for_status()
            payload = response.json()
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="search timeout", headers={"x-request-id": request_id}) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="search backend unavailable", headers={"x-request-id": request_id}) from exc
    results, seen = [], set()
    for item in payload.get("results", []):
        url = item.get("url")
        if not url or url in seen:
            continue
        seen.add(url)
        results.append({"title": item.get("title", ""), "url": url, "snippet": item.get("content", ""), "engines": item.get("engines", []), "published_at": item.get("publishedDate")})
        if len(results) >= limit:
            break
    return {"request_id": request_id, "results": results, "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "duration_ms": round((time.perf_counter() - started) * 1000), "partial": False, "warnings": []}


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "service": "wifaq-private-search", "version": "1.1.0"}

@app.get("/readyz")
async def readyz():
    try:
        async with httpx.AsyncClient(timeout=2) as client:
            response = await client.get(f"{SEARXNG_URL}/search", params={"q": "healthcheck", "format": "json"})
            response.raise_for_status()
        return {"status": "ready"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="search backend unavailable") from exc

@app.get("/v1/search")
async def search(request: Request, q: str = Query(min_length=1, max_length=500), language: str = Query(default="auto", max_length=32), time_range: str | None = Query(default=None, pattern="^(day|week|month|year)$"), safe_search: int = Query(default=1, ge=0, le=2), category: str = Query(default="general", max_length=32), page: int = Query(default=1, ge=1, le=3), limit: int = Query(default=10, ge=1, le=20), authorization: str | None = Header(default=None)):
    _authorized(authorization)
    return await _perform_search(q, language, time_range, safe_search, category, page, limit, request.headers.get("x-request-id") or str(uuid.uuid4()))


@app.post("/mcp")
async def mcp(request: Request, authorization: str | None = Header(default=None)):
    _authorized(authorization)
    body = await request.json()
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    method = body.get("method")
    rpc_id = body.get("id")
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": rpc_id, "result": {"protocolVersion": "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "wifaq-private-search", "version": "1.1.0"}}}
    if method == "notifications/initialized":
        return {"jsonrpc": "2.0", "id": rpc_id, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rpc_id, "result": {"tools": [{"name": "web_search", "description": "Search the public web through the private Wifaq SearXNG gateway.", "inputSchema": {"type": "object", "required": ["q"], "properties": {"q": {"type": "string", "maxLength": 500}, "language": {"type": "string"}, "time_range": {"type": "string", "enum": ["day", "week", "month", "year"]}, "safe_search": {"type": "integer", "minimum": 0, "maximum": 2}, "category": {"type": "string"}, "page": {"type": "integer", "minimum": 1, "maximum": 3}, "limit": {"type": "integer", "minimum": 1, "maximum": 20}}}}]}}
    if method == "tools/call":
        params = body.get("params") or {}
        if params.get("name") != "web_search":
            return {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": -32601, "message": "unknown tool"}}
        args = params.get("arguments") or {}
        result = await _perform_search(str(args.get("q") or ""), str(args.get("language") or "auto"), args.get("time_range"), int(args.get("safe_search", 1)), str(args.get("category") or "general"), int(args.get("page", 1)), int(args.get("limit", 10)), request_id)
        return {"jsonrpc": "2.0", "id": rpc_id, "result": {"content": [{"type": "text", "text": json.dumps(result)}], "structuredContent": result, "isError": False}}
    return {"jsonrpc": "2.0", "id": rpc_id, "error": {"code": -32601, "message": "method not found"}}
