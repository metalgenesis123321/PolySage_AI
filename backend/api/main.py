
import asyncio, time, json
from pathlib import Path
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from utils import utc_now_iso, short_id, extract_first_json_block
from clients import fetch_market_detail, fetch_news_for_market, call_claude, fetch_markets
from mcp import call_mcp_with_payload, startup_mcp_servers, shutdown_mcp_servers

app = FastAPI(title="PolySage API - Enhanced")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Simple cache file
CACHE_FILE = Path("response_cache.json")
import time 

def load_cache():
    """Load cache from JSON file"""
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_cache(cache):
    """Save cache to JSON file"""
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        print(f"⚠️ Cache save failed: {e}")

def get_cached(query):
    """Get cached response"""
    cache = load_cache()
    key = query
    if key in cache:
        print(f"✅ Cache HIT")
        
        return cache[key]
    print(f"❌ Cache MISS")
    return None

def set_cache(query, response):
    """Store response in cache"""
    cache = load_cache()
    key = query.lower().strip()
    cache[key] = response
    save_cache(cache)
    print(f"💾 Cached response")


@app.on_event("startup")
async def on_startup():
    """Start MCP servers when API starts"""
    print("="*70)
    print("PolySage API Starting...")
    print("="*70)
    
    import os
    claude_key = os.getenv("CLAUDE_API_KEY")
    if not claude_key:
        print("✗ CRITICAL: CLAUDE_API_KEY environment variable not set!")
        raise RuntimeError("Missing required API key: CLAUDE_API_KEY")
    
    print(f"✓ Claude API key configured: {claude_key[:20]}...")
    print(f"✓ Cache system initialized")
    
    try:
        await startup_mcp_servers()
        print("✓ MCP servers initialized")
    except Exception as e:
        print(f"✗ WARNING: MCP servers failed to start: {e}")
    print("="*70)


@app.on_event("shutdown")
async def on_shutdown():
    """Shutdown MCP servers when API stops"""
    print("\nShutting down MCP servers...")
    await shutdown_mcp_servers()
    print("✓ Shutdown complete")


async def resolve_market_id(query: str, request_id: str) -> Optional[str]:
    """
    Resolve a market ID from a query that mentions a market title.
    Returns market_id if found, None otherwise.
    """
    print(f"[{request_id}] Attempting to resolve market ID from query...")
    
    try:
        # Fetch available markets
        markets_raw = await fetch_markets(limit=50)
        
        # Handle different response formats
        if isinstance(markets_raw, dict):
            markets = markets_raw.get('data', []) or markets_raw.get('markets', []) or []
        elif isinstance(markets_raw, list):
            markets = markets_raw
        else:
            return None
        
        if not markets:
            return None
        
        # Build market list with titles
        market_list = []
        for m in markets:
            if not isinstance(m, dict):
                continue
            market_list.append({
                'id': m.get('id', 'unknown'),
                'title': m.get('title', 'Untitled')
            })
        
        # Use Claude to find the best matching market
        system_prompt = """You are a market matching assistant.
Given a user query and a list of markets, determine if the query is referring to a specific market.
If yes, return the market ID. If no clear match, return null.
Respond with ONLY a JSON object: {"market_id": "..." or null, "confidence": 0-1}"""

        user_prompt = f"""User Query: {query}

Available Markets:
{json.dumps(market_list, indent=2)}

Does this query refer to one of these markets? If yes, which one?
Output ONLY JSON."""

        response = await call_claude(system_prompt, user_prompt, temperature=0.1, max_tokens=300)
        result = extract_first_json_block(response)
        
        if result and result.get('market_id') and result.get('confidence', 0) > 0.5:
            market_id = result['market_id']
            print(f"[{request_id}] ✓ Resolved market ID: {market_id} (confidence: {result.get('confidence')})")
            return market_id
        
        # Fallback: fuzzy string matching
        query_lower = query.lower()
        for m in market_list:
            title_lower = m['title'].lower()
            # Check if significant portion of title is in query or vice versa
            if len(title_lower) > 10:
                if title_lower in query_lower or query_lower in title_lower:
                    print(f"[{request_id}] ✓ Resolved via fuzzy match: {m['id']}")
                    return m['id']
        
        print(f"[{request_id}] ⚠️  Could not resolve market ID from query")
        return None
        
    except Exception as e:
        print(f"[{request_id}] ⚠️  Market ID resolution failed: {e}")
        return None


