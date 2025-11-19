# ConnectWise MCP Server

A Docker-based Model Context Protocol (MCP) bridge server that provides AI-assisted ConnectWise Manage access through OpenWebUI. This server enables AI agents to search, read, and analyze ConnectWise data via natural language commands.

## Overview

The ConnectWise MCP Server consists of two components:

1. **MCP Server** - Python-based server that interfaces with ConnectWise Manage API
2. **MCP Bridge** - Node.js Express server that exposes an HTTP API for OpenWebUI

### Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐         ┌────────────────┐
│   OpenWebUI     │◄───────►│   MCP Bridge     │◄───────►│  ConnectWise    │◄───────►│  ConnectWise  │
│     Tools       │  HTTP   │   (Port 3002)    │  Docker │   MCP Server    │  HTTPS  │   Manage API  │
└─────────────────┘         └──────────────────┘         └─────────────────┘         └────────────────┘
```

## Features

### Company Management (Read-Only)
- Search companies with advanced filtering
- Retrieve complete company information
- View company contacts and relationships
- Filter by various criteria

### Service Tickets (Read-Only)
- Search tickets using ConnectWise conditions
- Retrieve full ticket details including notes
- View ticket history and timeline
- Filter by status, company, date, priority, etc.

### Contact Management (Read-Only)
- Search and retrieve contacts
- View contact details and company associations
- Filter contacts by various criteria
- Access communication preferences

### Sales & Opportunities (Read-Only)
- Search sales opportunities
- View opportunity details and status
- Track sales pipeline
- Monitor forecast and probability

### Agreements & Contracts (Read-Only)
- Search agreements and contracts
- View agreement details and terms
- Track contract status and renewal dates
- Monitor billing information

### Time Tracking (Read-Only)
- Search time entries
- View detailed time tracking data
- Filter by member, date, or ticket
- Analyze billable vs non-billable time

### Project Management (Read-Only)
- Search projects
- View project details and status
- Track project progress
- Monitor project phases and tasks

### Activities (Read-Only)
- Search activities and tasks
- View activity details
- Filter by various criteria
- Track scheduled and completed activities

### Team Members (Read-Only)
- List team members
- View member details and roles
- Filter active/inactive members
- Access member contact information

## Prerequisites

- **Docker** and **Docker Compose** installed
- **ConnectWise Manage API credentials** (Company ID, Public Key, Private Key)
- **OpenWebUI** already running (any version with Tools support)

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/taddiemason/Connectwise-MCP-Server.git
cd Connectwise-MCP-Server
```

### 2. Get ConnectWise API Credentials

You need three pieces of information from ConnectWise Manage:

**Step 1: Find Your Company ID**

Your Company ID is typically visible in your ConnectWise URL:

```
https://acmetechsolutions.myconnectwise.net/v2023_2/...
         ^^^^^^^^^^^^^^^^^
         This is your Company ID
```

Or navigate to **System** → **Setup Tables** → **Company** and look for "Company Identifier".

**Step 2: Create API Member (Recommended)**

For production use, create a dedicated API member with read-only permissions:

1. Navigate to **System** → **Members**
2. Click **"+ New"** or **"Add Member"**
3. Fill in the form:
   - **Identifier:** `mcp-readonly-api`
   - **Name:** `MCP Read-Only API`
   - **Member Type:** Select **"API Member"** or **"Integration"**
4. Set **Security Roles** (Read-Only permissions):
   - ✅ View Tickets
   - ✅ View Companies
   - ✅ View Contacts
   - ✅ View Opportunities
   - ✅ View Projects
   - ✅ View Time Entries
   - ✅ View Agreements
   - ❌ NO write/edit/delete permissions
5. Click **"API Keys"** tab
6. Click **"+ New"** or **"Generate Keys"**
7. Save your **Public Key** and **Private Key**
   - ⚠️ **IMPORTANT:** The Private Key will only be shown once!

**Step 3: Determine Your API URL**

Choose based on your ConnectWise region:

| Region | API URL |
|--------|---------|
| 🇺🇸 North America | `https://api-na.myconnectwise.net` |
| 🇪🇺 Europe | `https://api-eu.myconnectwise.net` |
| 🇦🇺 Australia | `https://api-au.myconnectwise.net` |
| 🏢 On-Premise | `https://your-server-url` |

For detailed instructions, see [connectwise_setup.md](connectwise_setup.md).

### 3. Configure ConnectWise Credentials

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

**Important:**
- This file is in `.gitignore` and won't be committed
- Never commit credentials to version control
- Use read-only API permissions for security

### 4. Start the MCP Server

Using the setup script (recommended):

```bash
chmod +x Setup.sh
./Setup.sh
```

Select option 1 to start the server.

Or manually with Docker Compose:

```bash
docker-compose up -d --build
```

The ConnectWise MCP Bridge will be available at: **http://localhost:3002**

### 5. Add Tool to OpenWebUI

