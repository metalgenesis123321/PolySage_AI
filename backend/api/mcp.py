import asyncio
import json
import os
import subprocess
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MCPServerManager:
    """Manages MCP server processes and handles communication"""
    
    def __init__(self):
        self.polymarket_proc = None
        self.news_proc = None
        self.initialized = False
        self.request_id = 0
        self._lock = asyncio.Lock()
    
    async def start(self):
        """Start both MCP servers"""
        if self.initialized:
            logger.info("MCP servers already initialized")
            return
        
        async with self._lock:
            if self.initialized:  # Double-check after acquiring lock
                return
            
            logger.info("Starting MCP servers...")
            python_exe = sys.executable
            
            # Determine base path
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            poly_path = os.path.join(base_path, "mcp_servers", "polymarket_server", "server.py")
            news_path = os.path.join(base_path, "mcp_servers", "news_server", "server.py")
            
            # Start Polymarket server
            try:
                self.polymarket_proc = subprocess.Popen(
                    [python_exe, poly_path],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    bufsize=1,
                    cwd=base_path
                )
                logger.info("✓ Polymarket MCP server process started")
            except Exception as e:
                logger.error(f"✗ Failed to start Polymarket server: {e}")
                raise
            
            # Start News server
            try:
                self.news_proc = subprocess.Popen(
                    [python_exe, news_path],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    bufsize=1,
                    cwd=base_path
                )
                logger.info("✓ News MCP server process started")
            except Exception as e:
                logger.error(f"✗ Failed to start News server: {e}")
                raise
            
            # Wait for servers to initialize
            await asyncio.sleep(3)
            
            # Send initialization messages
            await self._init_server(self.polymarket_proc, "polymarket")
            await self._init_server(self.news_proc, "news")
            
            self.initialized = True
            logger.info("✓ MCP servers ready")
    
    async def _init_server(self, proc, name):
        """Initialize an MCP server"""
        init_msg = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "0.1.0",
                "capabilities": {},
                "clientInfo": {"name": "polysage-api", "version": "1.0.0"}
            }
        }
        
        try:
            proc.stdin.write(json.dumps(init_msg) + "\n")
            proc.stdin.flush()
            response = proc.stdout.readline()
            if response:
                data = json.loads(response)
                logger.info(f"✓ {name} server initialized (response id={data.get('id')})")
        except Exception as e:
            logger.error(f"✗ Failed to initialize {name}: {e}")
    
    async def call_tool(self, server: str, tool: str, args: dict, timeout: float = 15.0) -> str:
        """Call a tool on an MCP server"""
        if not self.initialized:
            await self.start()
        
        self.request_id += 1
        proc = self.polymarket_proc if server == "polymarket" else self.news_proc
        
        if not proc or proc.poll() is not None:
            raise Exception(f"{server} server not running")
        
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": "tools/call",
            "params": {"name": tool, "arguments": args}
        }
        
        try:
            proc.stdin.write(json.dumps(request) + "\n")
            proc.stdin.flush()
            
            # Read response with timeout
            response_line = await asyncio.wait_for(
                asyncio.to_thread(proc.stdout.readline),
                timeout=timeout
            )
            
            if not response_line:
                return f"Error: No response from {server}"
            
            result = json.loads(response_line)
            
            if "result" in result:
                content = result["result"].get("content", [])
                if content:
                    return content[0].get("text", "")
            
            if "error" in result:
                return f"Error: {result['error'].get('message', 'Unknown')}"
            
            return ""
            
        except asyncio.TimeoutError:
            logger.warning(f"Timeout calling {tool} on {server}")
            return f"Timeout calling {tool}"
        except Exception as e:
            logger.error(f"Error calling {tool}: {e}")
            return f"Error: {str(e)}"
    
    async def shutdown(self):
        """Shutdown MCP servers"""
        logger.info("Shutting down MCP servers...")
        
        if self.polymarket_proc:
            self.polymarket_proc.terminate()
            try:
                self.polymarket_proc.wait(timeout=3)
            except:
                self.polymarket_proc.kill()
        
        if self.news_proc:
            self.news_proc.terminate()
            try:
                self.news_proc.wait(timeout=3)
            except:
                self.news_proc.kill()
        
        self.initialized = False
        logger.info("✓ MCP servers shutdown complete")


# Global instance
_mcp_manager = MCPServerManager()