async def classify_chat_intent(query: str, market_id: Optional[str]) -> Dict[str, Any]:
    """Classify user intent with fallback heuristics"""
    
    # Try Claude classification first
    classification_system = """You are a query classifier for a Polymarket analysis system.
Classify into: general_qa, bet_search, bet_info, dashboard_generation, or out_of_scope

- general_qa: Questions about how Polymarket works
- bet_search: Looking for bets/markets on a topic (e.g., "bets about AI", "show me crypto markets")
- bet_info: Asking about a specific bet/market (e.g., "tell me about market X")
- dashboard_generation: Requesting detailed analysis/dashboard
- out_of_scope: Unrelated to Polymarket

Respond with JSON: {"intent": "...", "reason": "...", "search_topic": "..." (only for bet_search)}"""

    classification_prompt = f"""Query: {query}
Market ID provided: {"Yes" if market_id else "No"}
Classify this query."""

    try:
        response = await call_claude(
            classification_system,
            classification_prompt,
            temperature=0.1,
            max_tokens=200
        )
        result = extract_first_json_block(response)
        if result and "intent" in result:
            return result
    except Exception as e:
        print(f"⚠️  Classification failed: {e}, using fallback...")
    
    # Fallback heuristics
    query_lower = query.lower()
    
    out_of_scope_keywords = ['weather', 'recipe', 'cook', 'movie', 'music']
    if any(k in query_lower for k in out_of_scope_keywords):
        if 'polymarket' not in query_lower:
            return {"intent": "out_of_scope", "reason": "unrelated topic"}
    
    # Check for bet search patterns
    bet_search_patterns = ['bets about', 'bets on', 'markets about', 'markets on', 
                          'show me', 'find', 'list', 'search for', 'what are']
    if any(pattern in query_lower for pattern in bet_search_patterns):
        # Extract search topic
        for pattern in bet_search_patterns:
            if pattern in query_lower:
                topic = query_lower.split(pattern)[1].strip().split()[0:3]
                return {"intent": "bet_search", "reason": "search request", 
                       "search_topic": " ".join(topic)}
    
    # Check for bet info patterns
    bet_info_patterns = ['tell me about', 'what is', 'information about', 'details on', 'info on']
    if any(pattern in query_lower for pattern in bet_info_patterns):
        if market_id:
            return {"intent": "bet_info", "reason": "info request with market_id"}
        else:
            return {"intent": "bet_search", "reason": "info request needs search", 
                   "search_topic": query_lower.split(bet_info_patterns[0])[1].strip() if bet_info_patterns[0] in query_lower else query}
    
    dashboard_keywords = ['analyze', 'dashboard', 'should i', 'risk', 'insight', 'analysis']
    if market_id or any(k in query_lower for k in dashboard_keywords):
        return {"intent": "dashboard_generation", "reason": "analysis request"}
    
    return {"intent": "general_qa", "reason": "general question"}


async def handle_general_qa(query: str, request_id: str) -> str:
    """Handle general Q&A - returns 3 sentences"""
    
    system_prompt = """You are a Polymarket expert assistant.
Answer in EXACTLY 3 sentences. Be clear and informative."""

    user_prompt = f"Question: {query}\n\nProvide a clear 3-sentence answer."
    
    print(f"[{request_id}] Handling general Q&A...")
    
    try:
        needs_data = any(k in query.lower() for k in ['current', 'latest', 'trending'])
        
        if needs_data:
            try:
                markets = await fetch_markets(limit=3)
                titles = [m.get('title', '')[:40] for m in markets[:3]]
                user_prompt += f"\n\nTrending: {titles}"
            except:
                pass
        
        response = await call_claude(system_prompt, user_prompt, temperature=0.3, max_tokens=300)
        return response.strip()
        
    except Exception as e:
        print(f"[{request_id}] ✗ Error: {e}")
        return "I apologize, but I'm having trouble processing your question. Polymarket is a prediction market platform where users trade on event outcomes. Please try rephrasing your question."


