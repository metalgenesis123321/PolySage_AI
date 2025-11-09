
import os
import json
import httpx
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
import requests
load_dotenv()
# API Configuration
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"
CLAUDE_MODEL = "claude-sonnet-4-20250514"  # or claude-3-5-sonnet-20241022

POLY_API_URL = os.getenv("POLY_API_URL", "https://clob.polymarket.com/")
NEWS_API_URL = os.getenv("NEWS_API_URL", "https://newsapi.org/v2/")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")


# Generic HTTP helper
async def _post(url: str, payload: dict, headers: dict = None, timeout: float = 10.0):
    """Generic POST request helper"""
    headers = headers or {}
    async with httpx.AsyncClient(timeout=timeout) as c:
        r = await c.post(url, json=payload, headers=headers)
        r.raise_for_status()
        return r.json()


async def _get(url: str, params: dict = None, headers: dict = None, timeout: float = 10.0):
    """Generic GET request helper"""
    headers = headers or {}
    params = params or {}
    async with httpx.AsyncClient(timeout=timeout) as c:
        r = await c.get(url, params=params, headers=headers)
        r.raise_for_status()
        return r.json()


# ============================================================================
# CLAUDE API - CORRECTED IMPLEMENTATION
# ============================================================================

async def call_claude(
    system_prompt: str,
    user_prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.0,
    max_tokens: int = 800
) -> str:
    """
    Call Claude API with CORRECT Anthropic format
    
    Args:
        system_prompt: System instructions (separate parameter in Claude API)
        user_prompt: User message
        model: Model name (defaults to CLAUDE_MODEL)
        temperature: 0.0 to 1.0
        max_tokens: Max response tokens
        
    Returns:
        Claude's text response
        
    Raises:
        ValueError: If API key not configured or API returns error
    """
    if not CLAUDE_API_KEY:
        raise ValueError("CLAUDE_API_KEY environment variable not set")
    if not CLAUDE_API_URL:
        raise ValueError("CLAUDE_API_URL not configured")
    
    # CORRECT: Anthropic Claude API format
    payload = {
        "model": model or CLAUDE_MODEL,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system_prompt,  # System prompt is separate, NOT in messages
        "messages": [
            {"role": "user", "content": user_prompt}  # Only user/assistant roles
        ]
    }
    
    # CORRECT: Anthropic API headers
    headers = {
        "x-api-key": CLAUDE_API_KEY,  # Use x-api-key, NOT Authorization: Bearer
        "anthropic-version": "2023-06-01",  # Required header
        "content-type": "application/json"
    }
    try:
        response = requests.post(CLAUDE_API_URL, data = json.dumps(payload), headers=headers)
        if response.status_code == 201:  # 201 Created is a common status for successful POST
            print("Resource created successfully!")
            print("Response:", response.json())
        else:
            print(f"Failed to create resource. Status code: {response.status_code}")
            print("Response:", response.text)
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
    try:
        # Use the _post helper
        resp = await _post(CLAUDE_API_URL, payload, headers=headers, timeout=30.0)
        
        # CORRECT: Parse Anthropic response format
        # Response structure:
        # {
        #   "id": "msg_...",
        #   "type": "message",
        #   "role": "assistant",
        #   "content": [
        #     {
        #       "type": "text",
        #       "text": "The actual response text here"
        #     }
        #   ],
        #   "model": "claude-sonnet-4-20250514",
        #   "stop_reason": "end_turn",
        #   "usage": {...}
        # }
        
        if isinstance(resp, dict) and "content" in resp:
            if len(resp["content"]) > 0:
                first_block = resp["content"][0]
                if isinstance(first_block, dict) and first_block.get("type") == "text":
                    return first_block.get("text", "")
        
        # If we get here, response format was unexpected
        raise ValueError(f"Unexpected Claude API response format: {json.dumps(resp)[:200]}")
        
    except httpx.HTTPStatusError as e:
        # More detailed error message
        error_body = ""
        try:
            error_body = e.response.json()
        except:
            error_body = e.response.text
        
        raise ValueError(
            f"Claude API error {e.response.status_code}: {error_body}"
        )
    except httpx.HTTPError as e:
        raise ValueError(f"HTTP error calling Claude API: {str(e)}")
    except Exception as e:
        raise ValueError(f"Unexpected error calling Claude API: {str(e)}")


