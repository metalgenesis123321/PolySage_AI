import asyncio, time
from typing import Dict, Any, Optional
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from .utils import utc_now_iso, short_id, extract_first_json_block
from .clients import fetch_market_detail, fetch_trades, fetch_news_for_market, call_claude, fetch_markets, fetch_latest_news
from .mcp import get_manipulation_report, call_mcp_with_payload, startup_mcp_servers, shutdown_mcp_servers

# prompts module supplied by prompt-engineer
try:
    from . import prompts as prompts_module
except Exception:
    prompts_module = None

app = FastAPI(title="PolySage API - Real MCP Integration")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# Lifecycle events for MCP servers
@app.on_event("startup")
async def on_startup():
    """Start MCP servers when API starts"""
    print("="*70)
    print("PolySage API Starting...")
    print("="*70)
    try:
        await startup_mcp_servers()
        print("✓ MCP servers initialized")
    except Exception as e:
        print(f"✗ Warning: MCP servers failed to start: {e}")
        print("  API will continue but MCP features may be unavailable")
    print("="*70)


@app.on_event("shutdown")
async def on_shutdown():
    """Shutdown MCP servers when API stops"""
    print("\nShutting down MCP servers...")
    await shutdown_mcp_servers()
    print("✓ Shutdown complete")


def build_unified_response(chat: Dict[str,Any], dashboard: Dict[str,Any]) -> Dict[str,Any]:
    return {"chat": chat or {}, "dashboard": dashboard or {}}


@app.post("/chat")
async def post_chat(payload: Dict[str,Any]):
    """
    Full orchestration flow with REAL MCP servers:
      1) Receive FE chat: {"query": "...", "context": {...}}
      2) Fetch market & news (client wrappers)
      3) Call prompt-engineer: build_structured_prompt(query, context, market, news)
      4) Send structured prompt outputs:
           - post mcp_payload to MCP via call_mcp_with_payload() → REAL MCP SERVERS
           - call Claude with system_prompt & user_prompt via call_claude()
         (run MCP + Claude concurrently)
      5) Receive results, parse Claude JSON if possible
      6) Call prompt-engineer: post_process_results(mcp_result, claude_result, structured_prompt, market, news)
      7) Return final {"chat","dashboard"} to frontend
    """
    request_id = short_id()
    start_ts = time.time()

    query = payload.get("query") or payload.get("text") or ""
    context = payload.get("context", {}) or {}
    market_id = context.get("market_id")

    # 1) fetch market & trades (parallel)
    market = {"id": market_id} if market_id else {"id": "unknown", "title": query}
    trades = []
    if market_id:
        market_task = asyncio.create_task(fetch_market_detail(market_id))
        trades_task = asyncio.create_task(fetch_trades(market_id, limit=50))
    else:
        market_task = None
        trades_task = None

    if market_task:
        try:
            market = await market_task
        except Exception:
            market = {"id": market_id or "unknown", "title": query}
        try:
            trades = await trades_task
        except Exception:
            trades = []

    # 2) fetch news (small) concurrently while prompt building happens
    news_task = asyncio.create_task(fetch_news_for_market((market.get("title") or query)[:200], page_size=5))

    # 3) build structured prompt via prompt-engineer
    try:
        if prompts_module and hasattr(prompts_module, "build_structured_prompt"):
            structured_prompt = prompts_module.build_structured_prompt(query, context, market, await news_task)
            if hasattr(structured_prompt, "__await__"):
                structured_prompt = await structured_prompt
        else:
            news = await news_task
            structured_prompt = {
                "mcp_payload": {
                    "market_id": market.get("id"),
                    "market": {"id": market.get("id"), "title": market.get("title"), "currentPrice": market.get("currentPrice") or market.get("lastPrice")},
                    "recent_trades": market.get("recentTrades", []),
                    "orderbook": market.get("orderbook", {}),
                    "news": news or [],
                    "meta": {"request_id": request_id}
                },
                "system_prompt": getattr(prompts_module, "SYSTEM_MARKET_ANALYST", "You are an expert prediction-market analyst. Return JSON only."),
                "user_prompt": f"Question: {query}\nContext: {market.get('title')}"
            }
    except Exception:
        news = await news_task
        structured_prompt = {
            "mcp_payload": {
                "market_id": market.get("id"),
                "market": {"id": market.get("id"), "title": market.get("title")},
                "recent_trades": market.get("recentTrades", []),
                "orderbook": market.get("orderbook", {}),
                "news": news or [],
                "meta": {"request_id": request_id}
            },
            "system_prompt": "You are an expert prediction-market analyst. Return JSON only.",
            "user_prompt": f"Question: {query}\nContext: {market.get('title')}"
        }

    # Ensure news variable is set
    if 'news' not in locals():
        news = await news_task

    # 4) call MCP + Claude concurrently using structured_prompt
    mcp_payload = structured_prompt.get("mcp_payload") or {
        "market_id": market.get("id"),
        "market": market,
        "recent_trades": market.get("recentTrades", []),
        "orderbook": market.get("orderbook", {}),
        "news": news or [],
        "meta": {"request_id": request_id}
    }
    system_prompt = structured_prompt.get("system_prompt", getattr(prompts_module, "SYSTEM_MARKET_ANALYST", "You are an expert prediction-market analyst. Return JSON only."))
    user_prompt = structured_prompt.get("user_prompt", f"Question: {query}\nContext: {market.get('title')}")

    # Call REAL MCP servers + Claude concurrently
    print(f"[{request_id}] Calling real MCP servers + Claude...")
    mcp_task = asyncio.create_task(call_mcp_with_payload(mcp_payload))
    claude_task = asyncio.create_task(call_claude(system_prompt, user_prompt, model=(getattr(prompts_module, "CLAUDE_MODEL", None) if prompts_module else None), temperature=0.0))

    # wait for both
    mcp_result = await mcp_task
    claude_raw = None
    claude_json = {}
    try:
        claude_raw = await claude_task
        parsed = extract_first_json_block(claude_raw)
        if parsed and isinstance(parsed, dict):
            claude_json = parsed
        else:
            claude_json = {"answer": claude_raw, "reasoning": [], "recommended_action": None, "confidence": 0.0}
    except Exception as e:
        claude_raw = None
        claude_json = {"answer": f"Claude unavailable: {str(e)}", "reasoning": [], "recommended_action": None, "confidence": 0.0}

    print(f"[{request_id}] MCP risk score: {mcp_result.get('riskScore')}, flags: {len(mcp_result.get('flags', []))}")

    # 5) call prompt-engineer's post-processing
    try:
        if prompts_module and hasattr(prompts_module, "post_process_results"):
            processed = prompts_module.post_process_results(mcp_result, claude_json, structured_prompt, market, news)
            if hasattr(processed, "__await__"):
                processed = await processed
            report = processed or {}
        else:
            # fallback aggregator
            report = {
                "chat": {
                    "answer": claude_json.get("answer"),
                    "reasoning": claude_json.get("reasoning", []),
                    "recommended_action": claude_json.get("recommended_action"),
                    "confidence": claude_json.get("confidence", 0.0),
                },
                "dashboard": {
                    "market": {"id": market.get("id"), "title": market.get("title"), "currentPrice": market.get("currentPrice") or market.get("lastPrice")},
                    "manipulation": mcp_result,
                    "news": news or []
                }
            }
    except Exception:
        report = {
            "chat": {
                "answer": claude_json.get("answer"),
                "reasoning": claude_json.get("reasoning", []),
                "recommended_action": claude_json.get("recommended_action"),
                "confidence": claude_json.get("confidence", 0.0),
            },
            "dashboard": {
                "market": {"id": market.get("id"), "title": market.get("title"), "currentPrice": market.get("currentPrice") or market.get("lastPrice")},
                "manipulation": mcp_result,
                "news": news or []
            }
        }

    # 6) ensure manipulation in dashboard
    if "dashboard" in report:
        if "manipulation" not in report["dashboard"]:
            report["dashboard"]["manipulation"] = mcp_result
    else:
        report = build_unified_response(report.get("chat", {}), {"market": market, "manipulation": mcp_result, "news": news})

    elapsed = time.time() - start_ts
    print(f"[{request_id}] Request completed in {elapsed:.2f}s")

    # 7) return to frontend
    return {"chat": report.get("chat", {}), "dashboard": report.get("dashboard", {})}