async def handle_bet_search(query: str, search_topic: str, request_id: str) -> Dict[str, Any]:
    """Search for bets/markets on a specific topic"""
    
    print(f"[{request_id}] Searching for bets about: {search_topic}")
    
    try:
        # Fetch markets from Polymarket API
        markets_raw = await fetch_markets(limit=20)
        
        # Ensure markets is a list and handle different response formats
        if isinstance(markets_raw, dict):
            markets = markets_raw.get('data', []) or markets_raw.get('markets', []) or []
        elif isinstance(markets_raw, list):
            markets = markets_raw
        else:
            markets = []
        
        if not markets:
            print(f"[{request_id}] ⚠️  No markets returned from API")
            return {
                "search_topic": search_topic,
                "count": 0,
                "markets": []
            }
        
        print(f"[{request_id}] Fetched {len(markets)} markets from API")
        
        # Build clean market list for Claude
        clean_markets = []
        for m in markets:
            if not isinstance(m, dict):
                continue
            clean_markets.append({
                'id': m.get('id', 'unknown'),
                'title': m.get('title', 'Untitled'),
                'description': (m.get('description') or '')[:200],
                'currentPrice': m.get('currentPrice', m.get('lastPrice', 0.5)),
                'volume24hr': m.get('volume24hr', m.get('volume', 0))
            })
        
        if not clean_markets:
            print(f"[{request_id}] ⚠️  No valid markets after cleaning")
            return {
                "search_topic": search_topic,
                "count": 0,
                "markets": []
            }
        
        # Filter markets by search topic using Claude
        system_prompt = """You are a market search assistant.
Given a list of prediction markets and a search topic, identify the most relevant markets.
Return ONLY a JSON array of market objects that match the topic."""

        user_prompt = f"""Search Topic: {search_topic}

Available Markets:
{json.dumps(clean_markets, indent=2)}

Return a JSON array of the 5-10 most relevant markets. Include id, title, description, currentPrice, volume24hr.
Output ONLY the JSON array."""

        print(f"[{request_id}] Filtering markets with Claude...")
        response = await call_claude(system_prompt, user_prompt, temperature=0.2, max_tokens=2000)
        
        filtered_markets = extract_first_json_block(response)
        
        if not filtered_markets or not isinstance(filtered_markets, list):
            # Fallback: simple keyword matching
            print(f"[{request_id}] Using fallback keyword matching...")
            filtered_markets = []
            topic_lower = search_topic.lower()
            for m in clean_markets[:15]:
                title = (m.get('title') or '').lower()
                desc = (m.get('description') or '').lower()
                if topic_lower in title or topic_lower in desc:
                    filtered_markets.append(m)
        
        print(f"[{request_id}] ✓ Found {len(filtered_markets)} relevant markets")
        
        return {
            "search_topic": search_topic,
            "count": len(filtered_markets),
            "markets": filtered_markets[:10]  # Limit to top 10
        }
        
    except Exception as e:
        print(f"[{request_id}] ✗ Search failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Bet search failed: {str(e)}")


