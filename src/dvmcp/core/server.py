"""Base MCP server for DVMCP - handles JSON-RPC over stdio."""

from __future__ import annotations

import asyncio
import json
import sys
import traceback
from typing import Any

from .registry import (
    TOOL_REGISTRY,
    get_visible_tools,
    DifficultyLevel,
)
from .difficulty import get_engine, set_difficulty
from .verification import get_verifier


SERVER_INFO = {
    "name": "dvmcp-novatech",
    "version": "2.0.0",
}

CAPABILITIES = {
    "tools": {"listChanged": False},
}


async def handle_initialize(params: dict) -> dict:
    return {
        "protocolVersion": "2024-11-05",
        "capabilities": CAPABILITIES,
        "serverInfo": SERVER_INFO,
    }


async def handle_tools_list(params: dict, department: str | None = None) -> dict:
    tools = get_visible_tools(department)
    return {
        "tools": [
            {
                "name": t.name,
                "description": t.description,
                "inputSchema": t.input_schema,
            }
            for t in tools
        ]
    }


async def handle_tools_call(params: dict) -> dict:
    tool_name = params.get("name", "")
    arguments = params.get("arguments", {})

    # Allow calling hidden tools too (shadow tool vulnerability)
    tool = TOOL_REGISTRY.get(tool_name)
    if not tool:
        return {
            "content": [{"type": "text", "text": f"Unknown tool: {tool_name}"}],
            "isError": True,
        }

    try:
        result = await tool.handler(arguments)
        verifier = get_verifier()
        verifier.record_call(tool_name, arguments, result)

        if isinstance(result, dict):
            text = json.dumps(result, indent=2, default=str)
        elif isinstance(result, list):
            text = json.dumps(result, indent=2, default=str)
        else:
            text = str(result)

        return {"content": [{"type": "text", "text": text}]}
    except Exception as e:
        engine = get_engine()
        error_text = traceback.format_exc() if engine.include_stack_trace() else str(e)
        return {
            "content": [{"type": "text", "text": f"Error: {error_text}"}],
            "isError": True,
        }


async def process_message(message: dict, department: str | None = None) -> dict | None:
    method = message.get("method")
    params = message.get("params", {})
    msg_id = message.get("id")

    if method == "initialize":
        result = await handle_initialize(params)
    elif method == "notifications/initialized":
        return None
    elif method == "tools/list":
        result = await handle_tools_list(params, department)
    elif method == "tools/call":
        result = await handle_tools_call(params)
    else:
        result = {"error": {"code": -32601, "message": f"Unknown method: {method}"}}

    if msg_id is not None:
        return {"jsonrpc": "2.0", "id": msg_id, "result": result}
    return None


async def run_server(department: str | None = None) -> None:
    """Run the MCP server reading JSON-RPC from stdin."""
    # Import all department tools to trigger registration
    import dvmcp.departments.hr.tools
    import dvmcp.departments.engineering.tools
    import dvmcp.departments.finance.tools
    import dvmcp.departments.it_admin.tools
    import dvmcp.departments.support.tools
    import dvmcp.departments.marketing.tools

    # Seed database
    from dvmcp.data.seed import seed_all
    seed_all()

    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

    buffer = b""
    while True:
        try:
            chunk = await reader.read(65536)
            if not chunk:
                break
            buffer += chunk

            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                line = line.strip()
                if not line:
                    continue
                try:
                    message = json.loads(line)
                except json.JSONDecodeError:
                    continue

                response = await process_message(message, department)
                if response:
                    out = json.dumps(response) + "\n"
                    sys.stdout.write(out)
                    sys.stdout.flush()
        except Exception:
            break


def main():
    """Entry point for the all-in-one server."""
    import argparse

    parser = argparse.ArgumentParser(description="DVMCP - Damn Vulnerable MCP Server")
    parser.add_argument(
        "--department",
        choices=["hr", "engineering", "finance", "it_admin", "support", "marketing"],
        help="Run only a specific department's tools",
    )
    parser.add_argument(
        "--difficulty",
        choices=["beginner", "intermediate", "advanced", "expert"],
        default="beginner",
        help="Set difficulty level (default: beginner)",
    )
    args = parser.parse_args()

    level = DifficultyLevel[args.difficulty.upper()]
    set_difficulty(level)

    asyncio.run(run_server(args.department))


if __name__ == "__main__":
    main()
