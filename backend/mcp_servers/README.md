# Polymarket Manipulation Detection - MCP Servers

This directory contains Model Context Protocol (MCP) servers that provide Claude with tools to analyze Polymarket markets for potential manipulation.

## Overview

Two MCP servers provide 11 total tools for comprehensive market analysis:

### Polymarket Server (6 tools)
- Market data fetching
- Volume anomaly detection
- Wash trading detection
- Health score calculation
- Trader concentration analysis
- Historical pattern matching

### News Server (5 tools)
- News article fetching
- Sentiment analysis
- News-price correlation
- Trading/news volume comparison
- Breaking news alerts

## Quick Start

### Installation
```bash
cd backend/mcp_servers
pip install -r requirements.txt
```

### Running Servers
```bash
# Polymarket Server
python polymarket_server/server.py

# News Server
python news_server/server.py
```

### Testing
```bash
# Run test suite
python tests/test_servers.py
```

## Architecture
```
MCP Servers
    ↓
Claude API (with tools enabled)
    ↓
Backend API
    ↓
Frontend Dashboard
```

## Tool Catalog

### Polymarket Server Tools

#### 1. get_market_data
Fetches current market information.

**Input:**
```json
{
  "market_id": "trump-2024"
}
```

**Output:** Price, volume, liquidity, trader count, etc.

#### 2. analyze_volume_anomaly
Detects unusual trading volume spikes.

**Input:**
```json
{
  "market_id": "trump-2024",
  "timeframe": "24h"
}
```

**Output:** Z-score, severity assessment, anomaly detection

#### 3. detect_wash_trading
Identifies potential wash trading patterns.

**Input:**
```json
{
  "market_id": "trump-2024",
  "lookback_hours": 24
}
```

**Output:** Suspicious wallet pairs, confidence level

#### 4. calculate_health_score
Calculates overall market health (0-100).

**Input:**
```json
{
  "market_id": "trump-2024"
}
```

**Output:** Overall score, component scores, risk level

#### 5. get_trader_concentration
Analyzes trader distribution.

**Input:**
```json
{
  "market_id": "trump-2024"
}
```

**Output:** Gini coefficient, top trader percentages

#### 6. get_historical_patterns
Finds similar past manipulation cases.

**Input:**
```json
{
  "pattern_type": "volume_spike"
}
```

**Output:** Similar historical cases with similarity scores

### News Server Tools

#### 1. get_market_related_news
Fetches news articles for a topic.

**Input:**
```json
{
  "topic": "Trump 2024",
  "timeframe": "24h"
}
```

**Output:** List of articles with summaries

#### 2. analyze_news_sentiment
Analyzes news sentiment.

**Input:**
```json
{
  "topic": "Trump 2024",
  "timeframe": "24h"
}
```

**Output:** Sentiment breakdown, confidence level

#### 3. correlate_news_to_price
Checks if price moves align with news.

**Input:**
```json
{
  "market_id": "trump-2024",
  "price_change_time": "2024-11-08T12:00:00Z",
  "window_minutes": 30
}
```

**Output:** Correlation score, red flags

#### 4. compare_news_trading_volume
Detects disproportionate trading vs news.

**Input:**
```json
{
  "market_id": "trump-2024",
  "timeframe": "24h"
}
```

**Output:** Volume-to-news ratio, anomaly assessment

#### 5. get_breaking_news
Gets breaking news alerts.

**Input:**
```json
{
  "categories": ["politics", "crypto"]
}
```

**Output:** Recent breaking news with market impact

## For API Team

### Integration

Use the `mcp_config.json` file in `backend/` directory:
```json
{
  "mcpServers": {
    "polymarket-analysis": {
      "command": "python",
      "args": ["backend/mcp_servers/polymarket_server/server.py"]
    },
    "news-analysis": {
      "command": "python",
      "args": ["backend/mcp_servers/news_server/server.py"]
    }
  }
}
```

### Example Usage with Claude
```python
import anthropic

client = anthropic.Anthropic(api_key="your_key")

# Define MCP tools
tools = [
    {
        "name": "get_market_data",
        "description": "Fetch market data",
        "input_schema": {...}
    },
    # ... more tools
]

# Call Claude with tools
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4000,
    tools=tools,
    messages=[{
        "role": "user",
        "content": "Analyze the Trump 2024 market for manipulation"
    }]
)

# Claude will automatically call your MCP tools as needed
```

## Development

### Current Status
✅ All tools implemented with mock data
✅ Servers tested and working
✅ Ready for API integration

### Next Steps (Optional)
- [ ] Replace mock data with real Polymarket API
- [ ] Integrate NewsAPI for real news data
- [ ] Add database for historical patterns
- [ ] Implement caching layer

## Troubleshooting

### Server won't start
```bash
# Check Python version (need 3.9+)
python --version

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Tools not responding
```bash
# Run test suite
python tests/test_servers.py

# Check server logs
python polymarket_server/server.py 2>&1 | tee server.log
```

## Contact

For questions or issues with MCP servers:
- Your Name: [your-email]
- Branch: `mcp-servers`
- Status: ✅ Ready for integration