async def handle_bet_info(query: str, market_id: str, request_id: str) -> Dict[str, Any]:
    """Get basic information about a specific bet"""
    
    print(f"[{request_id}] Fetching info for: {market_id}")
    
    try:
        # Fetch market details
        market = await fetch_market_detail(market_id)
        print(f"[{request_id}] ✓ Market: {market.get('title', '')[:50]}...")
        
        # Fetch related news
        try:
            news = await fetch_news_for_market(market.get("title", ""), page_size=5)
            print(f"[{request_id}] ✓ Found {len(news)} news articles")
        except:
            news = []
        
        # Generate summary using Claude
        system_prompt = """You are a prediction market information assistant.
Provide a clear, concise summary of a market in 3-4 paragraphs covering:
1. What the market is about
2. Current status (price, volume, trending)
3. Key factors or recent developments
4. Overall market sentiment"""

        user_prompt = f"""Market Information:
Title: {market.get('title', '')}
Description: {market.get('description', '')}
Current Price: {market.get('currentPrice', 0.5)}
Volume 24h: ${market.get('volume24hr', 0):,.0f}
End Date: {market.get('endDate', 'Unknown')}

Recent News ({len(news)} articles):
{json.dumps([{'title': n.get('title', ''), 'source': n.get('source', {}).get('name', '')} for n in news[:3]], indent=2)}

Provide a 3-4 paragraph summary of this market."""

        print(f"[{request_id}] Generating summary...")
        summary = await call_claude(system_prompt, user_prompt, temperature=0.3, max_tokens=600)
        
        print(f"[{request_id}] ✓ Info generated")
        
        return {
            "market_id": market_id,
            "title": market.get('title', ''),
            "description": market.get('description', ''),
            "currentPrice": market.get('currentPrice', 0.5),
            "volume24hr": market.get('volume24hr', 0),
            "endDate": market.get('endDate', 'Unknown'),
            "summary": summary.strip(),
            "news_count": len(news),
            "top_news": [
                {
                    "title": n.get('title', ''),
                    "source": n.get('source', {}).get('name', ''),
                    "publishedAt": n.get('publishedAt', '')
                } for n in news[:3]
            ]
        }
        
    except Exception as e:
        print(f"[{request_id}] ✗ Info fetch failed: {e}")
        raise HTTPException(status_code=404, detail=f"Could not fetch market info: {str(e)}")


