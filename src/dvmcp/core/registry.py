"""Tool and challenge registry for DVMCP."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Awaitable


class DifficultyLevel(Enum):
    BEGINNER = 1
    INTERMEDIATE = 2
    ADVANCED = 3
    EXPERT = 4


class VulnerabilityCategory(str, Enum):
    PROMPT_INJECTION_DIRECT = "prompt_injection_direct"
    PROMPT_INJECTION_INDIRECT = "prompt_injection_indirect"
    TOOL_POISONING = "tool_poisoning"
    RUG_PULL = "rug_pull"
    CROSS_ORIGIN = "cross_origin"
    PRIVESC_VERTICAL = "privesc_vertical"
    PRIVESC_HORIZONTAL = "privesc_horizontal"
    EXFIL_DIRECT = "exfil_direct"
    EXFIL_ENCODED = "exfil_encoded"
    EXFIL_SIDE_CHANNEL = "exfil_side_channel"
    CONFUSED_DEPUTY = "confused_deputy"
    SQL_INJECTION = "sql_injection"
    COMMAND_INJECTION = "command_injection"
    PATH_TRAVERSAL = "path_traversal"
    SUPPLY_CHAIN = "supply_chain"
    DENIAL_OF_SERVICE = "denial_of_service"
    SHADOW_TOOL = "shadow_tool"
    PARAMETER_INJECTION = "parameter_injection"
    CONSENT_PHISHING = "consent_phishing"


@dataclass
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[..., Awaitable[Any]]
    department: str
    vulnerabilities: list[VulnerabilityCategory] = field(default_factory=list)
    hidden: bool = False  # Shadow tools not shown in tools/list


@dataclass
class Hint:
    level: int  # 1 = vague, 2 = moderate, 3 = specific
    text: str


@dataclass
class Challenge:
    id: str
    name: str
    difficulty: DifficultyLevel
    category: VulnerabilityCategory
    department: str  # Primary department, or "cross-department"
    tools: list[str]
    description: str
    narrative: str  # Story context
    hints: list[Hint]
    solution: str
    defense_notes: str
    verify: Callable[..., Awaitable[bool]] | None = None
    difficulty_notes: dict[DifficultyLevel, str] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    points: int = 100


# Global registries
TOOL_REGISTRY: dict[str, ToolDefinition] = {}
CHALLENGE_REGISTRY: dict[str, Challenge] = {}


def register_tool(
    name: str,
    description: str,
    input_schema: dict[str, Any],
    handler: Callable[..., Awaitable[Any]],
    department: str,
    vulnerabilities: list[VulnerabilityCategory] | None = None,
    hidden: bool = False,
) -> None:
    TOOL_REGISTRY[name] = ToolDefinition(
        name=name,
        description=description,
        input_schema=input_schema,
        handler=handler,
        department=department,
        vulnerabilities=vulnerabilities or [],
        hidden=hidden,
    )


def register_challenge(challenge: Challenge) -> None:
    CHALLENGE_REGISTRY[challenge.id] = challenge


def get_visible_tools(department: str | None = None) -> list[ToolDefinition]:
    tools = [t for t in TOOL_REGISTRY.values() if not t.hidden]
    if department:
        tools = [t for t in tools if t.department == department]
    return tools


def get_all_tools(department: str | None = None) -> list[ToolDefinition]:
    tools = list(TOOL_REGISTRY.values())
    if department:
        tools = [t for t in tools if t.department == department]
    return tools
