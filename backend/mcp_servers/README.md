# REAL DATA SETUP INSTRUCTIONS

## Step 1: Get API Keys (5 minutes)

### Anthropic API Key
1. Go to: https://console.anthropic.com/
2. Sign up/Login
3. Go to "API Keys"
4. Click "Create Key"
5. Copy the key (starts with `sk-ant-api03-`)

### NewsAPI Key
1. Go to: https://newsapi.org/register
2. Fill in:
   - Email
   - Password
   - Use case: "Research project"
3. Click "Submit"
4. Check email for API key
5. Copy the key (32 character string)

## Step 2: Add Keys to .env
```bash
cd backend
nano .env  # or use VS Code
```

Add your keys:
```env
ANTHROPIC_API_KEY=sk-ant-api03-YOUR_KEY_HERE
NEWS_API_KEY=YOUR_NEWSAPI_KEY_HERE
```

Save and exit.

## Step 3: Test Everything
```bash
cd mcp_servers

# Test Polymarket server (no key needed!)
python polymarket_server/server.py

# Should see:
# 🚀 Starting Polymarket MCP Server (REAL DATA)
# 📡 Connected to Polymarket CLOB API

# Press Ctrl+C, then test News server
python news_server/server.py

# Should see:
# 🚀 Starting News MCP Server (REAL DATA)
# 📰 Connected to NewsAPI with key: ...abc123
```

## Step 4: Find Real Market IDs

Polymarket uses condition IDs (long hex strings). To find them:

### Method 1: Use search_markets tool
```python
# The search tool finds real markets for you!
```

### Method 2: Browse Polymarket website
1. Go to https://polymarket.com/
2. Click any market
3. URL will be: `https://polymarket.com/event/NAME?id=CONDITION_ID`
4. Copy the CONDITION_ID

### Example Real Market IDs:
- Trump 2024: Check polymarket.com for current ID
- Bitcoin: Check polymarket.com for current ID

## What Data is REAL:

✅ Polymarket Server:
- ALL market data from CLOB API
- ALL trade history from blockchain
- ALL volume calculations from actual trades
- ALL trader addresses from real wallets
- ALL health scores from real metrics

✅ News Server:
- ALL articles from NewsAPI
- ALL publication times real
- ALL sources real (Reuters, Bloomberg, etc.)
- ALL sentiment from actual article text

## Testing with Real Data
```bash
# Run test with real market
python test_quick.py

# This will call REAL APIs and return REAL data!
```

## Troubleshooting

### "NEWS_API_KEY not found"
→ Make sure .env file is in `backend/` directory
→ Make sure you added NEWS_API_KEY=your_key

### "NewsAPI rate limit exceeded"
→ Free tier = 100 requests/day
→ Wait 24 hours or upgrade

### "Invalid market ID"
→ Use search_markets tool to find valid IDs
→ Or copy from polymarket.com URLs

## Data Sources Confirmed Real

- Polymarket: https://clob.polymarket.com (Public API)
- News: https://newsapi.org (Your account)
- All blockchain data: Polygon network

## You're Done!