async def handle_dashboard_generation(query: str, market_id: str, request_id: str) -> Dict[str, Any]:
    """Generate dashboard in EXACT required format"""
    
    print(f"[{request_id}] Generating dashboard for: {market_id}")
    
    # Fetch market data
    try:
        market = await fetch_market_detail(market_id)
        print(f"[{request_id}] ✓ Market: {market.get('title', '')[:50]}...")
    except Exception as e:
        print(f"[{request_id}] ✗ Market fetch failed: {e}")
        raise HTTPException(status_code=404, detail=f"Market not found: {market_id}")
    
    # Fetch news
    try:
        news = await fetch_news_for_market(market.get("title", ""), page_size=10)
        print(f"[{request_id}] ✓ Found {len(news)} news articles")
    except:
        news = []
    
    # MCP analysis
    mcp_payload = {
        "market_id": market.get("id"),
        "market": {
            "id": market.get("id"),
            "title": market.get("title"),
            "currentPrice": market.get("currentPrice", 0.5),
            "volume24hr": market.get("volume24hr", 0)
        },
        "recent_trades": market.get("recentTrades", []),
        "orderbook": market.get("orderbook", {}),
        "news": news,
        "meta": {"request_id": request_id}
    }
    
    print(f"[{request_id}] Running MCP analysis...")
    try:
        mcp_result = await call_mcp_with_payload(mcp_payload)
        print(f"[{request_id}] ✓ MCP complete")
    except:
        mcp_result = {"riskScore": 50}
    
    # Generate dashboard with Claude
    system_prompt = """You are a prediction market dashboard generator.

Generate a COMPLETE dashboard JSON object with realistic, coherent data.

CRITICAL:
1. Output ONLY valid JSON
2. Follow the EXACT schema
3. Generate realistic time-series data
4. Make data internally consistent
5. No explanations, just JSON"""

    # Format news for Claude
    news_info = []
    for article in news[:5]:
        news_info.append({
            "title": article.get("title", ""),
            "source": article.get("source", {}).get("name", "Unknown"),
            "publishedAt": article.get("publishedAt", "")
        })

    user_prompt = f"""Generate dashboard JSON for:

MARKET: {market.get('title', '')}
PRICE: {market.get('currentPrice', 0.5)}
VOLUME_24H: ${market.get('volume24hr', 0):,.0f}
RISK: {mcp_result.get('riskScore', 50)}/100

NEWS: {json.dumps(news_info, indent=2)}

Generate JSON with this EXACT structure:
{{
  "question": "{market.get('title', '')}",
  "healthScore": <0-100 int, inverse of risk>,
  "liquidityScore": <0-10 float based on volume>,
  
  "volumeData": {{
    "24h": [
      {{"time": "00:00", "volume": <num>}}, {{"time": "04:00", "volume": <num>}},
      {{"time": "08:00", "volume": <num>}}, {{"time": "12:00", "volume": <num>}},
      {{"time": "16:00", "volume": <num>}}, {{"time": "20:00", "volume": <num>}}
    ],
    "7d": [
      {{"time": "Mon", "volume": <num>}}, {{"time": "Tue", "volume": <num>}},
      {{"time": "Wed", "volume": <num>}}, {{"time": "Thu", "volume": <num>}},
      {{"time": "Fri", "volume": <num>}}, {{"time": "Sat", "volume": <num>}},
      {{"time": "Sun", "volume": <num>}}
    ],
    "1m": [
      {{"time": "Week 1", "volume": <num>}}, {{"time": "Week 2", "volume": <num>}},
      {{"time": "Week 3", "volume": <num>}}, {{"time": "Week 4", "volume": <num>}}
    ]
  }},
  
  "betOptions": ["yes", "no", "maybe"],
  
  "oddsComparison": {{
    "yes": {{"polymarket": <num>, "news": <num>, "expert": <num>}},
    "no": {{"polymarket": <num>, "news": <num>, "expert": <num>}},
    "maybe": {{"polymarket": <num>, "news": <num>, "expert": <num>}}
  }},
  
  "shiftTimeline": [
    {{"date": "Nov 1", "polymarket": <num>, "news": <num>}},
    {{"date": "Nov 2", "polymarket": <num>, "news": <num>}},
    {{"date": "Nov 3", "polymarket": <num>, "news": <num>}},
    {{"date": "Nov 4", "polymarket": <num>, "news": <num>}},
    {{"date": "Nov 5", "polymarket": <num>, "news": <num>}},
    {{"date": "Nov 6", "polymarket": <num>, "news": <num>}}
  ],
  
  "news": [
    {{"title": "<actual news title>", "url": "#", "source": "<source>", "date": "<time ago>"}},
    {{"title": "<actual news title>", "url": "#", "source": "<source>", "date": "<time ago>"}},
    {{"title": "<actual news title>", "url": "#", "source": "<source>", "date": "<time ago>"}}
  ],
  
  "largeBets": [
    {{"option": "Yes", "amount": "$<num>", "time": "<ago>", "impact": "+<num>%", "icon": "TrendingUp"}},
    {{"option": "No", "amount": "$<num>", "time": "<ago>", "impact": "-<num>%", "icon": "TrendingDown"}},
    {{"option": "Yes", "amount": "$<num>", "time": "<ago>", "impact": "+<num>%", "icon": "TrendingUp"}}
  ],
  
  "sentimentTimeline": [
    {{"date": "Nov 1", "sentiment": <num>, "events": "<event description>"}},
    {{"date": "Nov 3", "sentiment": <num>, "events": "<event description>"}},
    {{"date": "Nov 5", "sentiment": <num>, "events": "<event description>"}},
    {{"date": "Nov 7", "sentiment": <num>, "events": "<event description>"}}
  ],
  
  "aiSummary": [
    {{"title": "Market Confidence:", "content": "<2-3 sentences>"}},
    {{"title": "Trend Analysis:", "content": "<2-3 sentences>"}},
    {{"title": "Risk Assessment:", "content": "<2-3 sentences>"}},
    {{"title": "Strategic Recommendation:", "content": "<2-3 sentences>"}}
  ]
}}

Use actual news titles. Make volume/odds/sentiment realistic and coherent.
Output ONLY JSON."""

    print(f"[{request_id}] Generating dashboard JSON...")
    try:
        response = await call_claude(system_prompt, user_prompt, temperature=0.3, max_tokens=3500)
        dashboard = extract_first_json_block(response)
        
        if not dashboard or not isinstance(dashboard, dict):
            raise ValueError("Invalid JSON response")
        
        # Validate required fields
        required = ["question", "healthScore", "liquidityScore", "volumeData", 
                   "betOptions", "oddsComparison", "shiftTimeline", "news",
                   "largeBets", "sentimentTimeline", "aiSummary"]
        missing = [f for f in required if f not in dashboard]
        if missing:
            raise ValueError(f"Missing fields: {missing}")
        
        print(f"[{request_id}] ✓ Dashboard complete")
        print(f"[{request_id}]   Health: {dashboard['healthScore']}/100")
        print(f"[{request_id}]   Liquidity: {dashboard['liquidityScore']}/10")
        
        return dashboard
        
    except Exception as e:
        print(f"[{request_id}] ✗ Generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Dashboard generation failed: {str(e)}")


