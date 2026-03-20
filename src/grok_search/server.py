import time
import uvicorn
from fastapi import FastAPI, Query, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from typing import Optional

from .providers.grok import GrokSearchProvider
from .logger import logger
from .config import config
from .utils import extract_sources_from_text, clean_answer, title_from_url, extract_snippet_for_url


app = FastAPI(
    title="Grok Search SERP API",
    description="SERP API powered by Grok's built-in search capabilities",
    version="1.0.0",
)


def _verify_api_key(authorization: Optional[str] = None, x_api_key: Optional[str] = None) -> None:
    """Verify the request API key if API_KEY is configured."""
    expected = config.api_key
    if not expected:
        return

    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:]
    elif x_api_key:
        token = x_api_key

    if not token or token != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@app.api_route("/search", methods=["GET", "POST"])
async def search(
    request: Request,
    q: Optional[str] = Query(None, description="Search query string"),
    model: Optional[str] = Query(None, description="Override Grok model for this request"),
    platform: Optional[str] = Query(None, description="Focus platform (e.g. 'Twitter', 'GitHub')"),
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
):
    """
    Perform a web search using Grok's built-in search and return SERP results.
    Supports both GET (query params) and POST (JSON body).
    """
    _verify_api_key(authorization, x_api_key)

    # For POST requests, read query/model/platform from JSON body
    count = None
    if request.method == "POST":
        try:
            body = await request.json()
        except Exception:
            body = {}
        q = q or body.get("q") or body.get("query") or body.get("search")
        model = model or body.get("model")
        platform = platform or body.get("platform")
        count = body.get("count")

    if not q:
        raise HTTPException(status_code=400, detail="Missing required parameter: q")

    start_time = time.time()

    try:
        api_url = config.grok_api_url
        api_key = config.grok_api_key
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"Configuration error: {str(e)}")

    effective_model = model or config.grok_model
    provider = GrokSearchProvider(api_url, api_key, effective_model)

    try:
        search_resp = await provider.search(q, platform=platform or "")
    except Exception as e:
        logger.error("Grok search failed: %s", e)
        raise HTTPException(status_code=502, detail=f"Upstream search error: {str(e)}")

    answer = clean_answer(search_resp.content)

    # Merge sources: API citations first (higher quality), then text-extracted
    text_sources = extract_sources_from_text(search_resp.content)
    seen_urls: set[str] = set()
    organic: list[dict] = []
    pos = 1

    # 1) API-level citations (from Grok response metadata)
    for c in search_resp.citations:
        url = c.get("url", "")
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        organic.append({
            "position": pos,
            "title": c.get("title") or title_from_url(url),
            "link": url,
            "snippet": c.get("snippet", ""),
        })
        pos += 1

    # 2) Text-extracted sources (from answer body)
    for src in text_sources:
        url = src["link"]
        if url in seen_urls:
            continue
        seen_urls.add(url)
        organic.append({
            "position": pos,
            "title": src.get("title", title_from_url(url)),
            "link": url,
            "snippet": src.get("snippet", ""),
        })
        pos += 1

    # 3) Fill empty snippets from answer context (zero LLM cost)
    for item in organic:
        if not item.get("snippet"):
            item["snippet"] = extract_snippet_for_url(item["link"], answer)

    elapsed_ms = round((time.time() - start_time) * 1000, 2)

    # POST: return flat list for Open WebUI compatibility
    if request.method == "POST":
        results = organic[:count] if count else organic
        return results

    # GET: return full SERP format
    return {
        "searchParameters": {
            "q": q,
            "model": effective_model,
            **({"platform": platform} if platform else {}),
        },
        "answer": answer,
        "organic": organic,
        "searchInformation": {
            "totalResults": len(organic),
            "timeTakenMs": elapsed_ms,
        },
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    try:
        _ = config.grok_api_url
        _ = config.grok_api_key
        config_ok = True
    except ValueError:
        config_ok = False

    return {
        "status": "ok" if config_ok else "misconfigured",
        "model": config.grok_model,
        "version": "1.0.0",
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )


def main():
    logger.info(
        "Starting Grok Search SERP API on %s:%d",
        config.api_host,
        config.api_port,
    )
    uvicorn.run(
        "grok_search.server:app",
        host=config.api_host,
        port=config.api_port,
        log_level=config.log_level.lower(),
    )


if __name__ == "__main__":
    main()
