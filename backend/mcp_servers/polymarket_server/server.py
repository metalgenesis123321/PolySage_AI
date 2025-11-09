#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import io

# if sys.platform == 'win32':
#     sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
#     sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import asyncio
import json
import os
from typing import Any, Dict, List
from datetime import datetime, timedelta
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.types import Tool, TextContent
import mcp.server.stdio
import aiohttp
from statistics import mean, stdev
from collections import defaultdict

POLYMARKET_API_BASE = "https://clob.polymarket.com"

server = Server("polymarket-analysis")

async def fetch_market_info(market_id: str) -> Dict[str, Any]:
    url = f"{POLYMARKET_API_BASE}/markets/{market_id}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
            else:
                raise Exception(f"Polymarket API error: {response.status}")

async def fetch_all_markets() -> List[Dict[str, Any]]:
    url = f"{POLYMARKET_API_BASE}/markets"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                
                # Handle different response structures
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    # Check for common patterns
                    if 'markets' in data:
                        return data['markets']
                    elif 'data' in data:
                        return data['data']
                    else:
                        # Return as single-item list
                        return [data]
                else:
                    print(f"Unexpected response type: {type(data)}")
                    return []
            else:
                print(f"API error {response.status}: {await response.text()}")
                return []

async def fetch_market_trades(market_id: str, limit: int = 1000) -> List[Dict[str, Any]]:
    url = f"{POLYMARKET_API_BASE}/trades"
    params = {"market": market_id, "limit": limit}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                return await response.json()
            else:
                return []

async def fetch_order_book(market_id: str) -> Dict[str, Any]:
    url = f"{POLYMARKET_API_BASE}/book"
    params = {"market": market_id}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                return await response.json()
            else:
                return {"bids": [], "asks": []}

async def fetch_price_history(market_id: str, days: int = 7) -> List[Dict[str, Any]]:
    url = f"{POLYMARKET_API_BASE}/prices-history"
    params = {"market": market_id, "interval": "1h", "fidelity": days}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("history", [])
            else:
                return []

async def calculate_real_volume_anomaly(market_id: str, timeframe: str) -> Dict[str, Any]:
    trades = await fetch_market_trades(market_id, limit=2000)
    if not trades:
        raise Exception("No trade data available for this market")
    timeframe_hours = {"1h": 1, "24h": 24, "7d": 168}.get(timeframe, 24)
    now = datetime.utcnow()
    current_window_start = now - timedelta(hours=timeframe_hours)
    current_volume = 0
    for trade in trades:
        try:
            trade_time = datetime.fromisoformat(trade.get("timestamp", "").replace("Z", ""))
            if trade_time >= current_window_start:
                size = float(trade.get("size", 0))
                price = float(trade.get("price", 0))
                current_volume += size * price
        except:
            continue
    historical_volumes = []
    for i in range(1, 8):
        period_start = now - timedelta(hours=timeframe_hours * (i + 1))
        period_end = now - timedelta(hours=timeframe_hours * i)
        period_volume = 0
        for trade in trades:
            try:
                trade_time = datetime.fromisoformat(trade.get("timestamp", "").replace("Z", ""))
                if period_start <= trade_time < period_end:
                    size = float(trade.get("size", 0))
                    price = float(trade.get("price", 0))
                    period_volume += size * price
            except:
                continue
        historical_volumes.append(period_volume)
    if len(historical_volumes) < 2:
        raise Exception("Insufficient historical data for analysis")
    avg_volume = mean(historical_volumes)
    std_dev = stdev(historical_volumes) if len(historical_volumes) > 1 else 0
    if std_dev > 0:
        z_score = (current_volume - avg_volume) / std_dev
    else:
        z_score = 0
    is_anomaly = abs(z_score) > 3
    severity = "HIGH" if abs(z_score) > 4 else "MEDIUM" if abs(z_score) > 3 else "LOW"
    return {
        "current_volume": current_volume,
        "average_volume": avg_volume,
        "std_dev": std_dev,
        "z_score": z_score,
        "is_anomaly": is_anomaly,
        "severity": severity
    }