@app.post("/chat")
async def post_chat(payload: Dict[str, Any]):
    """Main chat endpoint with simple caching"""
    request_id = short_id()
    start_ts = time.time()
    
    query = payload.get("query") or payload.get("text")
    if not query:
        raise HTTPException(status_code=400, detail="Missing 'query' field")
    
    market_id = payload.get("market_id")
    
    print(f"\n[{request_id}] Chat: {query}")
    
    # CHECK CACHE FIRST
    cached = get_cached(query)
    if cached:
        elapsed = time.time() - start_ts
        print(f"[{request_id}] ✓ Returned from cache in {elapsed:.2f}s\n")
        return cached
    
    # NOT IN CACHE - PROCESS NORMALLY
    if market_id:
        print(f"[{request_id}] Market ID provided: {market_id}")
    
    # Classify intent FIRST (before resolving market_id)
    classification = await classify_chat_intent(query, market_id)
    intent = classification.get("intent", "general_qa")
    search_topic = classification.get("search_topic", "")
    
    print(f"[{request_id}] Intent: {intent}")
    if search_topic:
        print(f"[{request_id}] Search topic: {search_topic}")
    
    # If no market_id provided but intent suggests we need one, try to resolve it
    if not market_id and intent in ["bet_info", "dashboard_generation"]:
        print(f"[{request_id}] No market_id provided, attempting resolution...")
        resolved_id = await resolve_market_id(query, request_id)
        if resolved_id:
            market_id = resolved_id
            print(f"[{request_id}] ✓ Using resolved market_id: {market_id}")
        else:
            print(f"[{request_id}] Could not resolve market_id, may switch to search...")
    
    try:
        response = None
        
        if intent == "out_of_scope":
            response = {
                "type": "error",
                "message": "I'm designed to help with Polymarket-related questions and market analysis. Please ask about prediction markets or request market analysis."
            }
        
        elif intent == "general_qa":
            answer = await handle_general_qa(query, request_id)
            response = {"type": "chat", "response": answer}
        
        elif intent == "bet_search":
            if not search_topic:
                search_topic = query
            
            search_results = await handle_bet_search(query, search_topic, request_id)
            response = {"type": "bet_search", "data": search_results}
        
        elif intent == "bet_info":
            if not market_id:
                # If we still don't have a market_id, try searching
                print(f"[{request_id}] No market_id available, falling back to search...")
                search_results = await handle_bet_search(query, query, request_id)
                
                if search_results['count'] > 0:
                    response = {
                        "type": "bet_search",
                        "data": search_results,
                        "message": "I found these markets. Please specify which one you'd like to know more about."
                    }
                else:
                    response = {
                        "type": "error",
                        "message": "I couldn't find a market matching your query. Please try rephrasing or provide a market_id."
                    }
            else:
                info = await handle_bet_info(query, market_id, request_id)
                response = {"type": "bet_info", "data": info}
        
        elif intent == "dashboard_generation":
            if not market_id:
                # Try searching first
                print(f"[{request_id}] No market_id for dashboard, trying search...")
                search_results = await handle_bet_search(query, query, request_id)
                
                if search_results['count'] > 0:
                    response = {
                        "type": "bet_search",
                        "data": search_results,
                        "message": "I found these markets. Please specify which one you'd like a dashboard for."
                    }
                else:
                    response = {
                        "type": "error",
                        "message": "To generate a dashboard, please provide a market_id or specify which market you'd like analyzed."
                    }
            else:
                dashboard = await handle_dashboard_generation(query, market_id, request_id)
                response = {"type": "dashboard", "data": dashboard}
        
        else:
            raise HTTPException(status_code=500, detail="Unknown intent")
        
        # STORE IN CACHE
        set_cache(query, response)
        
        elapsed = time.time() - start_ts
        print(f"[{request_id}] ✓ Completed in {elapsed:.2f}s\n")
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[{request_id}] ✗ Failed: {e}\n")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/search")
async def get_search(topic: str = Query(..., description="Search topic (e.g., 'AI', 'crypto', 'politics')")):
    """
    Search for bets/markets on a specific topic
    
    Returns: {"topic": "...", "count": N, "markets": [...]}
    """
    request_id = short_id()
    print(f"\n[{request_id}] Search request: {topic}")
    
    try:
        results = await handle_bet_search(
            query=f"Find bets about {topic}",
            search_topic=topic,
            request_id=request_id
        )
        
        return {
            "request_id": request_id,
            "timestamp": utc_now_iso(),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/bet/{market_id}")
async def get_bet_info(market_id: str):
    """
    Get information about a specific bet
    
    Returns: {"title": "...", "summary": "...", "currentPrice": ..., ...}
    """
    request_id = short_id()
    print(f"\n[{request_id}] Bet info request: {market_id}")
    
    try:
        info = await handle_bet_info(
            query=f"Get info for {market_id}",
            market_id=market_id,
            request_id=request_id
        )
        
        return {
            "request_id": request_id,
            "timestamp": utc_now_iso(),
            "info": info
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/dashboard")
async def get_dashboard(market_id: str = Query(...)):
    """Direct dashboard endpoint"""
    request_id = short_id()
    print(f"\n[{request_id}] Dashboard request: {market_id}")
    
    try:
        dashboard = await handle_dashboard_generation(
            query=f"Generate dashboard for {market_id}",
            market_id=market_id,
            request_id=request_id
        )
        
        return {
            "request_id": request_id,
            "timestamp": utc_now_iso(),
            "dashboard": dashboard,
            "status": "ok"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    """Health check"""
    import os
    from mcp import _mcp_manager
    
    cache = load_cache()
    
    return {
        "ok": True,
        "ts": utc_now_iso(),
        "services": {
            "claude_api_key": bool(os.getenv("CLAUDE_API_KEY")),
            "mcp_initialized": _mcp_manager.initialized
        },
        "cache": {
            "entries": len(cache)
        }
    }


@app.post("/cache/clear")
async def clear_cache_endpoint():
    """Clear the entire cache"""
    save_cache({})
    print("🗑️ Cache cleared")
    return {"message": "Cache cleared successfully", "timestamp": utc_now_iso()}


@app.get("/")
async def root():
    """API info"""
    return {
        "service": "PolySage API",
        "version": "4.1-enhanced",
        "features": [
            "General Q&A about Polymarket",
            "Bet search by topic",
            "Bet information retrieval",
            "Full dashboard generation",
            "Automatic market ID resolution from titles ⭐ NEW",
            "Claude Sonnet 4.5 powered",
            "MCP integration"
        ],
        "chat_types": {
            "general_qa": "Ask questions about Polymarket - get 3-sentence answers",
            "bet_search": "Search for bets on a topic - get list of relevant markets",
            "bet_info": "Get information about a specific bet - get summary and details",
            "dashboard_generation": "Request detailed analysis - get full dashboard JSON"
        },
        "endpoints": {
            "POST /chat": "Main endpoint - handles all query types (auto-resolves market IDs)",
            "GET /search?topic=X": "Search for bets on topic X",
            "GET /bet/{market_id}": "Get info about specific bet",
            "GET /dashboard?market_id=X": "Generate dashboard for market",
            "GET /health": "Health check"
        },
        "example_queries": {
            "general": "How does Polymarket work?",
            "search": "Show me bets about AI",
            "info_by_title": "Tell me about 'Will GPT-5 be released in 2025?' ⭐ NEW - No market_id needed!",
            "info_by_id": "Tell me about market abc123",
            "dashboard_by_title": "Analyze 'Will Bitcoin reach $100k?' ⭐ NEW",
            "dashboard_by_id": "Analyze market abc123"
        },
        "smart_features": {
            "title_resolution": "Just mention the market title - system finds the market_id automatically",
            "fuzzy_matching": "Works even with partial titles",
            "fallback_search": "If exact match not found, returns similar markets to choose from"
        }
    }