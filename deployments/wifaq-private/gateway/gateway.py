import os
import time
import uuid
from typing import Any
import httpx
from fastapi import FastAPI, Header, HTTPException, Query, Request

app = FastAPI(title="Wifaq Private Search API", version="1.0.0")
SEARXNG_URL = os.environ["SEARXNG_URL"].rstrip("/")
TOKEN = os.environ["WIFAQ_SEARCH_TOKEN"]
MAX_RESULTS = int(os.getenv("MAX_RESULTS", "20"))
TIMEOUT = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "10"))

@app.get("/healthz")
async def healthz():
    return {"status": "ok", "service": "wifaq-private-search", "version": "1.0.0"}

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
async def search(
    request: Request,
    q: str = Query(min_length=1, max_length=500),
    language: str = Query(default="auto", max_length=32),
    time_range: str | None = Query(default=None, pattern="^(day|week|month|year)$"),
    safe_search: int = Query(default=1, ge=0, le=2),
    category: str = Query(default="general", max_length=32),
    page: int = Query(default=1, ge=1, le=3),
    limit: int = Query(default=10, ge=1, le=20),
    authorization: str | None = Header(default=None),
):
    if authorization != f"Bearer {TOKEN}":
        raise HTTPException(status_code=401, detail="invalid credentials")
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
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
    results = []
    seen = set()
    for item in payload.get("results", []):
        url = item.get("url")
        if not url or url in seen:
            continue
        seen.add(url)
        results.append({"title": item.get("title", ""), "url": url, "snippet": item.get("content", ""), "engines": item.get("engines", []), "published_at": item.get("publishedDate")})
        if len(results) >= limit:
            break
    return {"request_id": request_id, "results": results, "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "duration_ms": round((time.perf_counter() - started) * 1000), "partial": False, "warnings": []}
