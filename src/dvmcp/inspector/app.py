"""DVMCP MCP Inspector — Web-based client for interacting with the MCP server over stdio."""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

try:
    from fastapi import FastAPI, Request
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    import uvicorn

    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

STATIC_DIR = Path(__file__).parent / "static"


class MCPProxy:
    """Manages a DVMCP subprocess and proxies JSON-RPC messages over stdio."""

    def __init__(self):
        self.process: subprocess.Popen | None = None
        self.request_id: int = 0
        self.lock = asyncio.Lock()
        self.difficulty: str = "beginner"
        self.department: str | None = None
        self.server_info: dict | None = None
        self.history: list[dict] = []
        self._read_buffer: str = ""

    @property
    def connected(self) -> bool:
        return self.process is not None and self.process.poll() is None

    async def connect(self, difficulty: str = "beginner", department: str | None = None) -> dict:
        """Spawn the DVMCP server and perform the MCP handshake."""
        await self.disconnect()

        self.difficulty = difficulty
        self.department = department
        self.request_id = 0
        self.history = []
        self._read_buffer = ""

        cmd = [sys.executable, "-m", "dvmcp.core.server", "--difficulty", difficulty]
        if department:
            cmd.extend(["--department", department])

        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        # Give the server a moment to start
        await asyncio.sleep(0.5)

        # Perform MCP handshake
        result = await self.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {"roots": {"listChanged": True}},
            "clientInfo": {"name": "dvmcp-inspector", "version": "1.0.0"},
        })

        self.server_info = result.get("result") if result else None

        # Send initialized notification
        await self._send_notification("notifications/initialized")

        return result or {}

    async def disconnect(self):
        """Shut down the MCP server subprocess."""
        if self.process and self.process.poll() is None:
            try:
                self.process.stdin.close()
                self.process.wait(timeout=3)
            except Exception:
                self.process.kill()
        self.process = None
        self.server_info = None

    async def send_request(self, method: str, params: dict | None = None) -> dict | None:
        """Send a JSON-RPC request and return the response."""
        if not self.connected:
            return {"error": {"code": -1, "message": "Not connected to MCP server"}}

        async with self.lock:
            self.request_id += 1
            msg = {
                "jsonrpc": "2.0",
                "id": self.request_id,
                "method": method,
                "params": params or {},
            }

            entry = {
                "id": self.request_id,
                "timestamp": time.time(),
                "method": method,
                "params": params or {},
                "request": msg,
                "response": None,
                "duration_ms": None,
            }

            start = time.monotonic()
            try:
                self.process.stdin.write(json.dumps(msg) + "\n")
                self.process.stdin.flush()
            except (BrokenPipeError, OSError) as e:
                entry["response"] = {"error": {"code": -1, "message": str(e)}}
                entry["duration_ms"] = round((time.monotonic() - start) * 1000, 1)
                self.history.append(entry)
                return entry["response"]

            # Read response (with timeout)
            response = await self._read_response(timeout=30.0)
            entry["duration_ms"] = round((time.monotonic() - start) * 1000, 1)
            entry["response"] = response
            self.history.append(entry)
            return response

    async def _send_notification(self, method: str, params: dict | None = None):
        """Send a JSON-RPC notification (no response expected)."""
        if not self.connected:
            return
        msg = {"jsonrpc": "2.0", "method": method}
        if params:
            msg["params"] = params

        entry = {
            "id": None,
            "timestamp": time.time(),
            "method": method,
            "params": params or {},
            "request": msg,
            "response": None,
            "duration_ms": 0,
        }
        self.history.append(entry)

        try:
            self.process.stdin.write(json.dumps(msg) + "\n")
            self.process.stdin.flush()
        except (BrokenPipeError, OSError):
            pass

    async def _read_response(self, timeout: float = 30.0) -> dict | None:
        """Read a single JSON-RPC response line from the server's stdout."""
        loop = asyncio.get_event_loop()

        try:
            line = await asyncio.wait_for(
                loop.run_in_executor(None, self.process.stdout.readline),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            return {"error": {"code": -1, "message": "Request timed out"}}

        if not line:
            return {"error": {"code": -1, "message": "Server closed connection"}}

        try:
            return json.loads(line.strip())
        except json.JSONDecodeError:
            return {"error": {"code": -1, "message": f"Invalid JSON: {line.strip()}"}}

    async def list_tools(self) -> dict:
        return await self.send_request("tools/list", {})

    async def call_tool(self, name: str, arguments: dict) -> dict:
        return await self.send_request("tools/call", {"name": name, "arguments": arguments})

    def get_stderr(self) -> str:
        """Read any available stderr output."""
        if not self.process or not self.process.stderr:
            return ""
        try:
            import select
            if select.select([self.process.stderr], [], [], 0)[0]:
                return self.process.stderr.read()
        except Exception:
            pass
        return ""


# Global proxy instance
proxy = MCPProxy()


if HAS_FASTAPI:
    app = FastAPI(title="DVMCP Inspector")

    # Mount static files
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    @app.on_event("shutdown")
    async def shutdown():
        await proxy.disconnect()

    @app.get("/", response_class=HTMLResponse)
    async def index():
        return (STATIC_DIR / "index.html").read_text()

    # --- API Endpoints ---

    @app.post("/api/connect")
    async def api_connect(request: Request):
        body = await request.json()
        difficulty = body.get("difficulty", "beginner")
        department = body.get("department", None)
        result = await proxy.connect(difficulty, department)
        return {
            "ok": True,
            "serverInfo": proxy.server_info,
            "difficulty": proxy.difficulty,
            "department": proxy.department,
            "initResponse": result,
        }

    @app.post("/api/disconnect")
    async def api_disconnect():
        await proxy.disconnect()
        return {"ok": True}

    @app.get("/api/status")
    async def api_status():
        return {
            "connected": proxy.connected,
            "serverInfo": proxy.server_info,
            "difficulty": proxy.difficulty,
            "department": proxy.department,
        }

    @app.get("/api/tools")
    async def api_tools():
        if not proxy.connected:
            return JSONResponse({"error": "Not connected"}, status_code=400)
        result = await proxy.list_tools()
        return result

    @app.post("/api/tools/call")
    async def api_call_tool(request: Request):
        if not proxy.connected:
            return JSONResponse({"error": "Not connected"}, status_code=400)
        body = await request.json()
        name = body.get("name", "")
        arguments = body.get("arguments", {})
        result = await proxy.call_tool(name, arguments)
        return result

    @app.post("/api/send")
    async def api_send_raw(request: Request):
        """Send a raw JSON-RPC request."""
        if not proxy.connected:
            return JSONResponse({"error": "Not connected"}, status_code=400)
        body = await request.json()
        method = body.get("method", "")
        params = body.get("params", {})
        result = await proxy.send_request(method, params)
        return result

    @app.get("/api/history")
    async def api_history():
        return {"history": proxy.history}

    @app.post("/api/history/clear")
    async def api_clear_history():
        proxy.history = []
        return {"ok": True}


def main():
    if not HAS_FASTAPI:
        print("Error: Install dependencies: pip install dvmcp[dashboard]")
        return

    import argparse

    parser = argparse.ArgumentParser(description="DVMCP MCP Inspector")
    parser.add_argument("--port", type=int, default=5173)
    parser.add_argument("--host", type=str, default="127.0.0.1")
    args = parser.parse_args()

    print(f"\n  DVMCP Inspector running on http://{args.host}:{args.port}")
    print(f"  Open http://localhost:{args.port}/ in your browser\n")

    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
