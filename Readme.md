# ConnectWise MCP Server

A Docker-based Model Context Protocol (MCP) bridge server that provides read-only AI-assisted ConnectWise Manage access through OpenWebUI. This server enables AI agents to search, read, and analyze ConnectWise data via natural language commands.

## 🏗️ Architecture

The ConnectWise MCP Server consists of two components:
- **MCP Server** - Python-based server that interfaces with ConnectWise Manage API
- **MCP Bridge** - Node.js Express server that exposes an HTTP API for OpenWebUI

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐     ┌────────────────┐
│   OpenWebUI     │◄────►│   MCP Bridge     │◄────►│ ConnectWise    │◄────►│ ConnectWise   │
│     Tools       │ HTTP │   (Port 3002)    │Docker│  MCP Server    │HTTPS │   Manage API  │
└─────────────────┘     └──────────────────┘     └─────────────────┘     └────────────────┘
```

## ✨ Features

### Company Management (Read-Only)
- Search companies with advanced filtering
- Retrieve complete company information
- View company contacts and relationships

### Service Tickets (Read-Only)
- Search tickets using ConnectWise conditions
- Retrieve full ticket details
- View ticket notes and history
- Filter by status, company, date, etc.

### Contact Management (Read-Only)
- Search and retrieve contacts
- View contact details and company associations
- Filter contacts by various criteria

### Sales & Opportunities (Read-Only)
- Search sales opportunities
- View opportunity details and status
- Track sales pipeline

### Agreements & Contracts (Read-Only)
- Search agreements and contracts
- View agreement details
- Track contract status

### Time Tracking (Read-Only)
- Search time entries
- View detailed time tracking data
- Filter by member, date, or ticket

### Project Management (Read-Only)
- Search projects
- View project details and status
- Track project progress

### Activities (Read-Only)
- Search activities and tasks
- View activity details
- Filter by various criteria

### Team Members (Read-Only)
- List team members
- View member details
- Filter active/inactive members

## 📋 Prerequisites

- Docker and Docker Compose installed
- ConnectWise Manage API credentials (Company ID, Public Key, Private Key)
- OpenWebUI already running (any version with Tools support)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd ConnectWise-MCP-Server
```

### 2. Configure ConnectWise Credentials

Create a `.env` file from the example:

```bash
cp .env.example .env
```

Edit `.env` and add your ConnectWise credentials:

```env
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

### 3. Obtaining ConnectWise API Credentials

1. Log in to your ConnectWise Manage instance
2. Navigate to **System** → **Members**
3. Create a new API Member or use existing credentials
4. Generate API Keys:
   - Go to **My Account** → **API Keys**
   - Click **New** to create new API keys
   - Save the **Public Key** and **Private Key**
5. Your **Company ID** is typically shown in the URL or system settings

**Important**: For read-only access, ensure the API member only has read permissions in ConnectWise.

### 4. Start the Server

Using the setup script (recommended):

```bash
chmod +x setup.sh
./setup.sh
```

Select option 1 to start the server.

Or manually with Docker Compose:

```bash
docker-compose up -d --build
```

The ConnectWise MCP Bridge will be available at: `http://localhost:3002`

### 5. Install in OpenWebUI

1. Open OpenWebUI in your browser
2. Go to **Settings** → **Admin Panel** → **Tools**
3. Click **"+ Create New Tool"**
4. Copy the contents of `connectwise_tools.py` from this repository
5. Paste into the tool editor
6. Configure the bridge URL in the **Valves** section:
   - If OpenWebUI is in Docker: `http://connectwise-mcp-bridge:3002`
   - If OpenWebUI is local: `http://localhost:3002`
7. Click **"Save"**
8. Enable the ConnectWise Tools

### 6. Test the Connection

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

## 💡 Usage

Once the ConnectWise Tools are installed in OpenWebUI, you can use natural language commands:

**Example queries:**

- "Show me all open tickets for ACME Corp"
- "Find all companies with 'Tech' in their name"
- "Get details for ticket #12345"
- "List all opportunities with status 'Open'"
- "Show me time entries for this week"
- "Find contacts at Microsoft"
- "What projects are currently active?"
- "Show me all agreements expiring this month"

The AI will automatically call the appropriate ConnectWise tool functions to complete your request.

## 🔧 Available Tools

### Company Tools
- `get_companies(conditions, order_by, page, page_size)` - Search companies
- `get_company(company_id)` - Get specific company

### Ticket Tools
- `get_tickets(conditions, order_by, page, page_size)` - Search tickets
- `get_ticket(ticket_id)` - Get specific ticket
- `get_ticket_notes(ticket_id, page_size)` - Get ticket notes

### Contact Tools
- `get_contacts(conditions, order_by, page, page_size)` - Search contacts
- `get_contact(contact_id)` - Get specific contact

### Sales Tools
- `get_opportunities(conditions, order_by, page, page_size)` - Search opportunities

### Agreement Tools
- `get_agreements(conditions, order_by, page, page_size)` - Search agreements

### Time Entry Tools
- `get_time_entries(conditions, order_by, page, page_size)` - Search time entries

### Project Tools
- `get_projects(conditions, order_by, page, page_size)` - Search projects

### Activity Tools
- `get_activities(conditions, order_by, page, page_size)` - Search activities

