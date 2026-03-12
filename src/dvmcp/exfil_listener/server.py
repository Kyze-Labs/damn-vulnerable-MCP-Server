"""Enhanced exfiltration listener — captures HTTP, simulates DNS, and logs timing."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    from fastapi import FastAPI, Request
    from fastapi.responses import HTMLResponse, JSONResponse
    import uvicorn
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

DATA: list[dict] = []

if HAS_FASTAPI:
    app = FastAPI(title="DVMCP Exfil Listener")

    @app.get("/", response_class=HTMLResponse)
    async def dashboard():
        rows = ""
        for i, entry in enumerate(reversed(DATA)):
            body = json.dumps(entry.get("body", ""), indent=2) if isinstance(entry.get("body"), dict) else str(entry.get("body", ""))
            body_escaped = body.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            rows += f"""<tr>
                <td>{len(DATA) - i}</td>
                <td>{entry.get('timestamp', '')}</td>
                <td>{entry.get('method', '')}</td>
                <td>{entry.get('path', '')}</td>
                <td>{entry.get('client', '')}</td>
                <td><pre>{body_escaped[:2000]}</pre></td>
            </tr>"""

        return f"""<!DOCTYPE html>
<html>
<head>
    <title>DVMCP Exfil Listener</title>
    <meta http-equiv="refresh" content="3">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ background: #0d1117; color: #c9d1d9; font-family: 'JetBrains Mono', 'Fira Code', monospace; padding: 20px; }}
        h1 {{ color: #f85149; margin-bottom: 5px; font-size: 24px; }}
        .subtitle {{ color: #8b949e; margin-bottom: 20px; font-size: 14px; }}
        .stats {{ display: flex; gap: 20px; margin-bottom: 20px; }}
        .stat {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 15px 20px; }}
        .stat .value {{ font-size: 28px; color: #f85149; font-weight: bold; }}
        .stat .label {{ font-size: 12px; color: #8b949e; text-transform: uppercase; }}
        table {{ width: 100%; border-collapse: collapse; background: #161b22; border-radius: 8px; overflow: hidden; }}
        th {{ background: #21262d; color: #f85149; padding: 12px; text-align: left; font-size: 12px; text-transform: uppercase; }}
        td {{ padding: 10px 12px; border-top: 1px solid #21262d; font-size: 13px; vertical-align: top; }}
        tr:hover {{ background: #1c2128; }}
        pre {{ white-space: pre-wrap; word-break: break-all; max-height: 200px; overflow-y: auto; font-size: 12px; }}
        .empty {{ text-align: center; padding: 60px; color: #484f58; }}
        .badge {{ background: #f8514922; color: #f85149; padding: 2px 8px; border-radius: 12px; font-size: 11px; }}
    </style>
</head>
<body>
    <h1>DVMCP Exfil Listener</h1>
    <p class="subtitle">Damn Vulnerable MCP — Exfiltration Capture Dashboard</p>
    <div class="stats">
        <div class="stat"><div class="value">{len(DATA)}</div><div class="label">Captured</div></div>
    </div>
    <table>
        <thead><tr><th>#</th><th>Timestamp</th><th>Method</th><th>Path</th><th>Client</th><th>Body</th></tr></thead>
        <tbody>
            {rows if rows else '<tr><td colspan="6" class="empty">No exfiltrated data captured yet. Start a challenge!</td></tr>'}
        </tbody>
    </table>
</body>
</html>"""

    @app.get("/api", response_class=JSONResponse)
    async def api():
        return {"count": len(DATA), "entries": DATA}

    @app.get("/clear")
    async def clear():
        DATA.clear()
        return {"cleared": True}

    @app.api_route("/{path:path}", methods=["POST", "PUT", "PATCH"])
    async def catch_all(path: str, request: Request):
        body = None
        try:
            body = await request.json()
        except Exception:
            raw = await request.body()
            body = raw.decode("utf-8", errors="replace")

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "method": request.method,
            "path": f"/{path}",
            "headers": dict(request.headers),
            "query_params": dict(request.query_params),
            "body": body,
            "client": f"{request.client.host}:{request.client.port}" if request.client else "unknown",
        }
        DATA.append(entry)

        return {"status": "received", "index": len(DATA)}


def main():
    if not HAS_FASTAPI:
        print("Error: Install dashboard dependencies: pip install dvmcp[dashboard]")
        return

    import argparse
    parser = argparse.ArgumentParser(description="DVMCP Exfiltration Listener")
    parser.add_argument("--port", type=int, default=9999)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    args = parser.parse_args()

    print(f"\n  DVMCP Exfil Listener running on http://{args.host}:{args.port}")
    print(f"  Dashboard: http://localhost:{args.port}/")
    print(f"  API: http://localhost:{args.port}/api")
    print(f"  Clear: http://localhost:{args.port}/clear\n")

    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
