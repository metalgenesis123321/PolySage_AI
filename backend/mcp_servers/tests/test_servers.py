#!/usr/bin/env python3
"""
Test script for MCP servers
Run this to verify servers work correctly
"""

import subprocess
import json
import sys

def test_server(server_path, server_name):
    """Test a single MCP server"""
    print(f"\n{'='*60}")
    print(f"Testing {server_name}")
    print(f"{'='*60}\n")
    
    try:
        # Start the server
        proc = subprocess.Popen(
            ["python", server_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Initialize
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "0.1.0",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        }
        
        proc.stdin.write(json.dumps(init_request) + "\n")
        proc.stdin.flush()
        response = proc.stdout.readline()
        print(f"✓ Server initialized")
        
        # List tools
        list_tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        }
        
        proc.stdin.write(json.dumps(list_tools_request) + "\n")
        proc.stdin.flush()
        response = proc.stdout.readline()
        
        tools_response = json.loads(response)
        tool_count = len(tools_response.get("result", {}).get("tools", []))
        print(f"✓ Found {tool_count} tools")
        
        for tool in tools_response.get("result", {}).get("tools", []):
            print(f"  - {tool['name']}")
        
        # Test a tool call
        if server_name == "Polymarket Server":
            test_tool = "get_market_data"
            test_args = {"market_id": "test-market"}
        else:
            test_tool = "get_market_related_news"
            test_args = {"topic": "test", "timeframe": "24h"}
        
        call_tool_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": test_tool,
                "arguments": test_args
            }
        }
        
        proc.stdin.write(json.dumps(call_tool_request) + "\n")
        proc.stdin.flush()
        response = proc.stdout.readline()
        print(f"✓ Tool call '{test_tool}' successful")
        
        proc.terminate()
        print(f"\n✅ {server_name} PASSED\n")
        return True
        
    except Exception as e:
        print(f"\n❌ {server_name} FAILED: {str(e)}\n")
        if 'proc' in locals():
            proc.terminate()
        return False

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("MCP SERVERS TEST SUITE")
    print("="*60)
    
    results = []
    
    # Test Polymarket server
    results.append(test_server(
        "backend/mcp_servers/polymarket_server/server.py",
        "Polymarket Server"
    ))
    
    # Test News server
    results.append(test_server(
        "backend/mcp_servers/news_server/server.py",
        "News Server"
    ))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED")
        sys.exit(1)

if __name__ == "__main__":
    main()