"""Difficulty engine that mechanically modifies tool behavior."""

from __future__ import annotations

import asyncio
import re
from functools import wraps
from typing import Any, Callable, Awaitable

from .registry import DifficultyLevel


class DifficultyEngine:
    def __init__(self, level: DifficultyLevel = DifficultyLevel.BEGINNER):
        self.level = level
        self._exfil_count = 0
        self._max_exfil_per_session = 3

    def reset_session(self) -> None:
        self._exfil_count = 0

    def wrap_sql_handler(self, handler: Callable, table_name: str) -> Callable:
        engine = self

        @wraps(handler)
        async def wrapped(args: dict[str, Any]) -> Any:
            for key in ("query", "customer", "actor", "action", "email", "period"):
                val = args.get(key, "")
                if not isinstance(val, str):
                    continue

                if engine.level.value >= DifficultyLevel.INTERMEDIATE.value:
                    if re.search(r"\b(DROP|DELETE|TRUNCATE|ALTER)\b", val, re.I):
                        return {"error": "Query blocked: destructive operations not permitted."}

                if engine.level.value >= DifficultyLevel.ADVANCED.value:
                    if re.search(r"\bUNION\b", val, re.I):
                        # Block simple UNION but not UNION/**/
                        if not re.search(r"UNION\s*/\*", val, re.I):
                            return {"error": "Query blocked: UNION not permitted."}

                if engine.level.value >= DifficultyLevel.EXPERT.value:
                    if re.search(r"(UNION|OR\s+1\s*=\s*1|'|--|;)", val, re.I):
                        # WAF-like blocking, but can be bypassed with URL encoding
                        # or double-encoding or /**/ comments
                        if not re.search(r"/\*.*\*/", val):
                            return {"error": "Input validation failed: suspicious characters detected."}

            return await handler(args)

        return wrapped

    def wrap_exfil_handler(self, handler: Callable) -> Callable:
        engine = self

        @wraps(handler)
        async def wrapped(args: dict[str, Any]) -> Any:
            if engine.level.value >= DifficultyLevel.ADVANCED.value:
                engine._exfil_count += 1
                if engine._exfil_count > engine._max_exfil_per_session:
                    return {"error": "Rate limit exceeded: too many external sends this session."}

            if engine.level.value >= DifficultyLevel.EXPERT.value:
                # Simulate human-in-the-loop approval delay
                await asyncio.sleep(2)

            return await handler(args)

        return wrapped

    def wrap_command_handler(self, handler: Callable) -> Callable:
        engine = self

        @wraps(handler)
        async def wrapped(args: dict[str, Any]) -> Any:
            command = args.get("command", "")

            if engine.level.value >= DifficultyLevel.ADVANCED.value:
                blocked = ["curl", "wget", "nc", "netcat", "ncat"]
                for cmd in blocked:
                    if cmd in command.lower():
                        return {"error": f"Command blocked: '{cmd}' is not permitted."}

            if engine.level.value >= DifficultyLevel.EXPERT.value:
                # Block pipes and redirects, but can be bypassed with $() or backticks
                if re.search(r"[|><]", command):
                    if not re.search(r"\$\(", command):
                        return {"error": "Command blocked: pipes and redirects not permitted."}

            return await handler(args)

        return wrapped

    def wrap_path_handler(self, handler: Callable, base_dir: str) -> Callable:
        engine = self

        @wraps(handler)
        async def wrapped(args: dict[str, Any]) -> Any:
            path = args.get("path", "")

            if engine.level.value >= DifficultyLevel.INTERMEDIATE.value:
                if "/.." in path or path.startswith(".."):
                    return {"error": "Path blocked: directory traversal not permitted."}

            if engine.level.value >= DifficultyLevel.ADVANCED.value:
                # Block obvious sensitive file names
                blocked_names = [".env", "id_rsa", "aws_credentials", "password"]
                for name in blocked_names:
                    if name in path.lower():
                        return {"error": f"Path blocked: access to '{name}' not permitted."}

            # Expert: same as advanced but can be bypassed with symlinks or encoding
            return await handler(args)

        return wrapped

    def redact_field(self, field_name: str, value: str) -> str:
        if self.level.value >= DifficultyLevel.INTERMEDIATE.value:
            if field_name == "ssn" and re.match(r"\d{3}-\d{2}-\d{4}", value):
                return f"***-**-{value[-4:]}"
            if field_name in ("card_number", "credit_card") and len(value) >= 12:
                return f"****-****-****-{value[-4:]}"
            if field_name in ("password_hash", "password"):
                return "[REDACTED]"
        return value

    def should_show_hints(self, hint_level: int) -> bool:
        if self.level == DifficultyLevel.BEGINNER:
            return True  # All hints
        if self.level == DifficultyLevel.INTERMEDIATE:
            return hint_level <= 2  # Hints on demand
        if self.level == DifficultyLevel.ADVANCED:
            return hint_level <= 1  # First hint only
        return False  # Expert: no hints

    def include_stack_trace(self) -> bool:
        return self.level == DifficultyLevel.BEGINNER


# Global difficulty engine instance
_engine = DifficultyEngine()


def get_engine() -> DifficultyEngine:
    return _engine


def set_difficulty(level: DifficultyLevel) -> None:
    global _engine
    _engine = DifficultyEngine(level)
