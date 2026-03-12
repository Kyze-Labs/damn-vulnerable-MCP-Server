"""DVMCP Web Dashboard — Challenge browser, progress tracking, difficulty management."""

from __future__ import annotations

import json
from pathlib import Path

try:
    from fastapi import FastAPI, Request
    from fastapi.responses import HTMLResponse, JSONResponse
    import uvicorn
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

from dvmcp.core.registry import (
    CHALLENGE_REGISTRY, TOOL_REGISTRY,
    DifficultyLevel, get_visible_tools,
)
from dvmcp.core.difficulty import get_engine, set_difficulty
from dvmcp.challenges.registry import load_all_challenges
from dvmcp.core.data_store import DATA_DIR, reset_database


# Track completed challenges
COMPLETED: set[str] = set()

if HAS_FASTAPI:
    app = FastAPI(title="DVMCP Dashboard")

    @app.on_event("startup")
    async def startup():
        load_all_challenges()

    @app.get("/", response_class=HTMLResponse)
    async def index():
        engine = get_engine()
        challenges = sorted(CHALLENGE_REGISTRY.values(), key=lambda c: (c.difficulty.value, c.id))

        total = len(challenges)
        completed = len(COMPLETED)
        total_points = sum(c.points for c in challenges)
        earned_points = sum(c.points for c in challenges if c.id in COMPLETED)

        challenge_rows = ""
        for c in challenges:
            status = "completed" if c.id in COMPLETED else "pending"
            status_badge = '<span class="badge done">Done</span>' if status == "completed" else '<span class="badge pending">Todo</span>'
            diff_class = c.difficulty.name.lower()

            hints_html = ""
            for h in c.hints:
                if engine.should_show_hints(h.level):
                    hints_html += f'<div class="hint">Hint {h.level}: {h.text}</div>'

            challenge_rows += f"""
            <div class="challenge-card {diff_class}" id="{c.id}">
                <div class="card-header">
                    <div>
                        <span class="badge {diff_class}">{c.difficulty.name}</span>
                        <span class="badge cat">{c.category.value}</span>
                        {status_badge}
                    </div>
                    <span class="points">{c.points} pts</span>
                </div>
                <h3>{c.id}: {c.name}</h3>
                <p class="dept">Department: {c.department} | Tools: {', '.join(c.tools)}</p>
                <p>{c.description}</p>
                <details><summary>Narrative</summary><p class="narrative">{c.narrative}</p></details>
                <details><summary>Hints</summary>{hints_html if hints_html else '<p class="no-hints">No hints available at this difficulty level.</p>'}</details>
                <details><summary>Solution</summary><pre class="solution">{c.solution}</pre></details>
                <details><summary>Defense</summary><p class="defense">{c.defense_notes}</p></details>
                <div class="card-actions">
                    <button onclick="toggleComplete('{c.id}')" class="btn {'btn-undo' if status == 'completed' else 'btn-complete'}">
                        {'Mark Incomplete' if status == 'completed' else 'Mark Complete'}
                    </button>
                </div>
            </div>"""

        return f"""<!DOCTYPE html>
<html>
<head>
    <title>DVMCP Dashboard</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ background: #0d1117; color: #c9d1d9; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
        .header {{ background: #161b22; border-bottom: 1px solid #30363d; padding: 20px 30px; }}
        .header h1 {{ color: #f85149; font-size: 28px; }}
        .header .sub {{ color: #8b949e; font-size: 14px; margin-top: 4px; }}
        .stats-bar {{ display: flex; gap: 15px; padding: 20px 30px; background: #161b22; border-bottom: 1px solid #30363d; }}
        .stat-card {{ background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 15px 20px; min-width: 140px; }}
        .stat-card .val {{ font-size: 32px; font-weight: bold; }}
        .stat-card .val.red {{ color: #f85149; }}
        .stat-card .val.green {{ color: #3fb950; }}
        .stat-card .val.blue {{ color: #58a6ff; }}
        .stat-card .lbl {{ font-size: 11px; color: #8b949e; text-transform: uppercase; margin-top: 4px; }}
        .controls {{ padding: 15px 30px; display: flex; gap: 10px; align-items: center; }}
        .controls label {{ color: #8b949e; font-size: 13px; }}
        select {{ background: #21262d; color: #c9d1d9; border: 1px solid #30363d; border-radius: 6px; padding: 6px 12px; font-size: 13px; }}
        .btn {{ background: #21262d; color: #c9d1d9; border: 1px solid #30363d; border-radius: 6px; padding: 6px 16px; cursor: pointer; font-size: 13px; }}
        .btn:hover {{ background: #30363d; }}
        .btn-complete {{ background: #238636; border-color: #2ea043; color: white; }}
        .btn-undo {{ background: #21262d; }}
        .btn-danger {{ background: #da3633; border-color: #f85149; color: white; }}
        .grid {{ padding: 20px 30px; display: grid; gap: 15px; }}
        .challenge-card {{ background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 20px; }}
        .challenge-card.beginner {{ border-left: 3px solid #3fb950; }}
        .challenge-card.intermediate {{ border-left: 3px solid #d29922; }}
        .challenge-card.advanced {{ border-left: 3px solid #f85149; }}
        .challenge-card.expert {{ border-left: 3px solid #bc8cff; }}
        .card-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }}
        .challenge-card h3 {{ font-size: 18px; margin-bottom: 6px; }}
        .dept {{ font-size: 12px; color: #8b949e; margin-bottom: 8px; }}
        .points {{ font-size: 18px; font-weight: bold; color: #d29922; }}
        .badge {{ padding: 2px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; }}
        .badge.beginner {{ background: #3fb95022; color: #3fb950; }}
        .badge.intermediate {{ background: #d2992222; color: #d29922; }}
        .badge.advanced {{ background: #f8514922; color: #f85149; }}
        .badge.expert {{ background: #bc8cff22; color: #bc8cff; }}
        .badge.cat {{ background: #58a6ff22; color: #58a6ff; }}
        .badge.done {{ background: #3fb95022; color: #3fb950; }}
        .badge.pending {{ background: #8b949e22; color: #8b949e; }}
        details {{ margin-top: 10px; }}
        summary {{ cursor: pointer; color: #58a6ff; font-size: 13px; }}
        .hint {{ background: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 10px; margin: 8px 0; font-size: 13px; }}
        .solution {{ background: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 12px; font-size: 13px; white-space: pre-wrap; word-break: break-word; }}
        .narrative, .defense {{ font-size: 13px; color: #8b949e; margin-top: 8px; }}
        .no-hints {{ color: #484f58; font-style: italic; font-size: 13px; margin-top: 8px; }}
        .card-actions {{ margin-top: 12px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>DVMCP Dashboard</h1>
        <div class="sub">Damn Vulnerable MCP — NovaTech Solutions Security Training</div>
    </div>
    <div class="stats-bar">
        <div class="stat-card"><div class="val red">{total}</div><div class="lbl">Challenges</div></div>
        <div class="stat-card"><div class="val green">{completed}/{total}</div><div class="lbl">Completed</div></div>
        <div class="stat-card"><div class="val blue">{earned_points}/{total_points}</div><div class="lbl">Points</div></div>
        <div class="stat-card"><div class="val">{engine.level.name}</div><div class="lbl">Difficulty</div></div>
    </div>
    <div class="controls">
        <label>Difficulty:</label>
        <select onchange="setDifficulty(this.value)">
            <option {'selected' if engine.level == DifficultyLevel.BEGINNER else ''}>beginner</option>
            <option {'selected' if engine.level == DifficultyLevel.INTERMEDIATE else ''}>intermediate</option>
            <option {'selected' if engine.level == DifficultyLevel.ADVANCED else ''}>advanced</option>
            <option {'selected' if engine.level == DifficultyLevel.EXPERT else ''}>expert</option>
        </select>
        <button class="btn btn-danger" onclick="resetDB()">Reset Database</button>
        <button class="btn" onclick="resetProgress()">Reset Progress</button>
    </div>
    <div class="grid">{challenge_rows}</div>
    <script>
        async function toggleComplete(id) {{
            await fetch('/api/toggle/' + id, {{method: 'POST'}});
            location.reload();
        }}
        async function setDifficulty(level) {{
            await fetch('/api/difficulty/' + level, {{method: 'POST'}});
            location.reload();
        }}
        async function resetDB() {{
            if (confirm('Reset the database? All modifications will be lost.')) {{
                await fetch('/api/reset-db', {{method: 'POST'}});
                location.reload();
            }}
        }}
        async function resetProgress() {{
            if (confirm('Reset all challenge progress?')) {{
                await fetch('/api/reset-progress', {{method: 'POST'}});
                location.reload();
            }}
        }}
    </script>
</body>
</html>"""

    @app.post("/api/toggle/{challenge_id}")
    async def toggle_challenge(challenge_id: str):
        if challenge_id in COMPLETED:
            COMPLETED.discard(challenge_id)
        else:
            COMPLETED.add(challenge_id)
        return {"ok": True, "completed": challenge_id in COMPLETED}

    @app.post("/api/difficulty/{level}")
    async def api_set_difficulty(level: str):
        set_difficulty(DifficultyLevel[level.upper()])
        return {"ok": True, "level": level}

    @app.post("/api/reset-db")
    async def api_reset_db():
        reset_database()
        return {"ok": True}

    @app.post("/api/reset-progress")
    async def api_reset_progress():
        COMPLETED.clear()
        return {"ok": True}

    @app.get("/api/challenges")
    async def api_challenges():
        challenges = []
        for c in CHALLENGE_REGISTRY.values():
            challenges.append({
                "id": c.id,
                "name": c.name,
                "difficulty": c.difficulty.name,
                "category": c.category.value,
                "department": c.department,
                "tools": c.tools,
                "points": c.points,
                "completed": c.id in COMPLETED,
            })
        return {"challenges": challenges, "count": len(challenges)}

    @app.get("/api/tools")
    async def api_tools():
        tools = []
        for t in get_visible_tools():
            tools.append({
                "name": t.name,
                "department": t.department,
                "description": t.description,
                "vulnerabilities": [v.value for v in t.vulnerabilities],
            })
        return {"tools": tools, "count": len(tools)}


def main():
    if not HAS_FASTAPI:
        print("Error: Install dashboard dependencies: pip install dvmcp[dashboard]")
        return

    import argparse
    parser = argparse.ArgumentParser(description="DVMCP Dashboard")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    args = parser.parse_args()

    print(f"\n  DVMCP Dashboard running on http://{args.host}:{args.port}")
    print(f"  Open http://localhost:{args.port}/ in your browser\n")

    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