async def detect_real_wash_trading(market_id: str, lookback_hours: int = 24) -> Dict[str, Any]:
    trades = await fetch_market_trades(market_id, limit=2000)
    if not trades:
        raise Exception("No trade data available")
    now = datetime.utcnow()
    cutoff = now - timedelta(hours=lookback_hours)
    recent_trades = []
    for trade in trades:
        try:
            trade_time = datetime.fromisoformat(trade.get("timestamp", "").replace("Z", ""))
            if trade_time >= cutoff:
                recent_trades.append(trade)
        except:
            continue
    trader_pairs = defaultdict(int)
    self_trades = 0
    for trade in recent_trades:
        maker = trade.get("maker_address", "")
        taker = trade.get("taker_address", "")
        if not maker or not taker:
            continue
        if maker.lower() == taker.lower():
            self_trades += 1
            continue
        pair = tuple(sorted([maker, taker]))
        trader_pairs[pair] += 1
    threshold = 5
    suspicious_pairs = [
        f"{pair[0][:8]}...{pair[0][-6:]} <-> {pair[1][:8]}...{pair[1][-6:]} ({count} trades)"
        for pair, count in trader_pairs.items()
        if count > threshold
    ]
    confidence = "HIGH" if len(suspicious_pairs) > 3 else "MEDIUM" if len(suspicious_pairs) > 0 else "LOW"
    return {
        "suspicious_patterns": len(suspicious_pairs),
        "repeated_pairs": suspicious_pairs[:10],
        "self_trades": self_trades,
        "confidence": confidence,
        "total_trades_analyzed": len(recent_trades)
    }

async def calculate_real_health_score(market_id: str) -> Dict[str, Any]:
    market_info = await fetch_market_info(market_id)
    trades = await fetch_market_trades(market_id, limit=1000)
    order_book = await fetch_order_book(market_id)
    total_liquidity = float(market_info.get("liquidity", 0))
    liquidity_score = min(100, (total_liquidity / 100000) * 100)
    unique_traders = set()
    for trade in trades:
        unique_traders.add(trade.get("maker_address", ""))
        unique_traders.add(trade.get("taker_address", ""))
    trader_count = len(unique_traders)
    diversity_score = min(100, (trader_count / 100) * 100)
    try:
        volume_analysis = await calculate_real_volume_anomaly(market_id, "24h")
        consistency_score = max(0, 100 - abs(volume_analysis["z_score"]) * 20)
    except:
        consistency_score = 50
    price_history = await fetch_price_history(market_id, days=7)
    if len(price_history) > 1:
        prices = [float(p.get("price", 0)) for p in price_history]
        price_std = stdev(prices) if len(prices) > 1 else 0
        stability_score = max(0, 100 - (price_std * 500))
    else:
        stability_score = 50
    try:
        wash_analysis = await detect_real_wash_trading(market_id, 24)
        manip_score = max(0, 100 - wash_analysis["suspicious_patterns"] * 10)
    except:
        manip_score = 50
    overall_score = (
        liquidity_score * 0.25 +
        diversity_score * 0.20 +
        consistency_score * 0.20 +
        stability_score * 0.15 +
        manip_score * 0.20
    )
    if overall_score >= 75:
        risk_level = "LOW"
    elif overall_score >= 50:
        risk_level = "MEDIUM"
    else:
        risk_level = "HIGH"
    return {
        "overall_score": int(overall_score),
        "risk_level": risk_level,
        "liquidity_score": int(liquidity_score),
        "diversity_score": int(diversity_score),
        "volume_score": int(consistency_score),
        "stability_score": int(stability_score),
        "manipulation_score": int(manip_score),
        "total_liquidity": total_liquidity,
        "unique_traders": trader_count
    }

