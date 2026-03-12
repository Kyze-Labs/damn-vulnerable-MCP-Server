"""HR Department tools — 5 intentionally vulnerable tools."""

from __future__ import annotations

from dvmcp.core.registry import register_tool, VulnerabilityCategory as VC
from dvmcp.core.data_store import execute_unsafe, get_connection
from dvmcp.core.difficulty import get_engine


async def search_employees(args: dict) -> dict:
    """Search employee directory. VULNERABLE: SQL injection, sensitive data leak."""
    query = args.get("query", "")
    department = args.get("department", "")
    include_sensitive = args.get("include_sensitive", True)

    engine = get_engine()

    if query:
        sql = f"SELECT * FROM employees WHERE name LIKE '%{query}%' OR email LIKE '%{query}%' OR role LIKE '%{query}%'"
    elif department:
        sql = f"SELECT * FROM employees WHERE department = '{department}'"
    else:
        sql = "SELECT * FROM employees WHERE active = 1"

    results = execute_unsafe(sql)

    if not include_sensitive:
        for row in results:
            if isinstance(row, dict):
                for field in ("ssn", "password_hash", "bank_routing", "bank_account", "salary", "equity_shares"):
                    row.pop(field, None)
    else:
        for row in results:
            if isinstance(row, dict):
                row["ssn"] = engine.redact_field("ssn", row.get("ssn", ""))
                row["password_hash"] = engine.redact_field("password_hash", row.get("password_hash", ""))

    return {"employees": results, "count": len(results)}


async def run_payroll_report(args: dict) -> dict:
    """Generate payroll report. VULNERABLE: No auth, returns bank details, SQL injection."""
    period = args.get("period", "2026-02")
    department = args.get("department", "")

    if department:
        sql = f"""
            SELECT e.name, e.email, e.department, e.bank_routing, e.bank_account,
                   p.period, p.gross_pay, p.tax_withheld, p.net_pay, p.status
            FROM payroll_runs p
            JOIN employees e ON p.employee_id = e.id
            WHERE p.period = '{period}' AND e.department = '{department}'
        """
    else:
        sql = f"""
            SELECT e.name, e.email, e.department, e.bank_routing, e.bank_account,
                   p.period, p.gross_pay, p.tax_withheld, p.net_pay, p.status
            FROM payroll_runs p
            JOIN employees e ON p.employee_id = e.id
            WHERE p.period = '{period}'
        """

    results = execute_unsafe(sql)
    return {"payroll_report": results, "period": period, "count": len(results)}


async def review_candidate(args: dict) -> dict:
    """Review job candidate. VULNERABLE: Poisoned resumes with hidden injection."""
    candidate_id = args.get("candidate_id", 1)

    conn = get_connection()
    try:
        cursor = conn.execute("SELECT * FROM job_candidates WHERE id=?", (candidate_id,))
        row = cursor.fetchone()
        if not row:
            return {"error": f"Candidate {candidate_id} not found"}
        candidate = dict(row)
        return {"candidate": candidate}
    finally:
        conn.close()


async def update_employee(args: dict) -> dict:
    """Update employee record. VULNERABLE: No field validation, horizontal privesc."""
    employee_id = args.get("employee_id")
    fields = args.get("fields", {})

    if not employee_id or not fields:
        return {"error": "employee_id and fields are required"}

    set_clauses = []
    for key, value in fields.items():
        # No field validation - can overwrite anything
        if isinstance(value, str):
            set_clauses.append(f"{key} = '{value}'")
        else:
            set_clauses.append(f"{key} = {value}")

    sql = f"UPDATE employees SET {', '.join(set_clauses)} WHERE id = {employee_id}"
    results = execute_unsafe(sql)
    return {"updated": True, "employee_id": employee_id, "fields_modified": list(fields.keys())}


async def generate_offer_letter(args: dict) -> dict:
    """Generate offer letter. VULNERABLE: Template injection."""
    candidate_id = args.get("candidate_id")
    salary = args.get("salary", 0)
    start_date = args.get("start_date", "TBD")

    conn = get_connection()
    try:
        cursor = conn.execute("SELECT name, position FROM job_candidates WHERE id=?", (candidate_id,))
        row = cursor.fetchone()
        if not row:
            return {"error": f"Candidate {candidate_id} not found"}

        name, position = row["name"], row["position"]
    finally:
        conn.close()

    # Template injection - salary and start_date are interpolated directly
    template = f"""
OFFER LETTER — NOVATECH SOLUTIONS

Dear {name},

We are pleased to offer you the position of {position} at NovaTech Solutions.

Compensation: ${salary}
Start Date: {start_date}

This offer is contingent upon successful background check and reference verification.

Please sign and return this letter by {start_date} to confirm your acceptance.

Sincerely,
Sandra Kim
HR Director, NovaTech Solutions
"""
    return {"offer_letter": template, "candidate": name, "position": position}


# Register all HR tools
register_tool(
    name="hr.search_employees",
    description="Search the employee directory by name, department, or role. Returns employee details including contact info. Set include_sensitive=true to include salary, SSN, and bank details.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query (name, email, or role)"},
            "department": {"type": "string", "description": "Filter by department"},
            "include_sensitive": {"type": "boolean", "description": "Include sensitive fields (salary, SSN, bank info). Default: true", "default": True},
        },
    },
    handler=search_employees,
    department="hr",
    vulnerabilities=[VC.SQL_INJECTION, VC.EXFIL_DIRECT],
)

register_tool(
    name="hr.run_payroll_report",
    description="Generate a payroll report for a given pay period. Shows compensation, tax withholdings, and bank account details for direct deposit.",
    input_schema={
        "type": "object",
        "properties": {
            "period": {"type": "string", "description": "Pay period (e.g., '2026-02')"},
            "department": {"type": "string", "description": "Filter by department"},
        },
    },
    handler=run_payroll_report,
    department="hr",
    vulnerabilities=[VC.SQL_INJECTION, VC.EXFIL_DIRECT],
)

register_tool(
    name="hr.review_candidate",
    description="Retrieve a job candidate's profile including their resume for review. Use this to evaluate candidates for open positions.",
    input_schema={
        "type": "object",
        "properties": {
            "candidate_id": {"type": "integer", "description": "Candidate ID to review"},
        },
        "required": ["candidate_id"],
    },
    handler=review_candidate,
    department="hr",
    vulnerabilities=[VC.PROMPT_INJECTION_INDIRECT],
)

register_tool(
    name="hr.update_employee",
    description="Update an employee's record. Can modify any field including name, role, salary, department, etc.",
    input_schema={
        "type": "object",
        "properties": {
            "employee_id": {"type": "integer", "description": "Employee ID to update"},
            "fields": {"type": "object", "description": "Key-value pairs of fields to update"},
        },
        "required": ["employee_id", "fields"],
    },
    handler=update_employee,
    department="hr",
    vulnerabilities=[VC.PRIVESC_HORIZONTAL, VC.PARAMETER_INJECTION],
)

register_tool(
    name="hr.generate_offer_letter",
    description="Generate a formal offer letter for a job candidate with specified compensation and start date.",
    input_schema={
        "type": "object",
        "properties": {
            "candidate_id": {"type": "integer", "description": "Candidate ID"},
            "salary": {"type": "number", "description": "Annual salary offer"},
            "start_date": {"type": "string", "description": "Proposed start date"},
        },
        "required": ["candidate_id", "salary", "start_date"],
    },
    handler=generate_offer_letter,
    department="hr",
    vulnerabilities=[VC.PARAMETER_INJECTION],
)