### Member Tools
- `get_members(conditions, order_by, page, page_size)` - Search team members

## 📚 ConnectWise API Conditions Examples

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

## ⚙️ Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CW_COMPANY_ID` | ConnectWise Company ID (required) | - |
| `CW_PUBLIC_KEY` | ConnectWise Public API Key (required) | - |
| `CW_PRIVATE_KEY` | ConnectWise Private API Key (required) | - |
| `CW_API_URL` | ConnectWise API base URL | `https://api-na.myconnectwise.net` |
| `CW_API_VERSION` | API version to use | `v2023.2` |
| `CW_CLIENT_ID` | Client ID for API requests | `mcp-connectwise-server` |
| `MCP_PORT` | Port for MCP bridge server | `3002` |
| `LOG_LEVEL` | Logging level | `INFO` |

### API URL Configuration

For cloud-hosted ConnectWise:
- North America: `https://api-na.myconnectwise.net`
- Europe: `https://api-eu.myconnectwise.net`
- Australia: `https://api-au.myconnectwise.net`

For on-premise installations, use your server URL.

## 🐳 Docker Management

### Using the Setup Script

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

### Manual Docker Commands

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

## 🔍 Troubleshooting

### Authentication Errors

If you receive authentication errors:
- Verify your Company ID, Public Key, and Private Key are correct
- Ensure the API member has appropriate permissions
- Check that the API URL matches your ConnectWise instance
- Generate new API keys if needed

### Port Already in Use

If port 3002 is already in use:

1. Edit `.env` file:
   ```env
   MCP_PORT=3003
   ```

2. Edit `docker-compose.yml`: Update port mapping to `3003:3002` and environment `PORT=3003`

3. Restart:
   ```bash
   docker-compose down && docker-compose up -d --build
   ```

4. Update bridge URL in OpenWebUI Tool Valves

### Bridge Not Responding

- Verify bridge is running: `docker-compose ps`
- Check bridge logs: `docker-compose logs mcp-bridge`
- Test health endpoint: `curl http://localhost:3002/health`
- Check bridge URL in OpenWebUI Tool Valves settings:
  - If both in Docker on same network: `http://connectwise-mcp-bridge:3002`
  - If OpenWebUI is local: `http://localhost:3002`

### OpenWebUI Can't Connect

- Make sure you saved the `connectwise_tools.py` in OpenWebUI Tools
- Enable the ConnectWise Tools in OpenWebUI Settings
- Verify the bridge URL is correct in Valves settings
- Check if Docker networks are connected:
  ```bash
  docker network connect openwebui_network connectwise-mcp-bridge
  ```

### Rate Limiting

ConnectWise has API rate limits. If you encounter rate limiting:
- Reduce the `pageSize` parameter
- Add delays between requests
- Check ConnectWise API documentation for current limits

## 🏗️ Project Structure

```
ConnectWise-MCP-Server/
├── Dockerfile                  # MCP server container
├── Dockerfile.bridge           # Bridge server container
├── docker-compose.yml          # Multi-container orchestration
├── connectwise_mcp.py          # Main MCP server implementation
├── bridge-server.js            # HTTP API bridge server
├── connectwise_tools.py        # OpenWebUI Tool (upload to OpenWebUI)
├── requirements.txt            # Python dependencies
├── .env.example                # Environment template
├── setup.sh                    # Setup and management script
└── README.md                   # This file
```

## 🔒 Security Best Practices

- **Never commit** `.env` file with real credentials to version control
- Use **API-only member accounts** with minimum required permissions
- **Read-only access**: This server is designed for read-only operations only
- **Regularly rotate** API credentials
- **Limit IP access** to ConnectWise API if possible
- Run bridge server in **private network** when possible
- Monitor API usage and set quotas

## 🧪 Development & Testing

### Local Development

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

### Testing API Endpoints

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

## 📦 Dependencies

### Python packages (connectwise-mcp-server):
- `mcp` - Model Context Protocol framework
- `fastmcp` - Fast MCP server implementation
- `httpx` - Async HTTP client
- `pydantic` - Data validation

### Node.js packages (mcp-bridge):
- `express` - Web server framework
- `cors` - CORS middleware

## 📄 License

MIT License - See LICENSE file for details

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📞 Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Check existing documentation
- Review ConnectWise API documentation
- Check OpenWebUI documentation

## 🔗 Resources

- [ConnectWise Developer Network](https://developer.connectwise.com/)
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
- [OpenWebUI](https://github.com/open-webui/open-webui)
- [ConnectWise REST API Documentation](https://developer.connectwise.com/Products/Manage/REST)

## ⚠️ Important Notes

- This server provides **READ-ONLY** access to ConnectWise
- No write operations are implemented
- Designed for AI-assisted data retrieval and analysis
- Respects ConnectWise API rate limits
- Requires valid ConnectWise API credentials

## 🎯 Version

Current Version: 1.0.0

## 📝 Changelog

### Version 1.0.0 (Initial Release)
- Read-only access to ConnectWise Manage
- Support for companies, tickets, contacts, opportunities, agreements
- Time entries, projects, activities, and members
- Docker-based deployment
- OpenWebUI integration
- MCP bridge architecture
- Comprehensive documentation

---

**Built with ❤️ for the ConnectWise and AI community**