1. **Open OpenWebUI** in your browser
2. Go to **Settings** → **Admin Panel** → **Tools**
3. Click **"+ Create New Tool"**
4. **Copy the contents** of `connectwise_tools.py` from this repository
5. **Paste** into the tool editor
6. **Configure the bridge URL** in the Valves section:
   - If OpenWebUI is in Docker: `http://connectwise-mcp-bridge:3002`
   - If OpenWebUI is local: `http://localhost:3002`
7. Click **"Save"**
8. **Enable** the ConnectWise Tools

### 6. Verify Installation

Test the health endpoint:

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

Once the ConnectWise Tools are installed in OpenWebUI, you can use these functions:

### Company Tools
- `get_companies(conditions, order_by, page, page_size)` - Search companies
- `get_company(company_id)` - Get specific company by ID

### Ticket Tools
- `get_tickets(conditions, order_by, page, page_size)` - Search service tickets
- `get_ticket(ticket_id)` - Get specific ticket by ID
- `get_ticket_notes(ticket_id, page_size)` - Get notes for a ticket

### Contact Tools
- `get_contacts(conditions, order_by, page, page_size)` - Search contacts
- `get_contact(contact_id)` - Get specific contact by ID

### Sales Tools
- `get_opportunities(conditions, order_by, page, page_size)` - Search sales opportunities

### Agreement Tools
- `get_agreements(conditions, order_by, page, page_size)` - Search agreements/contracts

### Time Entry Tools
- `get_time_entries(conditions, order_by, page, page_size)` - Search time entries

### Project Tools
- `get_projects(conditions, order_by, page, page_size)` - Search projects

### Activity Tools
- `get_activities(conditions, order_by, page, page_size)` - Search activities

### Member Tools
- `get_members(conditions, order_by, page, page_size)` - Search team members

## Usage Examples

Once the ConnectWise Tools are installed in OpenWebUI, you can use natural language commands:

**Example queries:**

```
"Show me all open tickets for ACME Corp"
"Find all companies with 'Tech' in their name"
"Get details for ticket #12345"
"List all opportunities with status 'Open'"
"Show me time entries for this week"
"Find contacts at Microsoft"
"What projects are currently active?"
"Show me all agreements expiring this month"
```

The AI will automatically call the appropriate ConnectWise tool functions to complete your request.

## ConnectWise API Conditions

ConnectWise uses a powerful condition syntax for filtering. Here are some examples:

```bash
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

For more examples, see the [ConnectWise API Documentation](https://developer.connectwise.com/).

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CW_COMPANY_ID` | ConnectWise Company ID (required) | - |
| `CW_PUBLIC_KEY` | ConnectWise Public API Key (required) | - |
| `CW_PRIVATE_KEY` | ConnectWise Private API Key (required) | - |
| `CW_API_URL` | ConnectWise API base URL | `https://api-na.myconnectwise.net` |
| `CW_API_VERSION` | API version to use | `v2023.2` |
| `CW_CLIENT_ID` | Client ID for API requests | `mcp-connectwise-server` |
| `MCP_PORT` | Port for MCP bridge server | `3002` |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` |

### Bridge URL Configuration

The bridge URL in OpenWebUI's Valves settings depends on your setup:

**Scenario 1: OpenWebUI in Docker on same host**
```
http://connectwise-mcp-bridge:3002
```

**Scenario 2: OpenWebUI running locally**
```
http://localhost:3002
```

**Scenario 3: OpenWebUI on different server**
```
http://your-server-ip:3002
```

Make sure to configure the correct URL based on your deployment.

## Docker Management

### Using the Setup Script

```bash
./Setup.sh
```

**Menu Options:**
1. Start ConnectWise MCP Server
2. Stop ConnectWise MCP Server
3. Restart ConnectWise MCP Server
4. View logs
5. Check status
6. Update server
7. Clean up
8. Exit

### Manual Docker Commands

```bash
# Start servers
docker-compose up -d --build

# View logs (all containers)
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

# Rebuild and restart
docker-compose up -d --build
```

## Troubleshooting

### Authentication Errors

**Symptoms:** `401 Unauthorized` or `403 Forbidden` errors

**Solutions:**
1. Verify your Company ID, Public Key, and Private Key are correct in `.env`
2. Ensure the API member has appropriate read permissions
3. Check that the API URL matches your ConnectWise instance region
4. Verify the API member is active (not disabled)
5. Try generating new API keys if needed

**Test manually:**
```bash
# Replace with your values
COMPANY_ID="yourcompany"
PUBLIC_KEY="yourpublickey"
PRIVATE_KEY="yourprivatekey"

# Create auth string
AUTH=$(echo -n "${COMPANY_ID}+${PUBLIC_KEY}:${PRIVATE_KEY}" | base64)

# Test API
curl -H "Authorization: Basic ${AUTH}" \
     -H "clientId: test" \
     "https://api-na.myconnectwise.net/v2023.2/apis/3.0/system/info"