async def get_manipulation_report(
    market_id: str,
    orderbook: Dict[str, Any],
    news: List[Dict[str, Any]],
    meta: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Generate manipulation report using real MCP servers.
    
    Calls 10 different tools across both servers:
    - Polymarket: search, market_data, volume_anomaly, wash_trading, health_score, trader_concentration
    - News: get_news, sentiment, news_correlation, volume_comparison
    """
    
    meta = meta or {}
    market = meta.get("market", {})
    market_title = market.get("title", "Unknown")
    
    logger.info(f"Generating report for: {market_id}")
    
    try:
        # Ensure servers are running
        if not _mcp_manager.initialized:
            await _mcp_manager.start()
        
        # Run all analysis tools
        results = await asyncio.gather(
            # Polymarket tools
            _mcp_manager.call_tool("polymarket", "search_markets", {"query": market_title[:50]}),
            _mcp_manager.call_tool("polymarket", "get_market_data", {"market_id": market_id}),
            _mcp_manager.call_tool("polymarket", "analyze_volume_anomaly", {"market_id": market_id, "timeframe": "24h"}),
            _mcp_manager.call_tool("polymarket", "detect_wash_trading", {"market_id": market_id, "lookback_hours": 24}),
            _mcp_manager.call_tool("polymarket", "calculate_health_score", {"market_id": market_id}),
            _mcp_manager.call_tool("polymarket", "get_trader_concentration", {"market_id": market_id}),
            
            # News tools
            _mcp_manager.call_tool("news", "get_market_related_news", {"topic": market_title, "timeframe": "24h"}),
            _mcp_manager.call_tool("news", "analyze_news_sentiment", {"topic": market_title, "timeframe": "24h"}),
            _mcp_manager.call_tool("news", "correlate_news_to_price", {
                "market_topic": market_title,
                "price_change_time": datetime.utcnow().isoformat() + "Z",
                "window_minutes": 60
            }),
            _mcp_manager.call_tool("news", "compare_news_trading_volume", {
                "market_topic": market_title,
                "timeframe": "24h",
                "trading_volume": market.get("volume24hr", 1000000)
            }),
            
            return_exceptions=True
        )
        
        # Unpack results
        (search_result, market_data, volume_analysis, wash_trading, 
         health_score, trader_conc, news_articles, sentiment, 
         news_corr, volume_comp) = results
        
        # Extract risk metrics
        risk_score = _extract_risk_score(health_score, volume_analysis, wash_trading)
        flags = _extract_flags(volume_analysis, wash_trading, news_corr, volume_comp)
        confidence = _calc_confidence(health_score, len(flags))
        
        # Build report
        report = {
            "market_id": market_id,
            "riskScore": risk_score,
            "risk_level": "HIGH" if risk_score >= 70 else "MEDIUM" if risk_score >= 40 else "LOW",
            "flags": flags,
            "explanation": _build_explanation(flags, risk_score),
            "confidence": confidence,
            "details": {
                "search": _parse_output(search_result),
                "market_data": _parse_output(market_data),
                "volume_analysis": _parse_output(volume_analysis),
                "wash_trading": _parse_output(wash_trading),
                "health_score": _parse_output(health_score),
                "trader_concentration": _parse_output(trader_conc),
                "news": _parse_output(news_articles),
                "sentiment": _parse_output(sentiment),
                "news_correlation": _parse_output(news_corr),
                "volume_comparison": _parse_output(volume_comp)
            },
            "diagnostics": {
                "tools_called": 10,
                "data_sources": ["Polymarket CLOB API", "NewsAPI"],
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        }
        
        logger.info(f"✓ Report generated: risk={risk_score}/100, flags={len(flags)}")
        return report
        
    except Exception as e:
        logger.error(f"Error generating report: {e}", exc_info=True)
        return {
            "market_id": market_id,
            "riskScore": None,
            "flags": [],
            "explanation": f"Analysis failed: {str(e)}",
            "details": {},
            "confidence": 0.0,
            "diagnostics": {"error": str(e)}
        }


async def call_mcp_with_payload(payload: Dict[str, Any], timeout: float = 15.0) -> Dict[str, Any]:
    """
    Main entry point - matches existing API interface.
    Routes payload to get_manipulation_report.
    """
    market_id = payload.get("market_id") or payload.get("market", {}).get("id", "unknown")
    recent_trades = payload.get("recent_trades", [])
    orderbook = payload.get("orderbook", {})
    news = payload.get("news", [])
    meta = payload.get("meta", {})
    meta["market"] = payload.get("market", {})
    
    return await get_manipulation_report(market_id, recent_trades, orderbook, news, meta)


# Helper functions
def _parse_output(text: str) -> Dict[str, Any]:
    """Parse MCP text output into dict"""
    if isinstance(text, Exception):
        return {"error": str(text)}
    
    lines = text.split('\n')
    data = {"raw": text[:500]}  # Keep raw for debugging
    
    for line in lines:
        if ':' in line and not line.startswith('http'):
            parts = line.split(':', 1)
            if len(parts) == 2:
                key = parts[0].strip().lower().replace(' ', '_')
                value = parts[1].strip()
                data[key] = value
    
    return data


def _extract_risk_score(health: str, volume: str, wash: str) -> int:
    """Calculate risk score from analysis results"""
    if isinstance(health, Exception):
        return 50
    
    # Try to extract health score
    for line in health.split('\n'):
        if "Overall Score:" in line or "Health Score:" in line:
            try:
                score = int(line.split(':')[1].strip().split('/')[0])
                return 100 - score  # Invert: health -> risk
            except:
                pass
    
    # Fallback: analyze severity
    risk = 50
    
    if "HIGH" in volume.upper() or "ANOMALY" in volume.upper():
        risk += 15
    if "ALERT" in volume.upper():
        risk += 10
    
    if "HIGH RISK" in wash.upper():
        risk += 20
    elif "SUSPICIOUS" in wash.upper():
        risk += 10
    
    return min(100, max(0, risk))


def _extract_flags(volume: str, wash: str, news_corr: str, vol_comp: str) -> List[str]:
    """Extract manipulation flags"""
    flags = []
    
    # Volume flags
    if isinstance(volume, str):
        if "Anomaly Detected: YES" in volume:
            flags.append("volume_spike")
        if "HIGH" in volume and "ALERT" in volume.upper():
            flags.append("high_volume_anomaly")
    
    # Wash trading flags
    if isinstance(wash, str):
        if "Suspicious Patterns:" in wash:
            try:
                for line in wash.split('\n'):
                    if "Suspicious Patterns:" in line:
                        count = int(line.split(':')[1].strip())
                        if count > 0:
                            flags.append("wash_trading_detected")
                        if count > 3:
                            flags.append("high_wash_trading_risk")
            except:
                pass
    
    # News flags
    if isinstance(news_corr, str):
        if "SUSPICIOUS" in news_corr.upper() or "RED FLAG" in news_corr.upper():
            flags.append("news_mismatch")
        if "manipulation" in news_corr.lower() or "insider" in news_corr.lower():
            flags.append("possible_insider_trading")
    
    # Volume comparison flags
    if isinstance(vol_comp, str):
        if "ALERT" in vol_comp.upper():
            flags.append("trading_news_mismatch")
        if "HIGH RISK" in vol_comp.upper():
            flags.append("manipulation_risk")
    
    return flags


def _calc_confidence(health: str, flag_count: int) -> float:
    """Calculate confidence score"""
    conf = 0.7
    
    if isinstance(health, str) and "Overall Score:" in health:
        conf += 0.15
    
    if flag_count > 0:
        conf += min(0.15, flag_count * 0.03)
    
    return min(1.0, conf)


def _build_explanation(flags: List[str], risk: int) -> str:
    """Build explanation text"""
    if not flags:
        return f"Market analysis complete. Risk score: {risk}/100. No significant manipulation detected."
    
    parts = []
    if "volume_spike" in flags:
        parts.append("Unusual volume spike detected")
    if "wash_trading_detected" in flags:
        parts.append("Suspicious trading patterns found")
    if "news_mismatch" in flags:
        parts.append("Price movements misaligned with news")
    if "trading_news_mismatch" in flags:
        parts.append("Trading volume disproportionate to news")
    
    return f"Risk score: {risk}/100. " + "; ".join(parts) + "."


# Lifecycle hooks for FastAPI
async def startup_mcp_servers():
    """Call this in FastAPI startup event"""
    await _mcp_manager.start()


async def shutdown_mcp_servers():
    """Call this in FastAPI shutdown event"""
    await _mcp_manager.shutdown()