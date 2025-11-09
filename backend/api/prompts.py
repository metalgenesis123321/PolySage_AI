# # prompts.py - STUB: prompt-engineer will replace with their exact prompt structure & post-processing.
# # This module must implement two functions for /chat orchestration:
# #  1) build_structured_prompt(query, context, market, news) -> dict
# #       expected return keys:
# #         - "mcp_payload": dict   (payload to send to MCP)
# #         - "system_prompt": str  (system instruction for Claude)
# #         - "user_prompt": str    (user prompt content for Claude)
# #
# #  2) post_process_results(mcp_result: dict, claude_result: dict, structured_prompt: dict, market: dict, news: list) -> dict
# #       expected return: report dict with top-level "chat" and "dashboard" keys ready to return to frontend.
# #
# # Both functions MAY be async (the server will await if necessary).

# import json
# from typing import Dict, Any, List

# SYSTEM_MARKET_ANALYST = "You are an expert prediction-market analyst. Output ONLY valid JSON when asked."

# def build_structured_prompt(query: str, context: Dict[str,Any], market: Dict[str,Any], news: List[Dict[str,Any]]) -> Dict[str,Any]:
#     """
#     Minimal stub implementation (prompt-engineer should override).
#     Returns a dict with 'mcp_payload', 'system_prompt', 'user_prompt'.
#     """
#     market_info = {"id": market.get("id"), "title": market.get("title"), "currentPrice": market.get("currentPrice") or market.get("lastPrice")}
#     # mcp_payload: prompt-engineer may want to use a specific shape; keep minimal here
#     mcp_payload = {
#         "market_id": market_info["id"],
#         "market": market_info,
#         "recent_trades": market.get("recentTrades", []),
#         "orderbook": market.get("orderbook", {}),
#         "news": news or [],
#         "meta": {"source": "structured_prompt_stub"}
#     }
#     system_prompt = SYSTEM_MARKET_ANALYST
#     user_prompt = f"Question: {query}\nContext: {json.dumps(market_info)}\nInclude manipulation info if available. Return JSON."
#     return {"mcp_payload": mcp_payload, "system_prompt": system_prompt, "user_prompt": user_prompt}

# def post_process_results(mcp_result: Dict[str,Any], claude_result: Dict[str,Any], structured_prompt: Dict[str,Any], market: Dict[str,Any], news: List[Dict[str,Any]]) -> Dict[str,Any]:
#     """
#     Minimal post-process: produce a simple chat + dashboard object.
#     Prompt-engineer will replace this with richer logic.
#     """
#     chat = {
#         "answer": claude_result.get("answer") if isinstance(claude_result, dict) else str(claude_result),
#         "reasoning": claude_result.get("reasoning", []) if isinstance(claude_result, dict) else [],
#         "recommended_action": claude_result.get("recommended_action") if isinstance(claude_result, dict) else None,
#         "confidence": claude_result.get("confidence", 0.0) if isinstance(claude_result, dict) else 0.0,
#     }
#     dashboard = {
#         "market": {"id": market.get("id"), "title": market.get("title"), "currentPrice": market.get("currentPrice") or market.get("lastPrice")},
#         "manipulation": mcp_result or {},
#         "news": news or []
#     }
#     return {"chat": chat, "dashboard": dashboard}


# if __name__ == "__main__":
#     demo_market = {"id": "m1", "title": "AI adoption rate", "currentPrice": 0.72}
#     demo_news = [{"headline": "AI boom continues", "source": "TechCrunch"}]
#     result = build_structured_prompt("What’s the trend?", {}, demo_market, demo_news)
#     print(json.dumps(result, indent=2))
def post_process_results(
    mcp_result: Dict[str,Any], 
    claude_result: Dict[str,Any], 
    structured_prompt: Dict[str,Any], 
    market: Dict[str,Any], 
    news: List[Dict[str,Any]]
) -> Dict[str,Any]:
    """
    Match your original spec format
    """
    
    # Extract from claude_result if it's JSON
    if isinstance(claude_result, dict):
        dashboard_data = claude_result
    else:
        # Fallback
        dashboard_data = {
            "market_id": market.get("id"),
            "question": market.get("title"),
            "last_price": market.get("currentPrice"),
            "analysis": {
                "volatility_index": 0.0,
                "sentiment_trend": "neutral",
                "manipulation_risk": 0.0,
                "confidence_score": 0.0,
                "notable_events": []
            }
        }
    
    # Add MCP manipulation data
    if mcp_result:
        dashboard_data["analysis"]["manipulation_risk"] = mcp_result.get("riskScore", 0) / 100.0
        dashboard_data["analysis"]["notable_events"] = mcp_result.get("flags", [])
    
    # Add news
    dashboard_data["news_headlines"] = [
        {
            "title": n.get("title"),
            "timestamp_iso": n.get("publishedAt"),
            "url": n.get("url"),
            "source": n.get("source", {}).get("name", "Unknown"),
            "relevance_score": 0.8  # Placeholder
        }
        for n in news[:10]
    ]
    
    return {
        "chat": {
            "answer": f"Analysis complete for {market.get('title')}",
            "reasoning": [],
            "recommended_action": None,
            "confidence": dashboard_data["analysis"]["confidence_score"]
        },
        "dashboard": dashboard_data
    }