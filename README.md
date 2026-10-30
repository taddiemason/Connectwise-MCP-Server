# ConnectWise MCP Server

## Overview

A Model Context Protocol (MCP) server giving AI agents read-only access to ConnectWise Manage. One Python process serves two transports:

```
┌──────────────────┐  stdio  ┐
│  Claude Code /   │─────────┤
│  Claude Desktop  │         │   ┌──────────────────┐  HTTPS  ┌────────────────┐
└──────────────────┘         ├──►│   ConnectWise    │────────►│  ConnectWise   │
┌──────────────────┐  HTTP   │   │   MCP Server     │         │   Manage API   │
│    OpenWebUI     │─────────┘   └──────────────────┘         └────────────────┘
└──────────────────┘ :3002
```

- **stdio** — add it to Claude Code or Claude Desktop like any other MCP server.
- **HTTP** — serves OpenWebUI, including a `/v1/tools/execute` route kept for compatibility with tools written against the old Node bridge.

### Changed in 2.0.0

The previous release **did not run**. `requirements.txt` specified `mcp>=1.0.0`; once mcp 2.x shipped it removed the decorator API the server was written against, so a fresh install failed at import with `AttributeError: 'Server' object has no attribute 'list_tools'` and the container could not start.

Fixing that pulled several other things with it:

- **Dependencies are pinned** with upper bounds. The unbounded range was the bug.
- **The Node bridge is gone.** It spawned a fresh Python process per request, invoked `python` in an image that only installed `python3`, and sent `tools/call` without an MCP `initialize` handshake. FastMCP serves HTTP directly, so all of that went with it.
- **One container instead of two.** The old `connectwise-mcp-server` service ran a stdio server with nothing attached to stdin, so it exited and was restarted forever while doing no work.
- **Credentials are no longer needed to import.** The client is built on first use, so the tool list can be inspected and the whole surface tested without keys.
- **There is now a test suite** that runs with no credentials and no network.

All 30 tool names are unchanged, and `/v1/tools/execute` returns the same shape it used to, so existing OpenWebUI installs keep working.

## Key Features

**Company Management:**
- Search companies with advanced filtering
- Retrieve complete company information
- View company contacts and relationships

**Service Tickets:**
- Search tickets using ConnectWise conditions
- Retrieve full ticket details including notes and history
- Filter by status, company, date, and more

**Contact & Sales:**
- Search and retrieve contacts with company associations
- View sales opportunities and pipeline tracking
- Access opportunity details and status

**Agreements & Time Tracking:**
- Search agreements and contracts
- View agreement additions and add-ons
- View detailed time tracking data
- Filter time entries by member, date, or ticket

**Project & Activity Management:**
- Search projects and track progress
- View activities and tasks
- Access team member information

**IT Asset Management:**
- Search and view IT configurations/assets
- Retrieve configuration types for asset categorization
- Access company sites and locations
- Track hardware and software inventory

**Finance & Billing:**
- Search and retrieve invoices
- View expense entries and reports
- Access billing cycles for recurring billing
- Review agreement additions and billing details

**Reference Data:**
- Company types and statuses for categorization
- Ticket priorities and sources
- Contact types for organization
- Service board configurations and statuses

**Service Desk Enhancements:**
- View service boards and workflows
- Access board-specific statuses
- Retrieve ticket tasks and checklists
- View scheduled work for tickets

**AI Integration:**
- Natural language command support in OpenWebUI
- Read-only access to all ConnectWise data
- Advanced filtering and search capabilities

## Prerequisites

- Docker and Docker Compose installed
- ConnectWise Manage API credentials (Company ID, Public Key, Private Key)
- OpenWebUI running (any version with Tools support)

## Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/taddiemason/Connectwise-MCP-Server
cd ConnectWise-MCP-Server
```

### 2. Obtain ConnectWise Credentials

To get your ConnectWise API credentials:

1. Log in to your ConnectWise Manage instance
2. Navigate to **System → Members**
3. Create a new API Member or use existing credentials
4. Generate API Keys:
   - Go to **My Account → API Keys**
   - Click **New** to create new API keys
   - Save the **Public Key** and **Private Key**
5. Your **Company ID** is typically shown in the URL or system settings

**Important:** For read-only access, ensure the API member only has read permissions in ConnectWise.

### 3. Configure Credentials

Create a `.env` file from the example:
```bash
cp .env.example .env
```

Edit `.env` and add your ConnectWise credentials:
```bash
# ConnectWise API Credentials (required)
CW_COMPANY_ID=your_company_id_here
CW_PUBLIC_KEY=your_public_key_here
CW_PRIVATE_KEY=your_private_key_here

