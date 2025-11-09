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
from datetime import datetime, timedelta
from typing import List, Dict, Any
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.types import Tool, TextContent
import mcp.server.stdio
import aiohttp
from dotenv import load_dotenv

load_dotenv()

NEWS_API_KEY = os.getenv("NEWS_API_KEY")
if not NEWS_API_KEY:
    raise Exception("NEWS_API_KEY not found in environment")

NEWS_API_BASE = "https://newsapi.org/v2"

server = Server("news-analysis")

async def fetch_newsapi_articles(topic: str, timeframe: str) -> List[Dict[str, Any]]:
    timeframe_hours = {"1h": 1, "6h": 6, "24h": 24, "7d": 168}
    hours = timeframe_hours.get(timeframe, 24)
    from_date = datetime.utcnow() - timedelta(hours=hours)
    from_iso = from_date.strftime("%Y-%m-%dT%H:%M:%S")
    url = f"{NEWS_API_BASE}/everything"
    params = {
        "q": topic,
        "from": from_iso,
        "sortBy": "publishedAt",
        "apiKey": NEWS_API_KEY,
        "language": "en",
        "pageSize": 100
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                articles = data.get("articles", [])
                return articles
            elif response.status == 426:
                raise Exception("NewsAPI: Upgrade required")
            elif response.status == 429:
                raise Exception("NewsAPI: Rate limit exceeded")
            else:
                error = await response.json()
                raise Exception(f"NewsAPI error {response.status}: {error.get('message', 'Unknown')}")

async def analyze_sentiment_real(articles: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not articles:
        return {
            "overall": "NEUTRAL",
            "score": 0.0,
            "positive_count": 0,
            "neutral_count": 0,
            "negative_count": 0,
            "confidence": "LOW"
        }
    positive_keywords = [
        'win', 'surge', 'gain', 'rise', 'success', 'positive', 'growth',
        'bullish', 'up', 'increase', 'rally', 'boom', 'strong', 'lead'
    ]
    negative_keywords = [
        'loss', 'fall', 'decline', 'down', 'negative', 'crash', 'bearish',
        'decrease', 'weak', 'concern', 'risk', 'threat', 'failure', 'drop'
    ]
    positive_count = 0
    negative_count = 0
    neutral_count = 0
    for article in articles:
        title = article.get('title', '').lower()
        description = article.get('description', '').lower()
        text = f"{title} {description}"
        pos_score = sum(1 for word in positive_keywords if word in text)
        neg_score = sum(1 for word in negative_keywords if word in text)
        if pos_score > neg_score:
            positive_count += 1
        elif neg_score > pos_score:
            negative_count += 1
        else:
            neutral_count += 1
    total = len(articles)
    score = (positive_count - negative_count) / total if total > 0 else 0.0
    if score > 0.2:
        overall = "POSITIVE"
    elif score < -0.2:
        overall = "NEGATIVE"
    else:
        overall = "NEUTRAL"
    return {
        "overall": overall,
        "score": round(score, 2),
        "positive_count": positive_count,
        "neutral_count": neutral_count,
        "negative_count": negative_count,
        "positive_pct": round(positive_count / total * 100, 1) if total > 0 else 0,
        "neutral_pct": round(neutral_count / total * 100, 1) if total > 0 else 0,
        "negative_pct": round(negative_count / total * 100, 1) if total > 0 else 0,
        "confidence": "HIGH" if total >= 10 else "MEDIUM" if total >= 5 else "LOW"
    }

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    return [
        Tool(
            name="get_market_related_news",
            description="Fetch REAL news articles from NewsAPI",
            inputSchema={
                "type": "object",
                "properties": {
                    "topic": {"type": "string"},
                    "timeframe": {"type": "string", "enum": ["1h", "6h", "24h", "7d"]}
                },
                "required": ["topic", "timeframe"]
            }
        ),
        Tool(
            name="analyze_news_sentiment",
            description="Analyze REAL sentiment from actual news articles",
            inputSchema={
                "type": "object",
                "properties": {"topic": {"type": "string"}, "timeframe": {"type": "string"}},
                "required": ["topic", "timeframe"]
            }
        ),
        Tool(
            name="correlate_news_to_price",
            description="Check if price movements correlate with REAL news timing",
            inputSchema={
                "type": "object",
                "properties": {
                    "market_topic": {"type": "string"},
                    "price_change_time": {"type": "string"},
                    "window_minutes": {"type": "integer", "default": 60}
                },
                "required": ["market_topic", "price_change_time"]
            }
        ),
        Tool(
            name="compare_news_trading_volume",
            description="Compare REAL news volume to trading volume",
            inputSchema={
                "type": "object",
                "properties": {
                    "market_topic": {"type": "string"},
                    "timeframe": {"type": "string"},
                    "trading_volume": {"type": "number"}
                },
                "required": ["market_topic", "timeframe", "trading_volume"]
            }
        ),
        Tool(
            name="get_breaking_news",
            description="Get REAL breaking news from NewsAPI",
            inputSchema={
                "type": "object",
                "properties": {"categories": {"type": "array", "items": {"type": "string"}}},
                "required": ["categories"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        if name == "get_market_related_news":
            topic = arguments["topic"]
            timeframe = arguments["timeframe"]
            articles = await fetch_newsapi_articles(topic, timeframe)
            if not articles:
                result = f"No news articles found for '{topic}' in last {timeframe}"
            else:
                articles_text = "\n\n".join([
                    f"Article {i+1}:\nTitle: {a.get('title', 'N/A')}\nSource: {a.get('source', {}).get('name', 'Unknown')}\nAuthor: {a.get('author', 'Unknown')}\nPublished: {a.get('publishedAt', 'N/A')}\nDescription: {a.get('description', 'No description')[:200]}...\nURL: {a.get('url', 'N/A')}"
                    for i, a in enumerate(articles[:20])
                ])
                result = f"REAL News Articles from NewsAPI:\n\nTopic: \"{topic}\"\nTimeframe: {timeframe}\nTotal Articles: {len(articles)}\n\n{articles_text}\n\nData Source: NewsAPI (REAL DATA)\nAPI Key: ...{NEWS_API_KEY[-6:]}\n"
            return [TextContent(type="text", text=result)]

        elif name == "analyze_news_sentiment":
            topic = arguments["topic"]
            timeframe = arguments["timeframe"]
            articles = await fetch_newsapi_articles(topic, timeframe)
            sentiment = await analyze_sentiment_real(articles)
            result = f"REAL News Sentiment Analysis:\n\nTopic: \"{topic}\"\nTimeframe: {timeframe}\nArticles Analyzed: {len(articles)}\n\nOverall Sentiment: {sentiment['overall']} (score: {sentiment['score']:.2f})\n\nBreakdown:\n  - Positive: {sentiment['positive_count']} ({sentiment['positive_pct']:.1f}%)\n  - Neutral: {sentiment['neutral_count']} ({sentiment['neutral_pct']:.1f}%)\n  - Negative: {sentiment['negative_count']} ({sentiment['negative_pct']:.1f}%)\n\nConfidence: {sentiment['confidence']}\n\nInterpretation: Sentiment is {'strongly positive' if sentiment['score'] > 0.3 else 'strongly negative' if sentiment['score'] < -0.3 else 'balanced/neutral'}\n\nData Source: NewsAPI (REAL DATA)\n"
            return [TextContent(type="text", text=result)]

        elif name == "correlate_news_to_price":
            topic = arguments["market_topic"]
            price_time_str = arguments["price_change_time"]
            window = arguments.get("window_minutes", 60)
            try:
                price_time = datetime.fromisoformat(price_time_str.replace('Z', '+00:00'))
            except:
                price_time = datetime.utcnow()
            articles = await fetch_newsapi_articles(topic, "24h")
            window_start = price_time - timedelta(minutes=window)
            window_end = price_time + timedelta(minutes=window)
            news_in_window = []
            for article in articles:
                try:
                    article_time = datetime.fromisoformat(article.get('publishedAt', '').replace('Z', '+00:00'))
                    if window_start <= article_time <= window_end:
                        news_in_window.append(article)
                except:
                    continue
            news_events_text = "\n".join([f"  [{a.get('publishedAt', 'N/A')}] {a.get('title', 'N/A')}" for a in news_in_window[:10]]) if news_in_window else "  No news found in window"
            expected_news = 3 if window >= 60 else 1
            is_suspicious = len(news_in_window) < (expected_news / 2)
            result = f"REAL News-Price Correlation Analysis:\n\nTopic: \"{topic}\"\nPrice Change Time: {price_time_str}\nAnalysis Window: +/-{window} minutes\n\nNews in Window ({len(news_in_window)} found):\n{news_events_text}\n\nExpected News: ~{expected_news} articles\nActual News: {len(news_in_window)} articles\n\n{'[ALERT] RED FLAG: Significant price movement with minimal news coverage' if is_suspicious else '[OK] Price movement appears justified by news activity'}\n\nVerdict: {'SUSPICIOUS - Possible manipulation or insider activity' if is_suspicious else 'Normal - Adequate news coverage'}\n\nData Source: NewsAPI (REAL DATA)\n"
            return [TextContent(type="text", text=result)]

        elif name == "compare_news_trading_volume":
            topic = arguments["market_topic"]
            timeframe = arguments["timeframe"]
            trading_volume = arguments["trading_volume"]
            articles = await fetch_newsapi_articles(topic, timeframe)
            news_count = len(articles)
            expected_news = max(1, int(trading_volume / 500000))
            ratio = trading_volume / news_count if news_count > 0 else trading_volume
            expected_ratio = 500000
            is_anomalous = ratio > (expected_ratio * 2)
            result = f"REAL News vs Trading Volume Comparison:\n\nTopic: \"{topic}\"\nTimeframe: {timeframe}\n\nTrading Volume: ${trading_volume:,.0f}\nNews Articles: {news_count}\nExpected Articles: ~{expected_news}\n\nVolume per Article: ${ratio:,.0f}\nExpected Ratio: ${expected_ratio:,.0f}\nMultiplier: {ratio / expected_ratio:.1f}x\n\n{'[ALERT] Trading volume disproportionate to news coverage' if is_anomalous else '[OK] Trading volume proportional to news'}\n\nAssessment: {'HIGH RISK - Investigate for manipulation' if is_anomalous else 'Normal activity'}\n\nData Source: NewsAPI (REAL DATA)\n"
            return [TextContent(type="text", text=result)]

        elif name == "get_breaking_news":
            categories = arguments["categories"]
            all_articles = []
            for category in categories:
                articles = await fetch_newsapi_articles(category, "1h")
                all_articles.extend(articles[:3])
            alerts_text = "\n\n".join([f"[{a.get('publishedAt', 'N/A')}]\n{a.get('title', 'N/A')}\nSource: {a.get('source', {}).get('name', 'Unknown')}\n{a.get('description', 'No description')[:150]}...\nURL: {a.get('url', 'N/A')}" for a in all_articles[:10]])
            result = f"REAL Breaking News Alerts:\n\nCategories: {', '.join(categories)}\nTotal Alerts: {len(all_articles)}\nLast Hour Coverage\n\n{alerts_text}\n\nData Source: NewsAPI (REAL DATA)\n"
            return [TextContent(type="text", text=result)]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except Exception as e:
        error_msg = f"Error executing {name}:\n\n{str(e)}\n\nPossible issues:\n- NewsAPI rate limit\n- Invalid API key\n- Network connectivity issue\n\nCheck your NEWS_API_KEY in .env file\n"
        return [TextContent(type="text", text=error_msg)]

async def main():
    print("Starting News MCP Server (REAL DATA)")
    print(f"Connected to NewsAPI with key: ...{NEWS_API_KEY[-6:]}")
    print("All tools use real news data")
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="news-analysis",
                server_version="1.0.0-REAL",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())
