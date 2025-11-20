# ConnectWise MCP Server

## Overview

The ConnectWise MCP Server is a Docker-based Model Context Protocol (MCP) bridge that enables AI agents to access ConnectWise Manage data through natural language commands. It provides read-only access to your ConnectWise instance, allowing AI-assisted data retrieval and analysis through OpenWebUI.

The server consists of two components:

1. **MCP Server** - Python-based ConnectWise Manage API interface
2. **MCP Bridge** - Node.js Express server exposing an HTTP API for OpenWebUI

```
┌─────────────────┐     ┌──────────────────┐      ┌─────────────────┐      ┌────────────────┐
│   OpenWebUI     │◄───►│   MCP Bridge     │◄───► │ ConnectWise     │◄────►│ ConnectWise    │
│     Tools       │ HTTP│   (Port 3002)    │Docker│  MCP Server     │HTTPS │   Manage API   │
└─────────────────┘     └──────────────────┘      └─────────────────┘      └────────────────┘
```

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

### 5. Add Tool to OpenWebUI

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

All tools support pagination and ConnectWise condition syntax for advanced filtering.

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
├── connectwise_mcp.py      (MCP server implementation)
├── bridge-server.js        (HTTP API bridge)
├── connectwise_tools.py    (OpenWebUI tool)
├── docker-compose.yml      (Multi-container setup)
├── Dockerfile              (MCP server container)
├── Dockerfile.bridge       (Bridge server container)
├── requirements.txt        (Python dependencies)
├── .env.example            (Environment template)
├── setup.sh                (Management script)
└── README.md               (This file)
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

## Security Best Practices

- Never commit `.env` file with real credentials to version control
- Use API-only member accounts with minimum required permissions
- **Read-only access:** This server is designed for read-only operations only
- Regularly rotate API credentials
- Limit IP access to ConnectWise API if possible
- Run bridge server in private network when possible
- Monitor API usage and set quotas

## Development & Testing

**Local Development:**

MCP Server:
```bash
cd ConnectWise-MCP-Server
pip install -r requirements.txt
export CW_COMPANY_ID=your_company_id
export CW_PUBLIC_KEY=your_public_key
export CW_PRIVATE_KEY=your_private_key
python connectwise_mcp.py
```

Bridge Server:
```bash
npm install express cors
export MCP_PORT=3002
node bridge-server.js
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

**Python packages (connectwise-mcp-server):**
- mcp - Model Context Protocol framework
- fastmcp - Fast MCP server implementation
- httpx - Async HTTP client
- pydantic - Data validation

**Node.js packages (mcp-bridge):**
- express - Web server framework
- cors - CORS middleware

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

**Current Version:** 1.1.0

### Changelog

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
