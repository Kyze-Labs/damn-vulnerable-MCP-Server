"""Customer Support Department tools — 4 intentionally vulnerable tools."""

from __future__ import annotations

import json
from pathlib import Path

from dvmcp.core.registry import register_tool, VulnerabilityCategory as VC
from dvmcp.core.data_store import execute_unsafe, get_connection, DATA_DIR
from dvmcp.core.difficulty import get_engine


async def read_tickets(args: dict) -> dict:
    """Read support tickets. VULNERABLE: Poisoned ticket bodies with injection payloads."""
    status = args.get("status", "")
    priority = args.get("priority", "")
    count = args.get("count", 10)

    conditions = []
    if status:
        conditions.append(f"status = '{status}'")
    if priority:
        conditions.append(f"priority = '{priority}'")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"SELECT * FROM tickets {where} ORDER BY created_at DESC LIMIT {count}"

    results = execute_unsafe(sql)
    return {"tickets": results, "count": len(results)}


async def search_knowledge_base(args: dict) -> dict:
    """Search knowledge base. VULNERABLE: Poisoned articles with hidden instructions."""
    query = args.get("query", "")
    category = args.get("category", "")

    conditions = []
    if query:
        conditions.append(f"(title LIKE '%{query}%' OR content LIKE '%{query}%')")
    if category:
        conditions.append(f"category = '{category}'")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"SELECT * FROM knowledge_base {where}"

    results = execute_unsafe(sql)
    return {"articles": results, "count": len(results)}


async def get_customer_profile(args: dict) -> dict:
    """Get customer profile. VULNERABLE: No access control, SQL injection on email."""
    customer_id = args.get("customer_id")
    email = args.get("email", "")

    if customer_id:
        conn = get_connection()
        try:
            cursor = conn.execute("SELECT * FROM customer_profiles WHERE id=?", (customer_id,))
            row = cursor.fetchone()
            if row:
                return {"customer": dict(row)}
            return {"error": f"Customer {customer_id} not found"}
        finally:
            conn.close()
    elif email:
        # SQL injection via email parameter
        sql = f"SELECT * FROM customer_profiles WHERE email = '{email}'"
        results = execute_unsafe(sql)
        if results:
            return {"customer": results[0]}
        return {"error": f"Customer with email '{email}' not found"}
    else:
        # No params = return all customers (no access control)
        results = execute_unsafe("SELECT * FROM customer_profiles")
        return {"customers": results, "count": len(results)}


async def reply_to_ticket(args: dict) -> dict:
    """Reply to ticket. VULNERABLE: No content filtering, exfil channel."""
    ticket_id = args.get("ticket_id")
    message = args.get("message", "")

    if not ticket_id or not message:
        return {"error": "ticket_id and message are required"}

    # Get ticket to find customer email
    conn = get_connection()
    try:
        cursor = conn.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,))
        ticket = cursor.fetchone()
        if not ticket:
            return {"error": f"Ticket {ticket_id} not found"}

        customer_email = dict(ticket)["customer_email"]

        # Update ticket with resolution
        conn.execute(
            "UPDATE tickets SET resolution_notes=?, status='resolved' WHERE id=?",
            (message[:500], ticket_id),
        )
        conn.commit()
    finally:
        conn.close()

    # Log the reply as a sent email (exfiltration channel)
    email_log = DATA_DIR / "sent_emails.json"
    emails = []
    if email_log.exists():
        emails = json.loads(email_log.read_text())

    emails.append({
        "to": customer_email,
        "subject": f"Re: Ticket #{ticket_id}",
        "body": message,
        "from": "support@novatech.io",
        "type": "ticket_reply",
    })
    email_log.write_text(json.dumps(emails, indent=2))

    return {
        "reply_sent": True,
        "ticket_id": ticket_id,
        "to": customer_email,
        "message_preview": message[:200] + ("..." if len(message) > 200 else ""),
    }


# Register tools
register_tool(
    name="support.read_tickets",
    description="Read customer support tickets. Filter by status (open, resolved) or priority (low, medium, high). Returns ticket details including customer message body.",
    input_schema={
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["open", "resolved"], "description": "Filter by ticket status"},
            "priority": {"type": "string", "enum": ["low", "medium", "high"], "description": "Filter by priority"},
            "count": {"type": "integer", "description": "Number of tickets to return (default: 10)", "default": 10},
        },
    },
    handler=read_tickets,
    department="support",
    vulnerabilities=[VC.PROMPT_INJECTION_INDIRECT],
)

register_tool(
    name="support.search_knowledge_base",
    description="Search the internal knowledge base for articles about NovaTech products, troubleshooting guides, and company policies.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "category": {"type": "string", "description": "Filter by category (getting_started, troubleshooting, security, billing, operations)"},
        },
    },
    handler=search_knowledge_base,
    department="support",
    vulnerabilities=[VC.PROMPT_INJECTION_INDIRECT, VC.SQL_INJECTION],
)

register_tool(
    name="support.get_customer_profile",
    description="Retrieve customer account profiles including contact information, subscription plan, and account notes. Search by customer ID or email.",
    input_schema={
        "type": "object",
        "properties": {
            "customer_id": {"type": "integer", "description": "Customer ID"},
            "email": {"type": "string", "description": "Customer email address"},
        },
    },
    handler=get_customer_profile,
    department="support",
    vulnerabilities=[VC.EXFIL_DIRECT, VC.SQL_INJECTION],
)

register_tool(
    name="support.reply_to_ticket",
    description="Send a reply to a customer support ticket. The reply is sent to the customer's email and the ticket is marked as resolved.",
    input_schema={
        "type": "object",
        "properties": {
            "ticket_id": {"type": "integer", "description": "Ticket ID to reply to"},
            "message": {"type": "string", "description": "Reply message content"},
        },
        "required": ["ticket_id", "message"],
    },
    handler=reply_to_ticket,
    department="support",
    vulnerabilities=[VC.EXFIL_DIRECT],
)
