# clients.py - wrappers for Polymarket / News / Claude (stateless)
import os, json
from typing import List, Dict, Any, Optional
import httpx
from cachetools import TTLCache, cached
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

# ENV
POLY_API_URL = os.getenv("POLY_API_URL")
POLY_API_KEY = os.getenv("POLY_API_KEY")
NEWS_API_URL = os.getenv("NEWS_API_URL")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
CLAUDE_API_URL = os.getenv("CLAUDE_API_URL")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

# caches
_markets_cache = TTLCache(maxsize=200, ttl=int(os.getenv("CACHE_TTL_MARKETS", "30")))
_detail_cache = TTLCache(maxsize=200, ttl=int(os.getenv("CACHE_TTL_DETAIL", "10")))
_news_cache = TTLCache(maxsize=200, ttl=60)

# HTTP helpers with retry
@retry(wait=wait_exponential(multiplier=0.3, min=0.3, max=3), stop=stop_after_attempt(3),
       retry=retry_if_exception_type(httpx.HTTPError))
async def _get(url: str, params: dict = None, headers: dict = None, timeout: float = 10.0):
    headers = headers or {}
    async with httpx.AsyncClient(timeout=timeout) as c:
        r = await c.get(url, params=params, headers=headers)
        r.raise_for_status()
        return r.json()

@retry(wait=wait_exponential(multiplier=0.3, min=0.3, max=3), stop=stop_after_attempt(3),
       retry=retry_if_exception_type(httpx.HTTPError))
async def _post(url: str, payload: dict, headers: dict = None, timeout: float = 10.0):
    headers = headers or {}
    async with httpx.AsyncClient(timeout=timeout) as c:
        r = await c.post(url, json=payload, headers=headers)
        r.raise_for_status()
        return r.json()

# Polymarket wrappers
@cached(_markets_cache)
async def fetch_markets(limit: int = 50) -> List[Dict[str,Any]]:
    if not POLY_API_URL:
        raise ValueError("POLY_API_URL not configured")
    headers = {"Authorization": f"Bearer {POLY_API_KEY}"} if POLY_API_KEY else {}
    data = await _get(f"{POLY_API_URL}/markets", params={"limit": limit}, headers=headers)
    return data.get("markets", data)

@cached(_detail_cache)
async def fetch_market_detail(market_id: str) -> Dict[str,Any]:
    if not POLY_API_URL:
        raise ValueError("POLY_API_URL not configured")
    headers = {"Authorization": f"Bearer {POLY_API_KEY}"} if POLY_API_KEY else {}
    return await _get(f"{POLY_API_URL}/markets/{market_id}", headers=headers)

async def fetch_trades(market_id: str, limit: int = 100):
    if not POLY_API_URL:
        raise ValueError("POLY_API_URL not configured")
    headers = {"Authorization": f"Bearer {POLY_API_KEY}"} if POLY_API_KEY else {}
    data = await _get(f"{POLY_API_URL}/markets/{market_id}/trades", headers=headers, params={"limit": limit})
    return data.get("trades", data)

async def fetch_latest(limit: int = 10):
    if not POLY_API_URL:
        raise ValueError("POLY_API_URL not configured")
    headers = {"Authorization": f"Bearer {POLY_API_KEY}"} if POLY_API_KEY else {}
    data = await _get(f"{POLY_API_URL}/markets/latest", headers=headers, params={"limit": limit})
    return data

# News wrappers
@cached(_news_cache)
async def fetch_news_for_market(query: str, page_size: int = 5):
    if not NEWS_API_URL or not NEWS_API_KEY:
        raise ValueError("NEWS_API_URL or NEWS_API_KEY not configured")
    data = await _get(f"{NEWS_API_URL}/everything", params={"q": query, "pageSize": page_size, "apiKey": NEWS_API_KEY})
    return data.get("articles", [])[:page_size]

async def fetch_latest_news(limit: int = 5):
    if not NEWS_API_URL or not NEWS_API_KEY:
        raise ValueError("NEWS_API_URL or NEWS_API_KEY not configured")
    data = await _get(f"{NEWS_API_URL}/top-headlines", params={"pageSize": limit, "apiKey": NEWS_API_KEY})
    return data.get("articles", [])[:limit]

# Claude wrapper (returns raw text)
async def call_claude(system_prompt: str, user_prompt: str, model: Optional[str] = None, temperature: float = 0.0, max_tokens: int = 800) -> str:
    if not CLAUDE_API_URL or not CLAUDE_API_KEY:
        raise ValueError("CLAUDE_API_URL or CLAUDE_API_KEY not configured")
    
    payload = {
        "model": model or CLAUDE_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    headers = {"Authorization": f"Bearer {CLAUDE_API_KEY}", "Content-Type": "application/json"}
    resp = await _post(CLAUDE_API_URL, payload, headers=headers, timeout=20.0)
    
    # adapt to common response shapes
    if isinstance(resp, dict):
        if "choices" in resp and len(resp["choices"]) > 0:
            c = resp["choices"][0]
            return c.get("message", {}).get("content") or c.get("text") or json.dumps(c)
        if "completion" in resp:
            return resp.get("completion")
        if "output" in resp:
            return resp.get("output")
    return json.dumps(resp)