# ConnectWise API Configuration
CW_API_URL=https://api-na.myconnectwise.net
CW_API_VERSION=v2023.2
CW_CLIENT_ID=mcp-connectwise-server

# MCP Bridge Server Port (default: 3002)
MCP_PORT=3002

# Log level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO
```

**API URL Configuration:**
- North America: `https://api-na.myconnectwise.net`
- Europe: `https://api-eu.myconnectwise.net`
- Australia: `https://api-au.myconnectwise.net`
- On-premise: Use your server URL

### 4. Start Services

**Using the setup script (recommended):**
```bash
chmod +x setup.sh
./setup.sh
```
Select option 1 to start the server.

**Or manually with Docker Compose:**
```bash
docker-compose up -d --build
```

Bridge available at: **http://localhost:3002**

### 5a. Use it from Claude Code or Claude Desktop

No Docker needed — stdio is the default transport. Install into a venv so the
interpreter you point at definitely has the dependencies:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt    # .venv\Scripts\python.exe on Windows
```

**Claude Code**, one command:

```bash
claude mcp add connectwise \
  -e CW_COMPANY_ID=your_company_id \
  -e CW_PUBLIC_KEY=your_public_key \
  -e CW_PRIVATE_KEY=your_private_key \
  -- /absolute/path/to/.venv/bin/python /absolute/path/to/connectwise_mcp.py
```

Check it took:

```bash
claude mcp list        # connectwise: ... - ✔ Connected
```

**Claude Desktop**, or Claude Code via file: copy `.mcp.json.example` to
`.mcp.json` and fill it in. Claude Desktop takes the same `mcpServers` block in
`claude_desktop_config.json`.

Two things that bite:

- **Use absolute paths, and point `command` at the venv's Python.** The MCP
  client does not inherit your shell, your `PATH` or your activated venv. A bare
  `python` will often be a different interpreter without `fastmcp` installed.
- **That config file holds live API keys in plaintext** — the same keys that
  read every client's tickets, contacts and agreements. `.mcp.json` and
  `claude_desktop_config.json` are both gitignored here for that reason. Commit
  the `.example`, never the real one.

Credentials are only needed to *call* a tool. The server starts and lists its 30
tools without them, and an uncredentialled call fails with a message naming the
variables that are missing rather than a stack trace.

### 5b. Add Tool to OpenWebUI

1. Open OpenWebUI in your browser
2. Navigate to **Settings → Admin Panel → Tools**
3. Click **"+ Create New Tool"**
4. Copy the contents of `connectwise_tools.py` from this repository
5. Paste into the tool editor
6. Configure the bridge URL in the Valves section:
   - Docker: `http://connectwise-mcp-bridge:3002`
   - Local: `http://localhost:3002`
7. Click **"Save"**
8. Enable the ConnectWise Tools

### 6. Verify Installation
```bash
curl http://localhost:3002/health
```

Expected response:
```json
{
  "status": "ok",
  "service": "connectwise-mcp-bridge"
}
```

## Available Tools in OpenWebUI

**Company Tools:**
- `get_companies()` - Search companies with advanced filtering
- `get_company()` - Get specific company details
- `get_company_sites()` - Get sites/locations for a specific company
- `get_company_types()` - Get all company types for categorization
- `get_company_statuses()` - Get all company statuses

**Ticket Tools:**
- `get_tickets()` - Search tickets with conditions
- `get_ticket()` - Get specific ticket details
- `get_ticket_notes()` - Retrieve ticket notes and history
- `get_ticket_tasks()` - Get tasks/checklist items for a ticket
- `get_ticket_schedules()` - Get scheduled work for a ticket
- `get_ticket_priorities()` - Get all ticket priorities
- `get_ticket_sources()` - Get all ticket sources