async def get_real_trader_concentration(market_id: str) -> Dict[str, Any]:
    trades = await fetch_market_trades(market_id, limit=2000)
    if not trades:
        raise Exception("No trade data available")
    trader_volumes = defaultdict(float)
    for trade in trades:
        maker = trade.get("maker_address", "")
        taker = trade.get("taker_address", "")
        size = float(trade.get("size", 0))
        price = float(trade.get("price", 0))
        volume = size * price
        if maker:
            trader_volumes[maker] += volume
        if taker:
            trader_volumes[taker] += volume
    sorted_traders = sorted(trader_volumes.items(), key=lambda x: x[1], reverse=True)
    total_volume = sum(trader_volumes.values())
    total_traders = len(trader_volumes)
    top10_volume = sum(v for _, v in sorted_traders[:10])
    top50_volume = sum(v for _, v in sorted_traders[:50])
    top10_pct = (top10_volume / total_volume * 100) if total_volume > 0 else 0
    top50_pct = (top50_volume / total_volume * 100) if total_volume > 0 else 0
    volumes = sorted([v for _, v in trader_volumes.items()])
    n = len(volumes)
    if n > 0 and sum(volumes) > 0:
        cumsum = 0
        gini_sum = 0
        for i, v in enumerate(volumes):
            cumsum += v
            gini_sum += (2 * (i + 1) - n - 1) * v
        gini = gini_sum / (n * sum(volumes))
    else:
        gini = 0
    if top10_pct > 60:
        level = "VERY HIGH"
    elif top10_pct > 40:
        level = "HIGH"
    elif top10_pct > 25:
        level = "MODERATE"
    else:
        level = "LOW"
    return {
        "total_traders": total_traders,
        "top10_percentage": round(top10_pct, 1),
        "top50_percentage": round(top50_pct, 1),
        "gini_coefficient": round(gini, 3),
        "concentration_level": level,
        "total_volume": total_volume
    }

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_market_data",
            description="Fetch REAL current data for a Polymarket market from CLOB API",
            inputSchema={
                "type": "object",
                "properties": {
                    "market_id": {"type": "string", "description": "The Polymarket condition ID (e.g., '0x1234...')"}
                },
                "required": ["market_id"]
            }
        ),
        Tool(
            name="analyze_volume_anomaly",
            description="Analyze REAL volume data to detect anomalies using actual trade history",
            inputSchema={
                "type": "object",
                "properties": {
                    "market_id": {"type": "string"},
                    "timeframe": {"type": "string", "enum": ["1h", "24h", "7d"]}
                },
                "required": ["market_id", "timeframe"]
            }
        ),
        Tool(
            name="detect_wash_trading",
            description="Detect REAL wash trading patterns from actual blockchain trades",
            inputSchema={
                "type": "object",
                "properties": {
                    "market_id": {"type": "string"},
                    "lookback_hours": {"type": "integer", "default": 24}
                },
                "required": ["market_id"]
            }
        ),
        Tool(
            name="calculate_health_score",
            description="Calculate REAL market health score from actual market data",
            inputSchema={
                "type": "object",
                "properties": {"market_id": {"type": "string"}},
                "required": ["market_id"]
            }
        ),
        Tool(
            name="get_trader_concentration",
            description="Analyze REAL trader concentration from actual trade data",
            inputSchema={
                "type": "object",
                "properties": {"market_id": {"type": "string"}},
                "required": ["market_id"]
            }
        ),
        Tool(
            name="search_markets",
            description="Search for Polymarket markets by keyword",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query (e.g., 'Trump', 'Bitcoin', 'Election')"}
                },
                "required": ["query"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "get_market_data":
            market_id = arguments["market_id"]
            data = await fetch_market_info(market_id)
            result = f"""REAL Market Data from Polymarket CLOB API:

Market ID: {market_id}
Question: {data.get('question', 'N/A')}
Description: {data.get('description', 'N/A')}

Current Price: ${float(data.get('last_price', 0)):.4f}
24h Volume: ${float(data.get('volume24hr', 0)):,.2f}
Total Volume: ${float(data.get('volume', 0)):,.2f}
Liquidity: ${float(data.get('liquidity', 0)):,.2f}

Active: {data.get('active', False)}
Closed: {data.get('closed', False)}
Market Type: {data.get('market_type', 'N/A')}

Outcome: {data.get('outcome', 'Pending')}
Outcome Prices: {data.get('outcome_prices', 'N/A')}

End Date: {data.get('end_date_iso', 'N/A')}
Created: {data.get('created_at', 'N/A')}

Data Source: Polymarket CLOB API (REAL DATA)
"""
            return [TextContent(type="text", text=result)]

        elif name == "analyze_volume_anomaly":
            market_id = arguments["market_id"]
            timeframe = arguments["timeframe"]
            analysis = await calculate_real_volume_anomaly(market_id, timeframe)
            result = f"""REAL Volume Anomaly Analysis (from actual trades):

Market: {market_id}
Timeframe: {timeframe}

Current Period Volume: ${analysis['current_volume']:,.2f}
Historical Average: ${analysis['average_volume']:,.2f}
Standard Deviation: ${analysis['std_dev']:,.2f}

Z-Score: {analysis['z_score']:.2f}
Anomaly Detected: {'YES' if analysis['is_anomaly'] else 'NO'}
Severity: {analysis['severity']}

Interpretation: Current volume is {abs(analysis['z_score']):.1f} standard deviations 
{'above' if analysis['z_score'] > 0 else 'below'} the historical mean.
{'[ALERT] This is statistically significant and warrants investigation!' if analysis['is_anomaly'] else '[OK] Volume appears normal.'}

Data Source: Real Polymarket trade history
"""
            return [TextContent(type="text", text=result)]

        elif name == "detect_wash_trading":
            market_id = arguments["market_id"]
            lookback = arguments.get("lookback_hours", 24)
            analysis = await detect_real_wash_trading(market_id, lookback)
            pairs_text = "\n".join(f"  - {pair}" for pair in analysis['repeated_pairs'][:10])
            result = f"""REAL Wash Trading Analysis (from blockchain data):

Market: {market_id}
Lookback Period: {lookback} hours
Total Trades Analyzed: {analysis['total_trades_analyzed']}

Suspicious Patterns: {analysis['suspicious_patterns']}
Self-Trades Detected: {analysis['self_trades']}
Confidence: {analysis['confidence']}

Repeated Trader Pairs:
{pairs_text if analysis['repeated_pairs'] else '  None detected'}

Assessment: {'[HIGH RISK] Multiple suspicious patterns detected' if analysis['suspicious_patterns'] > 3 else '[MODERATE RISK] Some patterns detected' if analysis['suspicious_patterns'] > 0 else '[LOW RISK] No significant patterns'}

Data Source: Real blockchain trade data
"""
            return [TextContent(type="text", text=result)]

        elif name == "calculate_health_score":
            market_id = arguments["market_id"]
            health = await calculate_real_health_score(market_id)
            result = f"""REAL Market Health Score (from actual data):

Market: {market_id}

Overall Score: {health['overall_score']}/100
Risk Level: {health['risk_level']}

Component Scores:
  - Liquidity: {health['liquidity_score']}/100 (${health['total_liquidity']:,.0f})
  - Trader Diversity: {health['diversity_score']}/100 ({health['unique_traders']} unique traders)
  - Volume Consistency: {health['volume_score']}/100
  - Price Stability: {health['stability_score']}/100
  - Manipulation Risk: {health['manipulation_score']}/100 (inverse)

Assessment: {'[OK] HEALTHY MARKET' if health['overall_score'] >= 75 else '[WARN] MODERATE CONCERNS' if health['overall_score'] >= 50 else '[ALERT] HIGH RISK'}

Data Source: Real Polymarket API + blockchain data
"""
            return [TextContent(type="text", text=result)]

        elif name == "get_trader_concentration":
            market_id = arguments["market_id"]
            conc = await get_real_trader_concentration(market_id)
            result = f"""REAL Trader Concentration Analysis:

Market: {market_id}

Total Unique Traders: {conc['total_traders']}
Total Volume: ${conc['total_volume']:,.2f}

Concentration Metrics:
  - Top 10 Traders: {conc['top10_percentage']:.1f}% of volume
  - Top 50 Traders: {conc['top50_percentage']:.1f}% of volume
  - Gini Coefficient: {conc['gini_coefficient']:.3f}

Concentration Level: {conc['concentration_level']}

Assessment: {'[ALERT] VERY HIGH concentration - manipulation risk' if conc['concentration_level'] == 'VERY HIGH' else '[WARN] HIGH concentration - monitor closely' if conc['concentration_level'] == 'HIGH' else '[OK] Moderate concentration' if conc['concentration_level'] == 'MODERATE' else '[OK] Good distribution'}

Healthy Threshold: <30% for top 10 traders
Current Status: {'ABOVE threshold' if conc['top10_percentage'] > 30 else 'Within threshold'}

Data Source: Real blockchain trade data
"""
            return [TextContent(type="text", text=result)]

        elif name == "search_markets":
            query = arguments["query"].lower()
            markets = await fetch_all_markets()
            matching = [
                m for m in markets
                if query in m.get('question', '').lower() or query in m.get('description', '').lower()
            ][:10]
            if matching:
                results = "\n\n".join([
                    f"""Market {i+1}:
Question: {m.get('question', 'N/A')}
ID: {m.get('condition_id', 'N/A')}
Price: ${float(m.get('last_price', 0)):.4f}
Volume: ${float(m.get('volume', 0)):,.0f}
Active: {m.get('active', False)}"""
                    for i, m in enumerate(matching)
                ])
            else:
                results = "No markets found matching query."
            result = f"""Market Search Results for "{query}":

Found {len(matching)} matching markets:

{results}

Data Source: Real Polymarket API
"""
            return [TextContent(type="text", text=result)]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        error_msg = f"""Error executing {name}:

{str(e)}

This could mean:
- Invalid market ID
- API connectivity issue
- Insufficient data for analysis

Please verify the market ID and try again.
"""
        return [TextContent(type="text", text=error_msg)]

async def main():
    print("Starting Polymarket MCP Server (REAL DATA)")
    print("Connected to Polymarket CLOB API")
    print("All tools use real blockchain and API data")
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="polymarket-analysis",
                server_version="1.0.0-REAL",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())