```

If this works, your credentials are correct!

### Port Already in Use

**Symptoms:** Error binding to port 3002

**Solutions:**
1. Edit `.env` file and change the port:
   ```bash
   MCP_PORT=3003
   ```
2. Restart the server:
   ```bash
   docker-compose down && docker-compose up -d --build
   ```
3. Update bridge URL in OpenWebUI Tool Valves settings

### Bridge Not Responding

**Symptoms:** OpenWebUI can't connect to bridge

**Solutions:**
1. Verify bridge is running:
   ```bash
   docker-compose ps
   ```
2. Check bridge logs for errors:
   ```bash
   docker-compose logs mcp-bridge
   ```
3. Test health endpoint:
   ```bash
   curl http://localhost:3002/health
   ```
4. Verify bridge URL in OpenWebUI Tool Valves settings matches your setup

### OpenWebUI Can't Connect

**Symptoms:** Tool calls fail or timeout

**Solutions:**
1. Make sure you saved `connectwise_tools.py` in OpenWebUI Tools
2. Enable the ConnectWise Tools in OpenWebUI Settings
3. Verify the bridge URL is correct in Valves settings
4. If both are in Docker, ensure they're on the same network:
   ```bash
   docker network connect openwebui_network connectwise-mcp-bridge
   ```

### Rate Limiting

**Symptoms:** API errors about rate limits

**Solutions:**
1. Reduce the `pageSize` parameter in queries
2. Add delays between requests
3. Check ConnectWise API documentation for current rate limits
4. Monitor API usage in ConnectWise admin panel

### Docker Permission Errors

**Symptoms:** Permission denied errors when running Docker commands

**Solutions:**
1. Add your user to the docker group:
   ```bash
   sudo usermod -aG docker $USER
   newgrp docker
   ```
2. Or run commands with sudo:
   ```bash
   sudo docker-compose up -d --build
   ```

## Project Structure

```
Connectwise-MCP-Server/
├── .env.example                # Environment variables template
├── .gitignore                  # Git ignore rules
├── LICENSE                     # MIT License
├── README.md                   # This file
├── Setup.sh                    # Setup and management script
├── Dockerfile                  # MCP server container
├── Dockerfile.bridge           # Bridge server container
├── docker-compose.yml          # Multi-container orchestration
├── connectwise_mcp.py          # Main MCP server implementation
├── bridge-server.js            # HTTP API bridge server
├── connectwise_tools.py        # OpenWebUI Tool (upload to OpenWebUI)
├── connectwise_setup.md        # Detailed credential setup guide
├── quickstart.md               # Quick start guide
├── requirements.txt            # Python dependencies
├── package.json                # Node.js dependencies
└── test.sh                     # Test script
```

## Security Best Practices

1. **Never commit `.env` file** with real credentials to version control
2. **Use API-only member accounts** with minimum required permissions
3. **Read-only access:** This server is designed for read-only operations only
4. **Regularly rotate API credentials** (quarterly recommended)
5. **Limit IP access** to ConnectWise API if possible
6. **Run bridge server** in private network when possible
7. **Monitor API usage** and set quotas
8. **Use strong passwords** for API member accounts
9. **Enable 2FA** for ConnectWise admin accounts
10. **Review logs regularly** for suspicious activity

## Development & Testing

### Local Development

**MCP Server:**

```bash
cd Connectwise-MCP-Server
pip install -r requirements.txt
export CW_COMPANY_ID=your_company_id
export CW_PUBLIC_KEY=your_public_key
export CW_PRIVATE_KEY=your_private_key
python connectwise_mcp.py
```

**Bridge Server:**

```bash
npm install express cors
export MCP_PORT=3002
node bridge-server.js
```

### Testing API Endpoints

**Health check:**

```bash
curl http://localhost:3002/health
```

**Test search:**

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

### Python Packages (connectwise-mcp-server)
- `mcp` - Model Context Protocol framework
- `fastmcp` - Fast MCP server implementation
- `httpx` - Async HTTP client
- `pydantic` - Data validation

### Node.js Packages (mcp-bridge)
- `express` - Web server framework
- `cors` - CORS middleware

## Resources

- [ConnectWise Developer Network](https://developer.connectwise.com/)
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
- [OpenWebUI](https://openwebui.com/)
- [ConnectWise REST API Documentation](https://developer.connectwise.com/Products/Manage/REST)

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Support

For issues, questions, or contributions:

- Open an issue on [GitHub](https://github.com/taddiemason/Connectwise-MCP-Server/issues)
- Check existing [documentation](connectwise_setup.md)
- Review [ConnectWise API documentation](https://developer.connectwise.com/)
- Check [OpenWebUI documentation](https://docs.openwebui.com/)

## License

MIT License - See [LICENSE](LICENSE) file for details.

## Important Notes

- ⚠️ This server provides **READ-ONLY** access to ConnectWise
- ⚠️ No write operations are implemented
- ⚠️ Designed for AI-assisted data retrieval and analysis
- ⚠️ Respects ConnectWise API rate limits
- ⚠️ Requires valid ConnectWise API credentials

## Version

**Current Version:** 1.0.0

## Changelog

### Version 1.0.0 (Initial Release)
- Read-only access to ConnectWise Manage
- Support for companies, tickets, contacts, opportunities, agreements
- Time entries, projects, activities, and members
- Docker-based deployment
- OpenWebUI integration
- MCP bridge architecture
- Comprehensive documentation