**Contact Tools:**
- `get_contacts()` - Search contacts
- `get_contact()` - Get specific contact details
- `get_contact_types()` - Get all contact types

**Sales Tools:**
- `get_opportunities()` - Search sales opportunities

**Agreement Tools:**
- `get_agreements()` - Search agreements and contracts
- `get_agreement_additions()` - Get add-ons for a specific agreement

**Time Entry Tools:**
- `get_time_entries()` - Search time tracking data

**Project Tools:**
- `get_projects()` - Search projects

**Activity Tools:**
- `get_activities()` - Search activities and tasks

**Member Tools:**
- `get_members()` - Search team members

**IT Asset Management Tools:**
- `get_configurations()` - Search IT configurations/assets
- `get_configuration()` - Get specific configuration by ID
- `get_configuration_types()` - Get all configuration types

**Finance & Billing Tools:**
- `get_invoices()` - Search and retrieve invoices
- `get_expense_entries()` - Search expense entries
- `get_billing_cycles()` - Get all billing cycles

**Service Desk Tools:**
- `get_service_boards()` - Get all service boards
- `get_board_statuses()` - Get statuses for a specific board

Collection tools take `conditions`, `orderBy`, `page`, `pageSize` and `fetchAll`. See [Reliability](#reliability) for what `fetchAll` is for.

## Usage Examples

In OpenWebUI, communicate naturally:

**General Queries:**
- "Show me all open tickets for ACME Corp"
- "Find all companies with 'Tech' in their name"
- "Get details for ticket #12345"
- "List all opportunities with status 'Open'"
- "Show me time entries for this week"
- "Find contacts at Microsoft"
- "What projects are currently active?"
- "Show me all agreements expiring this month"

**IT Asset Management:**
- "Show me all servers for ACME Corp"
- "What configurations are assigned to ticket #5678?"
- "List all company sites for XYZ Corporation"
- "What configuration types do we have?"

**Finance & Billing:**
- "Show me all open invoices for this month"
- "What are the expense entries for John this week?"
- "List all billing cycles"
- "What add-ons are included in agreement #123?"

**Service Desk:**
- "What service boards do we have?"
- "Show me all statuses for the Help Desk board"
- "What tasks are on ticket #9999?"
- "Show scheduled work for ticket #1234"

**Reference Data:**
- "What company types are available?"
- "List all ticket priorities"
- "Show me all contact types"
- "What ticket sources do we track?"

The AI will automatically call the appropriate ConnectWise tool functions to complete your request.

## ConnectWise API Conditions

ConnectWise uses a powerful condition syntax for filtering:

```
# String equality
identifier="ACME"

# Contains (like)
name like "%Corp%"

# Date comparisons
dateEntered > [2024-01-01]

# Numeric comparisons
id > 1000

# Multiple conditions
status/name="New" and company/identifier="ACME"

# Nested fields
company/name like "%Tech%"
```

## File Structure

```
ConnectWise-MCP-Server/
├── connectwise_mcp.py          (the whole server: tools, both transports)
├── connectwise_tools.py        (OpenWebUI tool)
├── test_connectwise_mcp.py     (offline test suite)
├── conftest.py                 (mock ConnectWise fixtures)
├── pytest.ini
├── docker-compose.yml          (one service)
├── Dockerfile
├── requirements.txt            (pinned)
├── requirements-dev.txt        (test only)
├── .env.example
├── Setup.sh                    (management script)
├── test.sh                     (live deployment smoke check)
└── README.md
```

## Management Commands

**Using setup script:**
```bash
./setup.sh
```

Options:
1. Start ConnectWise MCP Server
2. Stop ConnectWise MCP Server
3. Restart ConnectWise MCP Server
4. View logs
5. Check status
6. Update server
7. Clean up
8. Exit

**Direct Docker commands:**
```bash
# Start servers
docker-compose up -d --build

# View logs
docker-compose logs -f

# View bridge logs only
docker-compose logs -f mcp-bridge

# View MCP server logs only
docker-compose logs -f connectwise-mcp-server

# Stop servers
docker-compose down

# Restart servers
docker-compose restart

# Check status
docker-compose ps
```

## Troubleshooting

**Authentication Errors:**
- Verify your Company ID, Public Key, and Private Key are correct
- Ensure the API member has appropriate permissions
- Check that the API URL matches your ConnectWise instance
- Generate new API keys if needed

**Port Conflicts:**

If port 3002 is already in use:
1. Edit `.env` file: `MCP_PORT=3003`
2. Edit `docker-compose.yml`: Update port mapping to `3003:3002` and environment `PORT=3003`
3. Restart: `docker-compose down && docker-compose up -d --build`
4. Update bridge URL in OpenWebUI Tool Valves

**Bridge Connection Issues:**
- Verify bridge is running: `docker-compose ps`
- Check bridge logs: `docker-compose logs mcp-bridge`
- Test health endpoint: `curl http://localhost:3002/health`
- Verify bridge URL in OpenWebUI Tool Valves settings:
  - Both in Docker: `http://connectwise-mcp-bridge:3002`
  - OpenWebUI local: `http://localhost:3002`

**OpenWebUI Can't Connect:**
- Ensure `connectwise_tools.py` is saved in OpenWebUI Tools
- Enable the ConnectWise Tools in OpenWebUI Settings
- Verify the bridge URL is correct in Valves settings
- Check Docker networks: `docker network connect openwebui_network connectwise-mcp-bridge`

**Rate Limiting:**

ConnectWise has API rate limits. If you encounter rate limiting:
- Reduce the `pageSize` parameter
- Add delays between requests
- Check ConnectWise API documentation for current limits

## Security

### The HTTP transport requires a bearer token

`MCP_AUTH_TOKEN` is mandatory — **the server refuses to start on HTTP without it** rather than coming up wide open. Generate one:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Callers send it on every request:

```bash
curl -X POST http://localhost:3002/v1/tools/execute \
  -H "Authorization: Bearer $MCP_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "connectwise_get_companies", "arguments": {"pageSize": 5}}'
```

In OpenWebUI, add the same header in the tool's Valves.

`/health` stays unauthenticated so the container healthcheck works; it returns a fixed status string and nothing about your instance. Tokens are compared with `hmac.compare_digest`, so a wrong one cannot be narrowed down by timing.

**The stdio transport has no token** and does not need one — the trust boundary there is the process, not the network.

> Before this, port 3002 answered anyone who could reach it with your entire ConnectWise instance: every client's tickets, contacts, agreements and invoices, no credential required. If you have been running the previous version on a reachable interface, treat that as exposure and rotate the ConnectWise API keys.

### The rest

- Never commit `.env`, `.mcp.json` or `claude_desktop_config.json` — all three hold live API keys and all three are gitignored
- Use an API-only member with the minimum required permissions
- **Read-only:** no write operations are implemented; every tool issues `GET`, and a test enforces it
- Rotate API credentials regularly
- Restrict IP access to the ConnectWise API where you can
- Keep the HTTP port on a private network even with the token
- Errors never echo the API key, and that is tested

## Reliability

**Retries.** ConnectWise rate-limits. A 429 or a 5xx is retried `CW_MAX_RETRIES` times (default 3) with exponential backoff, honouring `Retry-After` when ConnectWise sends it. Client errors — 400, 401, 403, 404 — are *not* retried, because repeating them only burns the rate limit. Without this a 429 surfaced as a failed tool call, which reads to a model as "that data does not exist" rather than "ask again shortly".

**Pagination.** Collection tools take `fetchAll`:

```
get_tickets(conditions='status/name="New"', fetchAll=True)
```

Off by default, a query matching 400 tickets returns the first 25 and says nothing about the rest — and "25" is a wrong answer rather than a partial one. `fetchAll` walks every page, capped at `CW_MAX_RECORDS` (default 1000) so "every ticket" cannot become fifty thousand records and a rate-limit ban. The result is still a bare array either way.

**Error messages** name the endpoint, the status, and what to do:

```
ConnectWise service/tickets [401]: authentication was rejected. Check
CW_PUBLIC_KEY and CW_PRIVATE_KEY, that CW_COMPANY_ID matches the instance,
and that the API member has read rights to this area. Body: ...
```

## Development & Testing

**Tests** — no credentials, no network, no Docker. A `httpx.MockTransport` stands in for ConnectWise:

```bash
pip install -r requirements-dev.txt
pytest
```

They cover the endpoint and query string each tool produces, the auth headers, error paths (400/401/404/429/500, malformed JSON), that errors never echo the private key, that every tool issues `GET` and nothing else, and that the module imports with no credentials set — the failure that prompted the 2.0.0 rewrite.

**Running it locally:**

```bash
pip install -r requirements.txt
export CW_COMPANY_ID=your_company_id
export CW_PUBLIC_KEY=your_public_key
export CW_PRIVATE_KEY=your_private_key

python connectwise_mcp.py                    # stdio, for MCP clients
MCP_TRANSPORT=http python connectwise_mcp.py # HTTP on :3002, for OpenWebUI
```

**Testing API Endpoints:**

Health check:
```bash
curl http://localhost:3002/health
```

Test search:
```bash
curl -X POST http://localhost:3002/v1/tools/execute \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "connectwise_get_companies",
    "arguments": {
      "conditions": "identifier=\"ACME\"",
      "pageSize": 5
    }
  }'
```

## Dependencies

- `fastmcp` — MCP server framework; brings `mcp`, `starlette` and `uvicorn` with it
- `httpx` — async HTTP client

Both are pinned with upper bounds in `requirements.txt`. That is deliberate: an unbounded `mcp>=1.0.0` is exactly what broke the previous release when a major version shipped. Test-only dependencies live in `requirements-dev.txt`.

No Node.js. The bridge that needed it is gone.

## Resources

- [ConnectWise Developer Network](https://developer.connectwise.com/)
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
- [OpenWebUI](https://openwebui.com/)
- [ConnectWise REST API Documentation](https://developer.connectwise.com/Products/Manage/REST)

## Important Notes

- This server provides **READ-ONLY** access to ConnectWise
- No write operations are implemented
- Designed for AI-assisted data retrieval and analysis
- Respects ConnectWise API rate limits
- Requires valid ConnectWise API credentials

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check existing documentation
- Review ConnectWise API documentation
- Check OpenWebUI documentation

## License

MIT License - See LICENSE file for details

## Version

**Current Version:** 2.1.0

### Changelog

**Version 2.1.0 (Hardening)**
- **The HTTP transport now requires a bearer token** and refuses to start without one. It previously served the entire ConnectWise instance to anyone who could reach the port
- Retries 429 and 5xx with exponential backoff, honouring `Retry-After`; client errors are not retried
- Added `fetchAll` to collection tools, capped by `CW_MAX_RECORDS`, so a large result set cannot be silently truncated to page one
- Error messages name the endpoint, the status and the likely fix
- 81 tests

**Version 2.0.0 (Runs again)**
- Fixed the server failing at import: `mcp>=1.0.0` resolved to 2.x, which removed the decorator API it was built on
- Pinned all dependencies with upper bounds
- Ported to FastMCP: tool schemas come from type hints, deleting ~740 lines of hand-written JSON schema and a ~190-line dispatcher
- Removed the Node bridge — HTTP is served in-process, so no spawn per request, no `python`/`python3` mismatch, no missing MCP handshake
- Collapsed two containers into one; the second never did anything but restart
- Added stdio transport, so it works in Claude Code and Claude Desktop
- Credentials are no longer required at import time
- Added an offline test suite (51 tests, no credentials, no network)
- All 30 tool names and the `/v1/tools/execute` response shape are unchanged

**Version 1.1.0 (Enhanced Feature Set)**
- Added IT Asset Management (configurations, configuration types, company sites)
- Added Finance & Billing (invoices, expense entries, billing cycles, agreement additions)
- Added Reference Data endpoints (company types/statuses, ticket priorities/sources, contact types)
- Added Service Desk Enhancements (service boards, board statuses, ticket tasks, ticket schedules)
- Total of 18 new read-only tools
- Enhanced documentation with new usage examples

**Version 1.0.0 (Initial Release)**
- Read-only access to ConnectWise Manage
- Support for companies, tickets, contacts, opportunities, agreements
- Time entries, projects, activities, and members
- Docker-based deployment
- OpenWebUI integration
- MCP bridge architecture
- Comprehensive documentation
