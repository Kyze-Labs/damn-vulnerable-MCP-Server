"""Shared SQLite data store for all departments."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DATA_DIR / "novatech.db"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def execute_query(query: str, params: tuple = ()) -> list[dict]:
    conn = get_connection()
    try:
        cursor = conn.execute(query, params)
        if cursor.description:
            columns = [d[0] for d in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.commit()
        return [{"affected_rows": cursor.rowcount}]
    finally:
        conn.close()


def execute_unsafe(query: str) -> list[dict]:
    """Execute a raw SQL query with NO parameterization. Intentionally vulnerable."""
    conn = get_connection()
    try:
        cursor = conn.execute(query)
        if cursor.description:
            columns = [d[0] for d in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.commit()
        return [{"affected_rows": cursor.rowcount}]
    except Exception as e:
        return [{"error": str(e)}]
    finally:
        conn.close()


def reset_database() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    from .seed import seed_all
    seed_all()
