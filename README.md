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
- [MCP Inspector](#mcp-inspector)
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
git clone https://github.com/Kyze-Labs/damn-vulnerable-MCP-Server
cd damn-vulnerable-MCP-Server

# Install the core MCP server
pip install -e .

# Run the all-in-one MCP server (all 28 tools)
dvmcp --difficulty beginner

# Or run a specific department
dvmcp --department hr --difficulty beginner
```

To use the web dashboard, MCP inspector, and exfiltration listener, install with extras:

```bash
# Install with all optional dependencies
pip install -e ".[all]"

# Start the MCP Inspector (web-based MCP client)
dvmcp-inspector --port 5173

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

# Start the inspector, dashboard, and exfil listener
docker-compose up inspector dashboard exfil-listener
```

| Service | URL | Description |
|---------|-----|-------------|
| `inspector` | http://localhost:5173 | Web-based MCP client for testing and invoking tools |
| `dashboard` | http://localhost:8080 | Web dashboard for browsing challenges and tracking progress |
| `exfil-listener` | http://localhost:9999 | Captures exfiltrated data from challenges |

Available department services: `dvmcp-hr`, `dvmcp-engineering`, `dvmcp-finance`, `dvmcp-it`, `dvmcp-support`, `dvmcp-marketing`.

All services share a `dvmcp-data` volume for the SQLite database and seed data, so cross-department scenarios work out of the box.

> **Note:** The MCP server services (`dvmcp`, `dvmcp-hr`, etc.) communicate over stdio (JSON-RPC), not HTTP. Use `docker-compose run` (not `up`) to interact with them via your MCP client.

---

## MCP Inspector

The MCP Inspector is a **web-based client** for interacting with the DVMCP server directly from your browser. It works like [MCP Inspector](https://github.com/modelcontextprotocol/inspector) — a proxy server spawns the DVMCP server as a subprocess and bridges HTTP requests to stdio JSON-RPC messages.

### Starting the Inspector

```bash
# Local
dvmcp-inspector

# Custom port
dvmcp-inspector --port 5173

# Docker
docker-compose up inspector
```

Then open **http://localhost:5173** in your browser.

### How It Works

```
Browser (HTML/JS)          FastAPI Proxy           DVMCP Server
      |                        |                        |
      |--- fetch /api/... --->|                        |
      |                        |--- stdin (JSON-RPC) -->|
      |                        |<-- stdout (JSON-RPC) --|
      |<-- HTTP JSON ---------|                        |
```

The browser cannot talk to a stdio process directly. The FastAPI proxy server spawns the MCP server as a child process, translates HTTP API calls into JSON-RPC messages written to the server's `stdin`, reads responses from `stdout`, and returns them as HTTP JSON.

### Features

- **Connect/Disconnect** — Spawn the DVMCP server with a chosen difficulty level and optional department filter. The proxy performs the MCP handshake (`initialize` + `notifications/initialized`) automatically.
- **Tool Browser** — Sidebar listing all available tools with search/filter. Tools are color-coded by department (HR, Engineering, Finance, IT Admin, Support, Marketing).
- **Dynamic Forms** — Auto-generates input forms from each tool's `inputSchema`. Supports strings, numbers, booleans, enums, objects, and arrays.
- **Tool Execution** — Call any tool and view the formatted result with success/error status and response duration.
- **JSON-RPC Console** — Send arbitrary raw JSON-RPC requests with a split-pane view (request on the left, response on the right). Useful for testing hidden tools like `it._admin_reset` or crafting custom payloads.
- **Request History** — Full log of every JSON-RPC message exchanged with the server, including requests, notifications, responses, and timing. Click any entry to expand the raw JSON.
- **Server Info** — Displays server name, version, protocol version, capabilities, difficulty, department, and the raw `initialize` response.
- **Copy as JSON-RPC** — Export the current tool call as a raw JSON-RPC 2.0 message for use with other clients.
- **View Schema** — Inspect the full `inputSchema` of any tool.
- **Resizable Sidebar** — Drag the sidebar edge to resize.
- **Toast Notifications** — Non-intrusive success/error/info alerts.

### Using the Inspector for Challenges

1. **Connect** with the desired difficulty (e.g., Beginner).
2. **Browse tools** in the sidebar — each tool shows its department and description.
3. **Select a tool** to see its parameters and schema.
4. **Enter a payload** (e.g., `' OR 1=1 --` for SQL injection in `hr.search_employees`).
5. **Click Execute** and inspect the response.
6. **Switch to JSON-RPC Console** to send raw requests for advanced attacks (e.g., calling hidden tools, chaining requests).
7. **Check History** to review all requests and responses.

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
│   ├── inspector/      # MCP Inspector — web-based MCP client (FastAPI + static HTML/CSS/JS)
│   ├── dashboard/      # Web dashboard for challenge browsing (FastAPI)
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

If ports 5173, 8080, or 9999 are occupied, override them in docker-compose:

```bash
# Use alternative ports
docker-compose run -p 5174:5173 inspector
docker-compose run -p 8081:8080 dashboard
docker-compose run -p 9998:9999 exfil-listener
```

For local installs, use the `--port` flag:

```bash
dvmcp-inspector --port 5174
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