# ============================================================================
# POLYMARKET API
# ============================================================================

async def fetch_markets(limit: int = 10) -> List[Dict[str, Any]]:
    """Fetch trending markets from Polymarket"""
    try:
        url = f"{POLY_API_URL}/markets"
        params = {"limit": limit, "active": "true"}
        return await _get(url, params=params, timeout=10.0)
    except Exception as e:
        print(f"Error fetching markets: {e}")
        return []


async def fetch_market_detail(market_id: str) -> Dict[str, Any]:
    """Fetch detailed market information"""
    try:
        url = f"{POLY_API_URL}markets/{market_id}"
        return await _get(url, timeout=10.0)
    except Exception as e:
        raise ValueError(f"Failed to fetch market {market_id}: {e}")


# ============================================================================
# NEWS API
# ============================================================================

async def fetch_news_for_market(query: str, page_size: int = 5) -> List[Dict[str, Any]]:
    """Fetch news articles related to a market query"""
    if not NEWS_API_KEY:
        print("NEWS_API_KEY not configured, skipping news fetch")
        return []
    
    try:
        url = f"{NEWS_API_URL}everything"
        params = {
            "q": query,
            "pageSize": page_size,
            "sortBy": "publishedAt",
            "language": "en"
        }
        headers = {"X-Api-Key": NEWS_API_KEY}
        
        result = await _get(url, params=params, headers=headers, timeout=10.0)
        return result.get("articles", [])
    except Exception as e:
        print(f"Error fetching news: {e}")
        return []


async def fetch_latest_news(limit: int = 10) -> List[Dict[str, Any]]:
    """Fetch latest news headlines"""
    if not NEWS_API_KEY:
        return []
    
    try:
        url = f"{NEWS_API_URL}top-headlines"
        params = {
            "pageSize": limit,
            "language": "en",
            "category": "general"
        }
        headers = {"X-Api-Key": NEWS_API_KEY}
        
        result = await _get(url, params=params, headers=headers, timeout=10.0)
        return result.get("articles", [])
    except Exception as e:
        print(f"Error fetching latest news: {e}")
        return []


# ============================================================================
# VALIDATION HELPERS
# ============================================================================

def validate_api_keys() -> Dict[str, bool]:
    """Check which API keys are configured"""
    return {
        "claude": bool(CLAUDE_API_KEY),
        "news": bool(NEWS_API_KEY),
        "polymarket": bool(POLY_API_URL)
    }


def get_api_status() -> Dict[str, Any]:
    """Get detailed API configuration status"""
    keys = validate_api_keys()
    
    return {
        "configured": keys,
        "claude_model": CLAUDE_MODEL,
        "endpoints": {
            "claude": CLAUDE_API_URL,
            "polymarket": POLY_API_URL,
            "news": NEWS_API_URL
        },
        "all_ready": all(keys.values())
    }


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test_claude():
        """Test Claude API with correct format"""
        try:
            print("Testing Claude API...")
            response = await call_claude(
                system_prompt="You are a helpful assistant.",
                user_prompt="What is 2+2? Answer in one sentence.",
                temperature=0.3,
                max_tokens=100
            )
            print(f"✓ Claude response: {response}")
        except Exception as e:
            print(f"✗ Claude API test failed: {e}")
    
    async def test_polymarket():
        """Test Polymarket API"""
        try:
            print("\nTesting Polymarket API...")
            markets = await fetch_markets(limit=3)
            print(f"✓ Fetched {len(markets)} markets")
            if markets:
                print(f"  First market: {markets[0].get('title', 'N/A')[:50]}...")
        except Exception as e:
            print(f"✗ Polymarket API test failed: {e}")
    
    async def test_all():
        """Run all tests"""
        print("="*60)
        print("API Configuration Test")
        print("="*60)
        
        status = get_api_status()
        print(f"\nConfigured APIs: {status['configured']}")
        print(f"All ready: {status['all_ready']}")
        
        print("\n" + "="*60)
        await test_claude()
        await test_polymarket()
        print("="*60)
    
    # Run tests
    asyncio.run(test_all())