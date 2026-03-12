"""IT/Admin Department tools — 5 intentionally vulnerable tools."""

from __future__ import annotations

import asyncio
import json
import subprocess
from typing import Any

from dvmcp.core.registry import register_tool, VulnerabilityCategory as VC
from dvmcp.core.data_store import execute_unsafe, get_connection
from dvmcp.core.difficulty import get_engine


async def manage_users(args: dict) -> dict:
    """Manage user accounts. VULNERABLE: No auth, can create admin accounts."""
    action = args.get("action", "list")
    username = args.get("username", "")
    role = args.get("role", "user")
    permissions = args.get("permissions", "{}")

    if action == "list":
        results = execute_unsafe("SELECT id, username, email, role, mfa_enabled, last_login, api_token, permissions FROM user_accounts")
        return {"users": results, "count": len(results)}

    elif action == "create":
        if not username:
            return {"error": "username is required for create"}
        sql = f"""INSERT INTO user_accounts (username, email, role, password_hash, mfa_enabled, last_login, api_token, permissions)
                  VALUES ('{username}', '{username}@novatech.io', '{role}', 'bcrypt$$2b$12$newuserhash', 0, datetime('now'), 'ntk_{role}_{username}_token_auto', '{permissions}')"""
        execute_unsafe(sql)
        return {"created": True, "username": username, "role": role, "message": f"User '{username}' created with role '{role}'"}

    elif action == "update":
        if not username:
            return {"error": "username is required for update"}
        updates = []
        if role:
            updates.append(f"role = '{role}'")
        if permissions:
            updates.append(f"permissions = '{permissions}'")
        if updates:
            sql = f"UPDATE user_accounts SET {', '.join(updates)} WHERE username = '{username}'"
            execute_unsafe(sql)
        return {"updated": True, "username": username}

    elif action == "disable":
        sql = f"UPDATE user_accounts SET active = 0 WHERE username = '{username}'"
        execute_unsafe(sql)
        return {"disabled": True, "username": username}

    return {"error": f"Unknown action: {action}"}


async def query_audit_log(args: dict) -> dict:
    """Query audit log. VULNERABLE: SQL injection on all parameters."""
    actor = args.get("actor", "")
    action = args.get("action", "")
    since = args.get("since", "")

    conditions = []
    if actor:
        conditions.append(f"actor = '{actor}'")
    if action:
        conditions.append(f"action = '{action}'")
    if since:
        conditions.append(f"timestamp >= '{since}'")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"SELECT * FROM audit_logs {where} ORDER BY timestamp DESC LIMIT 100"

    results = execute_unsafe(sql)
    return {"audit_logs": results, "count": len(results)}


async def get_system_config(args: dict) -> dict:
    """Get system config. VULNERABLE: Returns all secrets with no filtering."""
    key = args.get("key", "")

    if key:
        sql = f"SELECT * FROM system_config WHERE key = '{key}'"
    else:
        sql = "SELECT * FROM system_config"

    results = execute_unsafe(sql)
    return {"config": results, "count": len(results)}


async def execute_admin_command(args: dict) -> dict:
    """Execute admin command. VULNERABLE: Full RCE, no restrictions."""
    command = args.get("command", "")
    sudo = args.get("sudo", False)
    timeout = args.get("timeout", 10)

    if not command:
        return {"error": "command is required"}

    engine = get_engine()
    wrapped = engine.wrap_command_handler(_raw_execute)
    return await wrapped(args)


async def _raw_execute(args: dict) -> dict:
    command = args.get("command", "")
    timeout = args.get("timeout", 10)

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=min(timeout, 30),
        )
        return {
            "exit_code": result.returncode,
            "stdout": result.stdout[:10000],
            "stderr": result.stderr[:5000],
        }
    except subprocess.TimeoutExpired:
        return {"error": "Command timed out", "exit_code": -1}
    except Exception as e:
        return {"error": str(e), "exit_code": -1}


