# PolySage

AI-powered prediction market analysis platform using Claude and MCP servers to detect manipulation and provide investment insights.

## Quick Start

### Prerequisites

- Python 3.11+
- Node 18+
- Claude API key
- NewsAPI key

### Backend Setup

```bash
cd backend

# Create .env
cat > .env << EOF
CLAUDE_API_KEY=your_claude_key
NEWS_API_KEY=your_news_key
CLAUDE_API_URL=https://api.anthropic.com/v1/messages
CLAUDE_MODEL=claude-sonnet-4-20250514
NEWS_API_URL=https://newsapi.org/v2
POLY_API_URL=https://clob.polymarket.com
EOF

# Install dependencies
pip install -r api/requirements.txt
pip install -r mcp_servers/requirements.txt

# Start API
cd api
uvicorn main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install
npm install

# Start
npm start
```

## Architecture

```
React Frontend → FastAPI Backend → MCP Servers (11 tools) → External APIs
                      ↓
                 Claude API (Analysis + Transform)
```

**MCP Servers:**
- Polymarket Server: 6 tools (volume analysis, wash trading detection, health scoring)
- News Server: 5 tools (sentiment analysis, news correlation)

## API Endpoints

- `POST /chat` - Analyze market with query
- `GET /dashboard?market_id=X` - Get dashboard data
- `GET /health` - Check service status

## Project Structure

```
backend/
├── api/
│   ├── main.py                   # FastAPI app
│   ├── mcp.py                    # MCP manager
│   ├── dashboard_processor.py    # Claude transformer
│   └── clients.py                # API clients
└── mcp_servers/
    ├── polymarket_server/        # 6 analysis tools
    └── news_server/              # 5 news tools

frontend/
└── src/
    ├── components/
    │   ├── Chat/
    │   └── Dashboard/
    └── hooks/
```

## Tech Stack

**Backend:** FastAPI, MCP SDK, Claude API, aiohttp  
**Frontend:** React, TailwindCSS, Recharts  
**Data:** Polymarket CLOB API, NewsAPI

## Features

- Real-time manipulation detection
- Market health scoring (0-100)
- Volume anomaly detection
- Wash trading detection
- News sentiment correlation
- AI-powered insights
- Interactive dashboard

## License

MIT
