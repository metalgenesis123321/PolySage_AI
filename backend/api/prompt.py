# prompts.py - STUB: prompt-engineer will replace with their exact prompt structure & post-processing.
# This module must implement two functions for /chat orchestration:
#  1) build_structured_prompt(query, context, market, news) -> dict
#       expected return keys:
#         - "mcp_payload": dict   (payload to send to MCP)
#         - "system_prompt": str  (system instruction for Claude)
#         - "user_prompt": str    (user prompt content for Claude)
#
#  2) post_process_results(mcp_result: dict, claude_result: dict, structured_prompt: dict, market: dict, news: list) -> dict
#       expected return: report dict with top-level "chat" and "dashboard" keys ready to return to frontend.
#
# Both functions MAY be async (the server will await if necessary).

import json
from typing import Dict, Any, List

SYSTEM_MARKET_ANALYST = "You are an expert prediction-market analyst. Output ONLY valid JSON when asked."

def build_structured_prompt(query: str, context: Dict[str,Any], market: Dict[str,Any], news: List[Dict[str,Any]]) -> Dict[str,Any]:
    """
    Minimal stub implementation (prompt-engineer should override).
    Returns a dict with 'mcp_payload', 'system_prompt', 'user_prompt'.
    """
    market_info = {"id": market.get("id"), "title": market.get("title"), "currentPrice": market.get("currentPrice") or market.get("lastPrice")}
    # mcp_payload: prompt-engineer may want to use a specific shape; keep minimal here
    mcp_payload = {
        "market_id": market_info["id"],
        "market": market_info,
        "recent_trades": market.get("recentTrades", []),
        "orderbook": market.get("orderbook", {}),
        "news": news or [],
        "meta": {"source": "structured_prompt_stub"}
    }
    system_prompt = SYSTEM_MARKET_ANALYST
    user_prompt = f"Question: {query}\nContext: {json.dumps(market_info)}\nInclude manipulation info if available. Return JSON."
    return {"mcp_payload": mcp_payload, "system_prompt": system_prompt, "user_prompt": user_prompt}

def post_process_results(mcp_result: Dict[str,Any], claude_result: Dict[str,Any], structured_prompt: Dict[str,Any], market: Dict[str,Any], news: List[Dict[str,Any]]) -> Dict[str,Any]:
    """
    Minimal post-process: produce a simple chat + dashboard object.
    Prompt-engineer will replace this with richer logic.
    """
    chat = {
        "answer": claude_result.get("answer") if isinstance(claude_result, dict) else str(claude_result),
        "reasoning": claude_result.get("reasoning", []) if isinstance(claude_result, dict) else [],
        "recommended_action": claude_result.get("recommended_action") if isinstance(claude_result, dict) else None,
        "confidence": claude_result.get("confidence", 0.0) if isinstance(claude_result, dict) else 0.0,
    }
    dashboard = {
        "market": {"id": market.get("id"), "title": market.get("title"), "currentPrice": market.get("currentPrice") or market.get("lastPrice")},
        "manipulation": mcp_result or {},
        "news": news or []
    }
    return {"chat": chat, "dashboard": dashboard}
