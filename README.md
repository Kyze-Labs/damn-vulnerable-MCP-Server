# DVMCP — Damn Vulnerable MCP

![Version](https://img.shields.io/badge/version-2.0.0-blue)
![Python](https://img.shields.io/badge/python-3.11%2B-green)
![License](https://img.shields.io/badge/license-MIT-orange)

> **An intentionally vulnerable Model Context Protocol server for security training.**
> Think [DVWA](https://github.com/digininja/DVWA) but for MCP/AI agent security.

DVMCP is a self-contained training platform for learning how to attack and defend AI agents that use the Model Context Protocol. It simulates a fictional company (**NovaTech Solutions**) with 6 departments, 28 vulnerable tools, and 38 challenges across 4 difficulty levels.

**WARNING: This is intentionally vulnerable software. Do NOT deploy in production. All data is fake.**

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
  - [Local Installation](#local-installation)
  - [Docker](#docker)
- [MCP Host Configuration](#mcp-host-configuration)
- [Architecture](#architecture)
- [Vulnerability Categories](#vulnerability-categories-19)
- [Challenges](#challenges-38)
- [Difficulty Levels](#difficulty-levels)
- [Fake Data](#fake-data)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)
- [Disclaimer](#disclaimer)

---

## Prerequisites

- **Python 3.11+**
- **pip** (included with Python)
- **Docker & Docker Compose** (optional, for containerized setup)

---

## Quick Start

### Local Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/dvmcp-v2.git
cd dvmcp-v2

# Install the core MCP server
pip install -e .

# Run the all-in-one MCP server (all 28 tools)
dvmcp --difficulty beginner

# Or run a specific department
dvmcp --department hr --difficulty beginner
```

To use the web dashboard and exfiltration listener, install with extras:

```bash
# Install with dashboard + exfil listener dependencies
pip install -e ".[all]"

# Start the exfil listener (captures stolen data)
dvmcp-exfil --port 9999

# Start the web dashboard (challenge browser)
dvmcp-dashboard --port 8080
```

### Docker

Build and run all services:

```bash
# Build all images
docker-compose build

# Run the all-in-one MCP server
docker-compose run --rm dvmcp

# Run a specific department server
docker-compose run --rm dvmcp-hr

# Start the dashboard and exfil listener
docker-compose up dashboard exfil-listener
```

| Service | URL | Description |
|---------|-----|-------------|
| `dashboard` | http://localhost:8080 | Web dashboard for browsing challenges and tracking progress |
| `exfil-listener` | http://localhost:9999 | Captures exfiltrated data from challenges |

Available department services: `dvmcp-hr`, `dvmcp-engineering`, `dvmcp-finance`, `dvmcp-it`, `dvmcp-support`, `dvmcp-marketing`.

All services share a `dvmcp-data` volume for the SQLite database and seed data, so cross-department scenarios work out of the box.

> **Note:** The MCP server services (`dvmcp`, `dvmcp-hr`, etc.) communicate over stdio (JSON-RPC), not HTTP. Use `docker-compose run` (not `up`) to interact with them via your MCP client.

---

## MCP Host Configuration

Add to your MCP client config (Claude Desktop, Cursor, etc.):

```json
{
  "mcpServers": {
    "novatech": {
      "command": "dvmcp",
      "args": ["--difficulty", "beginner"]
    }
  }
}
```

For Docker-based setups, point the command to `docker-compose run`:

```json
{
  "mcpServers": {
    "novatech": {
      "command": "docker-compose",
      "args": ["-f", "/path/to/dvmcp-v2/docker-compose.yml", "run", "--rm", "-T", "dvmcp"]
    }
  }
}
```

For cross-origin scenarios, configure each department as a separate server:

```json
{
  "mcpServers": {
    "novatech-hr": {
      "command": "dvmcp",
      "args": ["--department", "hr"]
    },
    "novatech-engineering": {
      "command": "dvmcp",
      "args": ["--department", "engineering"]
    },
    "novatech-finance": {
      "command": "dvmcp",
      "args": ["--department", "finance"]
    },
    "novatech-it": {
      "command": "dvmcp",
      "args": ["--department", "it_admin"]
    },
    "novatech-support": {
      "command": "dvmcp",
      "args": ["--department", "support"]
    },
    "novatech-marketing": {
      "command": "dvmcp",
      "args": ["--department", "marketing"]
    }
  }
}
```

---

## Architecture

```
NovaTech Solutions (Fictional Company)
├── HR Department (5 tools)
│   └── search_employees, run_payroll_report, review_candidate, update_employee, generate_offer_letter
├── Engineering (5 tools)
│   └── query_repos, trigger_deployment, run_ci_pipeline, read_source_file, manage_infrastructure
├── Finance (5 tools)
│   └── query_invoices, process_payment, submit_expense, export_financial_data, wire_transfer
├── IT/Admin (5 tools + 1 hidden)
│   └── manage_users, query_audit_log, get_system_config, execute_admin_command, manage_api_tokens, [_admin_reset]
├── Customer Support (4 tools)
│   └── read_tickets, search_knowledge_base, get_customer_profile, reply_to_ticket
└── Marketing (4 tools)
    └── manage_campaigns, send_campaign_email, query_analytics, manage_social_accounts
```

**Shared SQLite database** — all departments read/write the same `novatech.db` (no schema isolation = cross-table SQL injection).

---

## Vulnerability Categories (19)

| ID | Category | Description |
|----|----------|-------------|
| V01 | Prompt Injection (Direct) | Payload in tool parameters |
| V02 | Prompt Injection (Indirect) | Poisoned content in tool results |
| V03 | Tool Poisoning | Malicious tool descriptions |
| V04 | Rug Pull / TOCTOU | Tool behavior changes after initial trust |
| V05 | Cross-Origin Tool Abuse | Cross-department data access |
| V06 | Privilege Escalation (Vertical) | User → Admin |
| V07 | Privilege Escalation (Horizontal) | Access other users' data |
| V08 | Data Exfiltration (Direct) | Plaintext to external endpoint |
| V09 | Data Exfiltration (Encoded) | Base64/hex encoding |
| V10 | Data Exfiltration (Side Channel) | DNS, timing, steganography |
| V11 | Confused Deputy | Agent tricked via tool chains |
| V12 | SQL Injection | Unsanitized SQL |
| V13 | Command Injection | Shell metacharacters |
| V14 | Path Traversal | File access outside directory |
| V15 | Supply Chain | Compromised CI/CD |
| V16 | Denial of Service | Resource exhaustion |
| V17 | Shadow Tool Invocation | Hidden tools not in tools/list |
| V18 | Parameter Injection | Params escape context |
| V19 | Consent Phishing | Hidden tool side effects |

---

## Challenges (38)

### Beginner (10) — Single-tool, obvious payloads — 50 pts each
| ID | Name | Category |
|----|------|----------|
| C01 | The Open Door | SQL Injection |
| C02 | Shell Shock | Command Injection |
| C03 | Credential Harvest | Path Traversal |
| C04 | The Email Cannon | Direct Exfil |
| C05 | DROP It Like It's Hot | SQL Injection |
| C06 | Admin for a Day | Vertical Privesc |
| C07 | The Key Vault | Data Exfil |
| C08 | Pipe Dream | Shell Pipes + Exfil |
| C09 | Negative Balance | Parameter Injection |
| C10 | Token Grab | Privesc |

### Intermediate (10) — Two-tool chains, encoded payloads — 100 pts each
| ID | Name | Category |
|----|------|----------|
| C11 | The Poisoned Inbox | Indirect Prompt Injection |
| C12 | Resume Bomb | Indirect Prompt Injection |
| C13 | Base64 Smuggling | Encoded Exfiltration |
| C14 | The Wire | Cross-Origin Abuse |
| C15 | Audit Log Inception | SQL Injection (UNION) |
| C16 | Deploy Key Heist | Path Traversal + Exfil |
| C17 | Knowledge Poisoning | Indirect Prompt Injection |
| C18 | Social Engineering | Data Exfil Chain |
| C19 | The Expense Fraud | Horizontal Privesc |
| C20 | Config Overwrite | Code Execution via CI |

### Advanced (10) — Multi-step cross-department chains — 200 pts each
| ID | Name | Category |
|----|------|----------|
| C21 | The Long Con | Confused Deputy (3-step) |
| C22 | Insider Threat | Cross-Origin Chain |
| C23 | The Backdoor | Persistence |
| C24 | DNS Tunnel | Side-Channel Exfil |
| C25 | The Phantom Tool | Shadow Tool |
| C26 | Supply Chain Attack | CI/CD Compromise |
| C27 | The Slow Drip | Low-and-Slow Exfil |
| C28 | Model Manipulation | Context Poisoning |
| C29 | The Rug Pull | TOCTOU |
| C30 | Cross-Origin Pivot | Full Chain (4+ depts) |

### Expert (8) — Side channels, steganography, model manipulation — 300-500 pts each
| ID | Name | Category |
|----|------|----------|
| C31 | Timing Oracle | Timing Side-Channel |
| C32 | Steganographic Exfil | Whitespace Encoding |
| C33 | The Consent Trap | Consent Phishing |
| C34 | Tool Description Poisoning | Tool Poisoning |
| C35 | The Infinite Loop | Denial of Service |
| C36 | Unicode Smuggling | Zero-Width Char Encoding |
| C37 | The Dead Drop | Two-Stage Injection |
| C38 | The Full Breach | Capstone (Full Kill Chain) |

---

## Difficulty Levels

Difficulty is **mechanical**, not just a label. It changes tool behavior:

| Level | Behavior |
|-------|----------|
| **Beginner** | Zero sanitization. Raw SQL. No path validation. Full stack traces. All hints. |
| **Intermediate** | Blocks DROP/DELETE. Partial field redaction. Logs external sends. Hints on demand. |
| **Advanced** | Parameterized queries (UNION bypass works). Rate limits. Command blocklist. First hint only. |
| **Expert** | WAF-like rules (encoding bypass). Simulated approval delays. No hints. |

---

## Fake Data

All data is obviously fake and safe for training:
- **25 employees** with SSNs starting `000-` (invalid prefix)
- **Credit cards** use test numbers (4111-1111-1111-1111)
- **API keys** use formats like `AKIAIOSFODNN7EXAMPLE`
- **Passwords** are clearly fake hashes
- **Company** "NovaTech Solutions" is fictional

---

## Project Structure

```
dvmcp-v2/
├── src/dvmcp/
│   ├── core/           # Server, registry, difficulty engine, verification
│   ├── departments/    # hr, engineering, finance, it_admin, support, marketing
│   ├── challenges/     # beginner, intermediate, advanced, expert
│   ├── data/           # Seed data, planted secrets, poisoned content
│   ├── dashboard/      # Web dashboard (FastAPI)
│   └── exfil_listener/ # Exfiltration capture server
├── tests/              # Test suite
├── docs/               # Documentation
├── docker-compose.yml  # Multi-service Docker config
├── Dockerfile          # Container image definition
└── pyproject.toml      # Project metadata and dependencies
```

---

## Troubleshooting

### Docker daemon not running

```
Cannot connect to the Docker daemon. Is the docker daemon running?
```

Start Docker Desktop (macOS/Windows) or the Docker service (Linux):

```bash
# macOS
open -a Docker

# Linux
sudo systemctl start docker
```

### Port already in use

If ports 8080 or 9999 are occupied, override them in docker-compose:

```bash
# Use alternative ports
docker-compose run -p 8081:8080 dashboard
docker-compose run -p 9998:9999 exfil-listener
```

### MCP server produces no visible output

This is expected. The MCP server uses stdio (JSON-RPC over stdin/stdout), not HTTP. It only responds when an MCP client sends it a request. Connect it to an MCP client like Claude Desktop or Cursor instead of running it in a terminal directly.

### Database reset

The SQLite database is seeded on first run. To reset it:

```bash
# Local
rm src/dvmcp/data/novatech.db
dvmcp --difficulty beginner  # re-seeds on start

# Docker
docker-compose down -v  # removes the dvmcp-data volume
docker-compose up       # re-creates and seeds
```

---

## Contributing

PRs welcome! Ideas for new challenges, vulnerability categories, or tools are especially appreciated.

## License

MIT — This is educational software. Use responsibly.

## Disclaimer

DVMCP is designed exclusively for security education and authorized testing. Do not use these techniques against systems you don't own or have explicit permission to test.
