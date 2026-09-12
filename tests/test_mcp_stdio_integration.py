"""Exercise a real server process without opening a browser or changing charts."""
import asyncio
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def test_stdio_initialize_and_list_tools():
    async def check():
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "tradingview_mcp.server"],
            cwd=str(Path(__file__).resolve().parents[1]),
            env={**os.environ, "PYTHONUTF8": "1", "TV_MCP_SKIP_CHROME_LAUNCH": "1"},
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                result = await session.initialize()
                assert result.serverInfo.name == "tradingview"
                tools = (await session.list_tools()).tools
                names = {tool.name for tool in tools}
                assert {"tv_get_current_symbol", "tv_validate_pine_script", "tv_screenshot"} <= names
                assert len(names) == len(tools)
                print(f"MCP handshake OK: {len(tools)} tools")

    asyncio.run(asyncio.wait_for(check(), timeout=30))
