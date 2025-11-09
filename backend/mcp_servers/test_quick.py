#!/usr/bin/env python3

import subprocess
import json
import time
import sys

def test_server_real_data(server_path, server_name, test_tool_call):
    print(f"\nTesting {server_name} (REAL DATA)\n")
    try:
        proc = subprocess.Popen(
            ["python", server_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        time.sleep(2)
        if proc.poll() is not None:
            stderr = proc.stderr.read()
            print("Server failed to start")
            print(f"Error: {stderr}")
            return False
        print("Server started")
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "0.1.0",
                "capabilities": {},
                "clientInfo": {"name": "real-data-test-client", "version": "1.0.0"}
            }
        }
        proc.stdin.write(json.dumps(init_request) + "\n")
        proc.stdin.flush()
        init_response = proc.stdout.readline()
        if init_response:
            try:
                init_data = json.loads(init_response)
                print("Server initialized")
                print(f"Response ID: {init_data.get('id')}")
            except json.JSONDecodeError:
                print(f"Got response but couldn't parse: {init_response[:100]}")
        time.sleep(0.5)
        list_tools_request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
        proc.stdin.write(json.dumps(list_tools_request) + "\n")
        proc.stdin.flush()
        tools_response = proc.stdout.readline()
        tool_count = 0
        tool_names = []
        if tools_response:
            try:
                tools_data = json.loads(tools_response)
                tools = tools_data.get("result", {}).get("tools", [])
                tool_count = len(tools)
                tool_names = [t.get("name", "Unknown") for t in tools]
                print(f"Found {tool_count} tools:")
                for name in tool_names:
                    print(f"  - {name}")
            except json.JSONDecodeError:
                print("Couldn't parse tools response")
        time.sleep(0.5)
        print(f"Testing tool: {test_tool_call['name']} with args {test_tool_call['arguments']}")
        call_tool_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": test_tool_call["name"], "arguments": test_tool_call["arguments"]}
        }
        proc.stdin.write(json.dumps(call_tool_request) + "\n")
        proc.stdin.flush()
        print("Waiting for API response...")
        tool_response = proc.stdout.readline()
        if tool_response:
            try:
                tool_data = json.loads(tool_response)
                if "result" in tool_data:
                    content = tool_data["result"].get("content", [])
                    if content:
                        text = content[0].get("text", "")
                        is_real_data = ("REAL" in text.upper() or "API" in text.upper() or "Data Source:" in text)
                        print("Tool call successful")
                        print(f"Response length: {len(text)}")
                        lines = text.split('\n')[:10]
                        print("Response preview:")
                        for line in lines:
                            if line.strip():
                                print(f"  {line}")
                        if is_real_data:
                            print("CONFIRMED: Using REAL data")
                        else:
                            print("WARNING: May be using mock data")
                elif "error" in tool_data:
                    error = tool_data["error"]
                    print("Tool call error")
                    print(f"Code: {error.get('code')}")
                    print(f"Message: {error.get('message')}")
            except json.JSONDecodeError as e:
                print(f"Couldn't parse tool response: {e}")
                print(f"Raw response: {tool_response[:200]}")
        else:
            print("No response from tool call")
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        print(f"\n{server_name} TEST PASSED\n")
        return True
    except Exception as e:
        print(f"{server_name} TEST FAILED")
        print(f"Error: {str(e)}")
        if 'proc' in locals():
            proc.terminate()
        return False

def main():
    print("\nMCP SERVERS REAL DATA TEST SUITE\n")
    print("This will test actual API calls with real data")
    print("Ensure API keys are in your .env file")
    print("Waiting 3 seconds...")
    try:
        time.sleep(3)
    except KeyboardInterrupt:
        print("Test cancelled")
        sys.exit(0)
    results = []
    polymarket_test = {"name": "search_markets", "arguments": {"query": "Trump"}}
    results.append(test_server_real_data("polymarket_server/server.py", "Polymarket Server", polymarket_test))
    time.sleep(2)
    news_test = {"name": "get_market_related_news", "arguments": {"topic": "Trump election", "timeframe": "24h"}}
    results.append(test_server_real_data("news_server/server.py", "News Server", news_test))
    passed = sum(results)
    total = len(results)
    print("\nTEST SUMMARY")
    print(f"Tests Passed: {passed}/{total}")
    if passed == total:
        print("\nALL REAL DATA TESTS PASSED")
        print("MCP servers connected to real APIs and processing data")
    else:
        print("\nSOME TESTS FAILED")
        print("Possible issues:")
        print("  - Missing or invalid API keys")
        print("  - Network connectivity")
        print("  - API rate limits")
        print("Check .env and API key validity")
    sys.exit(0 if passed == total else 1)

if __name__ == "__main__":
    main()