@app.get("/dashboard")
async def get_dashboard(market_id: str = Query(...)):
    """Get dashboard data for a market using REAL MCP analysis"""
    market = await fetch_market_detail(market_id)
    trades = await fetch_trades(market_id, limit=50)
    news = await fetch_news_for_market(market.get("title") or market_id, page_size=5)
    
    # Call real MCP servers for manipulation analysis
    manipulation = await get_manipulation_report(market_id, trades, market.get("orderbook", {}), news, meta={"market": market})
    
    return {
        "request_id": short_id(),
        "timestamp": utc_now_iso(),
        "market": {"id": market.get("id"), "title": market.get("title"), "currentPrice": market.get("currentPrice") or market.get("lastPrice")},
        "manipulation": manipulation,
        "news": news,
        "sources": [f"polymarket:{market.get('id')}", "MCP real-data servers"],
        "mcp_status": "ok" if manipulation and manipulation.get("riskScore") is not None else "unavailable"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    from .clients import POLY_API_URL, NEWS_API_URL, CLAUDE_API_URL
    from .mcp import _mcp_manager
    
    return {
        "ok": True,
        "ts": utc_now_iso(),
        "services": {
            "polymarket": bool(POLY_API_URL),
            "news": bool(NEWS_API_URL),
            "claude": bool(CLAUDE_API_URL),
            "mcp_polymarket": _mcp_manager.polymarket_proc is not None and _mcp_manager.polymarket_proc.poll() is None if _mcp_manager.initialized else False,
            "mcp_news": _mcp_manager.news_proc is not None and _mcp_manager.news_proc.poll() is None if _mcp_manager.initialized else False
        }
    }


@app.get("/")
async def root():
    """API info"""
    return {
        "service": "PolySage API",
        "version": "1.0.0",
        "mcp_integration": "Real MCP Servers (Polymarket + News)",
        "endpoints": {
            "POST /chat": "Main chat endpoint with MCP analysis",
            "GET /dashboard?market_id=X": "Get dashboard data",
            "GET /health": "Health check"
        }
    }