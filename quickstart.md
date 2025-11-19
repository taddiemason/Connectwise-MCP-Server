# ConnectWise MCP Server - Quick Start Guide

This guide will get you up and running in 5 minutes!

## Step 1: Get Your ConnectWise API Credentials

1. Log in to ConnectWise Manage
2. Go to **System** → **Members**
3. Create an API member with **READ-ONLY** permissions
4. Go to **My Account** → **API Keys**
5. Generate new API keys
6. Save these three values:
   - **Company ID** (usually visible in URL)
   - **Public Key**
   - **Private Key**

## Step 2: Configure the Server

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your credentials:
   ```env
   CW_COMPANY_ID=your_company_id_here
   CW_PUBLIC_KEY=your_public_key_here
   CW_PRIVATE_KEY=your_private_key_here
   ```

## Step 3: Start the Server

Option A - Using the setup script:
```bash
chmod +x Setup.sh
./Setup.sh
# Select option 1
```

Option B - Using Docker directly:
```bash
docker-compose up -d --build
```

## Step 4: Test the Connection

```bash
curl http://localhost:3002/health
```

You should see:
```json
{
  "status": "ok",
  "service": "connectwise-mcp-bridge"
}
```

## Step 5: Add to OpenWebUI

1. Open OpenWebUI
2. Go to **Settings** → **Admin Panel** → **Tools**
3. Click **"+ Create New Tool"**
4. Copy all content from `connectwise_tools.py`
5. Paste into the editor
6. In **Valves** section, set:
   - If OpenWebUI in Docker: `http://connectwise-mcp-bridge:3002`
   - If OpenWebUI local: `http://localhost:3002`
7. Click **"Save"**
8. Enable the tool

## Step 6: Try It Out!

In OpenWebUI, ask:
- "Show me all open tickets"
- "Find companies with 'Tech' in the name"
- "Get details for ticket #12345"
- "List all opportunities"

## Common Issues

**Authentication Error?**
- Double-check your credentials in `.env`
- Ensure API member has proper permissions

**Port 3002 already in use?**
- Change `MCP_PORT=3003` in `.env`
- Update port mapping in `docker-compose.yml`

**OpenWebUI can't connect?**
- Verify bridge URL in Valves settings
- If both in Docker, use: `http://connectwise-mcp-bridge:3002`
- If OpenWebUI local, use: `http://localhost:3002`

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check [ConnectWise API documentation](https://developer.connectwise.com/) for advanced queries
- Explore all available tools in `connectwise_tools.py`

## Need Help?

1. Check logs: `docker-compose logs -f`
2. Test health: `curl http://localhost:3002/health`
3. Verify status: `docker-compose ps`

---

That's it! You're now ready to use AI to query your ConnectWise data! 🚀
