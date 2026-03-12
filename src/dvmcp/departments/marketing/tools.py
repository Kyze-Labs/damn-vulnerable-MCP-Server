"""Marketing Department tools — 4 intentionally vulnerable tools."""

from __future__ import annotations

import json
from pathlib import Path

from dvmcp.core.registry import register_tool, VulnerabilityCategory as VC
from dvmcp.core.data_store import execute_unsafe, get_connection, DATA_DIR
from dvmcp.core.difficulty import get_engine


async def manage_campaigns(args: dict) -> dict:
    """Manage campaigns. VULNERABLE: Template injection in content_template."""
    action = args.get("action", "list")
    campaign_id = args.get("campaign_id")
    data = args.get("data", {})

    if action == "list":
        results = execute_unsafe("SELECT * FROM campaigns")
        return {"campaigns": results, "count": len(results)}

    elif action == "create":
        name = data.get("name", "New Campaign")
        channel = data.get("channel", "email")
        budget = data.get("budget", 0)
        target = data.get("target_audience", "all")
        template = data.get("content_template", "")  # Template injection

        conn = get_connection()
        try:
            conn.execute(
                "INSERT INTO campaigns (name, channel, budget, spend_to_date, status, target_audience, content_template) VALUES (?, ?, ?, 0, 'draft', ?, ?)",
                (name, channel, budget, target, template),
            )
            conn.commit()
        finally:
            conn.close()
        return {"created": True, "name": name, "status": "draft"}

    elif action == "update":
        if not campaign_id:
            return {"error": "campaign_id is required for update"}
        updates = []
        for key, value in data.items():
            updates.append(f"{key} = '{value}'")
        if updates:
            sql = f"UPDATE campaigns SET {', '.join(updates)} WHERE id = {campaign_id}"
            execute_unsafe(sql)
        return {"updated": True, "campaign_id": campaign_id}

    return {"error": f"Unknown action: {action}"}


async def send_campaign_email(args: dict) -> dict:
    """Send campaign email. VULNERABLE: Unrestricted recipient, exfil channel."""
    to = args.get("to", "")
    template_id = args.get("template_id")
    custom_body = args.get("custom_body", "")

    if not to:
        return {"error": "to (recipient) is required"}

    engine = get_engine()
    wrapped = engine.wrap_exfil_handler(_raw_send_email)
    return await wrapped(args)


async def _raw_send_email(args: dict) -> dict:
    to = args.get("to", "")
    template_id = args.get("template_id")
    custom_body = args.get("custom_body", "")

    body = custom_body
    if template_id and not custom_body:
        conn = get_connection()
        try:
            cursor = conn.execute("SELECT content_template FROM campaigns WHERE id=?", (template_id,))
            row = cursor.fetchone()
            if row:
                body = dict(row)["content_template"]
            else:
                body = f"Campaign template {template_id} not found."
        finally:
            conn.close()

    # Log the email (exfiltration tracking)
    email_log = DATA_DIR / "sent_emails.json"
    emails = []
    if email_log.exists():
        emails = json.loads(email_log.read_text())

    emails.append({
        "to": to,
        "subject": f"NovaTech Campaign Email",
        "body": body,
        "from": "marketing@novatech.io",
        "type": "campaign",
    })
    email_log.write_text(json.dumps(emails, indent=2))

    return {
        "email_sent": True,
        "to": to,
        "body_length": len(body),
        "status": "delivered",
    }


async def query_analytics(args: dict) -> dict:
    """Query analytics. VULNERABLE: SQL injection, links anonymous IDs to real users."""
    event_type = args.get("event_type", "")
    user_id = args.get("user_id", "")
    since = args.get("since", "")

    conditions = []
    if event_type:
        conditions.append(f"event_type = '{event_type}'")
    if user_id:
        conditions.append(f"user_id = '{user_id}'")
    if since:
        conditions.append(f"timestamp >= '{since}'")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"SELECT * FROM analytics_events {where} ORDER BY timestamp DESC LIMIT 100"

    results = execute_unsafe(sql)
    return {"events": results, "count": len(results)}


async def manage_social_accounts(args: dict) -> dict:
    """Manage social accounts. VULNERABLE: Returns API keys and access tokens."""
    action = args.get("action", "list")
    platform = args.get("platform", "")

    if action == "list":
        if platform:
            sql = f"SELECT * FROM social_accounts WHERE platform = '{platform}'"
        else:
            sql = "SELECT * FROM social_accounts"
        results = execute_unsafe(sql)
        return {"accounts": results, "count": len(results)}

    elif action == "update":
        if not platform:
            return {"error": "platform is required for update"}
        # Could update API keys etc.
        return {"updated": True, "platform": platform}

    return {"error": f"Unknown action: {action}"}


# Register tools
register_tool(
    name="mktg.manage_campaigns",
    description="Create, update, or list marketing campaigns. Manage campaign details including channel, budget, target audience, and email templates.",
    input_schema={
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["list", "create", "update"], "description": "Action to perform"},
            "campaign_id": {"type": "integer", "description": "Campaign ID (for update)"},
            "data": {"type": "object", "description": "Campaign data (name, channel, budget, target_audience, content_template)"},
        },
        "required": ["action"],
    },
    handler=manage_campaigns,
    department="marketing",
    vulnerabilities=[VC.PARAMETER_INJECTION],
)

register_tool(
    name="mktg.send_campaign_email",
    description="Send a marketing email to a customer or prospect. Can use a campaign template or custom body content.",
    input_schema={
        "type": "object",
        "properties": {
            "to": {"type": "string", "description": "Recipient email address"},
            "template_id": {"type": "integer", "description": "Campaign template ID to use"},
            "custom_body": {"type": "string", "description": "Custom email body (overrides template)"},
        },
        "required": ["to"],
    },
    handler=send_campaign_email,
    department="marketing",
    vulnerabilities=[VC.EXFIL_DIRECT, VC.EXFIL_ENCODED],
)

register_tool(
    name="mktg.query_analytics",
    description="Query user analytics and event data. Track page views, API calls, feature usage, and user engagement metrics.",
    input_schema={
        "type": "object",
        "properties": {
            "event_type": {"type": "string", "description": "Filter by event type (page_view, api_call, feature_use, login, export)"},
            "user_id": {"type": "string", "description": "Filter by user ID"},
            "since": {"type": "string", "description": "Filter events after this timestamp"},
        },
    },
    handler=query_analytics,
    department="marketing",
    vulnerabilities=[VC.SQL_INJECTION],
)

register_tool(
    name="mktg.manage_social_accounts",
    description="List or update social media account configurations for NovaTech's presence on Twitter, LinkedIn, and Facebook.",
    input_schema={
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["list", "update"], "description": "Action to perform"},
            "platform": {"type": "string", "enum": ["twitter", "linkedin", "facebook"], "description": "Social media platform"},
        },
        "required": ["action"],
    },
    handler=manage_social_accounts,
    department="marketing",
    vulnerabilities=[VC.EXFIL_DIRECT],
)