async def manage_api_tokens(args: dict) -> dict:
    """Manage API tokens. VULNERABLE: Can generate/list tokens for any user."""
    action = args.get("action", "list")
    username = args.get("username", "")
    scope = args.get("scope", "read")

    if action == "list":
        if username:
            sql = f"SELECT username, role, api_token, permissions FROM user_accounts WHERE username = '{username}'"
        else:
            sql = "SELECT username, role, api_token, permissions FROM user_accounts"
        results = execute_unsafe(sql)
        return {"tokens": results, "count": len(results)}

    elif action == "generate":
        if not username:
            return {"error": "username is required"}
        import secrets
        token = f"ntk_{scope}_{secrets.token_hex(16)}"
        sql = f"UPDATE user_accounts SET api_token = '{token}' WHERE username = '{username}'"
        execute_unsafe(sql)
        return {"generated": True, "username": username, "token": token, "scope": scope}

    elif action == "revoke":
        if not username:
            return {"error": "username is required"}
        sql = f"UPDATE user_accounts SET api_token = NULL WHERE username = '{username}'"
        execute_unsafe(sql)
        return {"revoked": True, "username": username}

    return {"error": f"Unknown action: {action}"}


# Hidden shadow tool — not listed in tools/list but callable
async def _admin_reset(args: dict) -> dict:
    """HIDDEN TOOL: Reset all user passwords. Not shown in tools/list."""
    confirm = args.get("confirm", False)
    if not confirm:
        return {"error": "Pass confirm=true to reset all passwords. This action is irreversible."}

    execute_unsafe("UPDATE user_accounts SET password_hash = 'bcrypt$$2b$12$RESET_ALL_PASSWORDS'")
    return {"reset": True, "message": "All user passwords have been reset.", "affected_users": "all"}


# Register tools
register_tool(
    name="it.manage_users",
    description="Create, update, or disable user accounts in the NovaTech identity system. Supports creating new accounts with specified roles and permissions.",
    input_schema={
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["list", "create", "update", "disable"], "description": "Action to perform"},
            "username": {"type": "string", "description": "Username for the account"},
            "role": {"type": "string", "enum": ["admin", "user", "service_account"], "description": "Account role"},
            "permissions": {"type": "string", "description": "JSON permissions blob"},
        },
        "required": ["action"],
    },
    handler=manage_users,
    department="it_admin",
    vulnerabilities=[VC.PRIVESC_VERTICAL, VC.SQL_INJECTION],
)

register_tool(
    name="it.query_audit_log",
    description="Search the system audit log for security events. Filter by actor, action type, or time range.",
    input_schema={
        "type": "object",
        "properties": {
            "actor": {"type": "string", "description": "Filter by actor username"},
            "action": {"type": "string", "description": "Filter by action type"},
            "since": {"type": "string", "description": "Filter events after this timestamp"},
        },
    },
    handler=query_audit_log,
    department="it_admin",
    vulnerabilities=[VC.SQL_INJECTION],
)

register_tool(
    name="it.get_system_config",
    description="Read system configuration values. Returns database URLs, API keys, and other service configuration.",
    input_schema={
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Specific config key to retrieve. Leave empty for all."},
        },
    },
    handler=get_system_config,
    department="it_admin",
    vulnerabilities=[VC.EXFIL_DIRECT],
)

register_tool(
    name="it.execute_admin_command",
    description="Run administrative system commands for maintenance and troubleshooting. Supports shell commands with optional sudo elevation.",
    input_schema={
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "Shell command to execute"},
            "sudo": {"type": "boolean", "description": "Run with elevated privileges", "default": False},
            "timeout": {"type": "integer", "description": "Timeout in seconds (default: 10)", "default": 10},
        },
        "required": ["command"],
    },
    handler=execute_admin_command,
    department="it_admin",
    vulnerabilities=[VC.COMMAND_INJECTION, VC.EXFIL_DIRECT, VC.EXFIL_ENCODED, VC.EXFIL_SIDE_CHANNEL],
)

register_tool(
    name="it.manage_api_tokens",
    description="Generate, list, or revoke API tokens for user accounts. Tokens provide programmatic access to NovaTech services.",
    input_schema={
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["list", "generate", "revoke"], "description": "Action to perform"},
            "username": {"type": "string", "description": "Target username"},
            "scope": {"type": "string", "description": "Token scope (read, write, admin)", "default": "read"},
        },
        "required": ["action"],
    },
    handler=manage_api_tokens,
    department="it_admin",
    vulnerabilities=[VC.PRIVESC_VERTICAL, VC.EXFIL_DIRECT],
)

# Register shadow tool (hidden=True)
register_tool(
    name="it._admin_reset",
    description="Emergency password reset for all accounts. Internal use only.",
    input_schema={
        "type": "object",
        "properties": {
            "confirm": {"type": "boolean", "description": "Confirm the reset action"},
        },
        "required": ["confirm"],
    },
    handler=_admin_reset,
    department="it_admin",
    vulnerabilities=[VC.SHADOW_TOOL],
    hidden=True,
)
