"""
ConnectWise MCP Server - Read-only access to ConnectWise Manage
"""
import os
import json
import base64
import logging
from typing import Optional, Any
import httpx
from mcp.server import Server
from mcp.types import TextContent, Tool, INVALID_PARAMS, INTERNAL_ERROR
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables
CW_COMPANY_ID = os.getenv('CW_COMPANY_ID')
CW_PUBLIC_KEY = os.getenv('CW_PUBLIC_KEY')
CW_PRIVATE_KEY = os.getenv('CW_PRIVATE_KEY')
CW_API_URL = os.getenv('CW_API_URL', 'https://api-na.myconnectwise.net')
CW_API_VERSION = os.getenv('CW_API_VERSION', 'v2023.2')
CW_CLIENT_ID = os.getenv('CW_CLIENT_ID', 'mcp-connectwise-server')

class ConnectWiseClient:
    """Client for ConnectWise Manage API - Read-only operations"""
    
    def __init__(self):
        if not all([CW_COMPANY_ID, CW_PUBLIC_KEY, CW_PRIVATE_KEY]):
            raise ValueError("ConnectWise credentials not configured")
        
        self.base_url = f"{CW_API_URL}/{CW_API_VERSION}/apis/3.0"
        
        # Create Basic Auth header
        auth_string = f"{CW_COMPANY_ID}+{CW_PUBLIC_KEY}:{CW_PRIVATE_KEY}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        self.headers = {
            'Authorization': f'Basic {auth_b64}',
            'Content-Type': 'application/json',
            'clientId': CW_CLIENT_ID,
            'Accept': 'application/json'
        }
        
        self.client = httpx.AsyncClient(headers=self.headers, timeout=30.0)
        logger.info(f"ConnectWise client initialized for company: {CW_COMPANY_ID}")
    
    async def get(self, endpoint: str, params: Optional[dict] = None) -> Any:
        """Make a GET request to ConnectWise API"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        logger.info(f"GET request to: {url}")
        
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Request failed: {str(e)}")
            raise
    
    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

# Initialize ConnectWise client
try:
    cw_client = ConnectWiseClient()
except Exception as e:
    logger.error(f"Failed to initialize ConnectWise client: {str(e)}")
    raise

# Initialize MCP server
app = Server("connectwise-mcp-server")

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available read-only ConnectWise tools"""
    return [
        # Company endpoints
        Tool(
            name="connectwise_get_companies",
            description="Search and retrieve companies. Supports filtering with conditions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "conditions": {
                        "type": "string",
                        "description": "ConnectWise API conditions (e.g., 'identifier=\"ACME\"' or 'name like \"%Corp%\"')"
                    },
                    "orderBy": {
                        "type": "string",
                        "description": "Field to order by (e.g., 'name', 'id')"
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number (1-based)",
                        "default": 1
                    },
                    "pageSize": {
                        "type": "integer",
                        "description": "Results per page (max 1000)",
                        "default": 25
                    }
                }
            }
        ),
        Tool(
            name="connectwise_get_company",
            description="Get a specific company by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "company_id": {
                        "type": "integer",
                        "description": "Company ID"
                    }
                },
                "required": ["company_id"]
            }
        ),
        
        # Ticket endpoints
        Tool(
            name="connectwise_get_tickets",
            description="Search and retrieve service tickets. Supports filtering with conditions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "conditions": {
                        "type": "string",
                        "description": "ConnectWise API conditions (e.g., 'status/name=\"New\"' or 'company/identifier=\"ACME\"')"
                    },
                    "orderBy": {
                        "type": "string",
                        "description": "Field to order by (e.g., 'id desc', 'summary')"
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number (1-based)",
                        "default": 1
                    },
                    "pageSize": {
                        "type": "integer",
                        "description": "Results per page (max 1000)",
                        "default": 25
                    }
                },
            }
        ),
        Tool(
            name="connectwise_get_ticket",
            description="Get a specific ticket by ID with full details",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticket_id": {
                        "type": "integer",
                        "description": "Ticket ID"
                    }
                },
                "required": ["ticket_id"]
            }
        ),
        Tool(
            name="connectwise_get_ticket_notes",
            description="Get notes for a specific ticket",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticket_id": {
                        "type": "integer",
                        "description": "Ticket ID"
                    },
                    "pageSize": {
                        "type": "integer",
                        "description": "Results per page",
                        "default": 25
                    }
                },
                "required": ["ticket_id"]
            }
        ),
        
        # Contact endpoints
        Tool(
            name="connectwise_get_contacts",
            description="Search and retrieve contacts. Supports filtering with conditions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "conditions": {
                        "type": "string",
                        "description": "ConnectWise API conditions (e.g., 'company/identifier=\"ACME\"')"
                    },
                    "orderBy": {
                        "type": "string",
                        "description": "Field to order by"
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number (1-based)",
                        "default": 1
                    },
                    "pageSize": {
                        "type": "integer",
                        "description": "Results per page (max 1000)",
                        "default": 25
                    }
                }
            }
        ),
        Tool(
            name="connectwise_get_contact",
            description="Get a specific contact by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "contact_id": {
                        "type": "integer",
                        "description": "Contact ID"
                    }
                },
                "required": ["contact_id"]
            }
        ),
        
        # Opportunity endpoints
        Tool(
            name="connectwise_get_opportunities",
            description="Search and retrieve sales opportunities. Supports filtering with conditions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "conditions": {
                        "type": "string",
                        "description": "ConnectWise API conditions (e.g., 'status/name=\"Open\"')"
                    },
                    "orderBy": {
                        "type": "string",
                        "description": "Field to order by"
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number (1-based)",
                        "default": 1
                    },
                    "pageSize": {
                        "type": "integer",
                        "description": "Results per page (max 1000)",
                        "default": 25
                    }
                }
            }
        ),
        
        # Agreement endpoints
        Tool(
            name="connectwise_get_agreements",
            description="Search and retrieve agreements/contracts. Supports filtering with conditions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "conditions": {
                        "type": "string",
                        "description": "ConnectWise API conditions"
                    },
                    "orderBy": {
                        "type": "string",
                        "description": "Field to order by"
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number (1-based)",
                        "default": 1
                    },
                    "pageSize": {
                        "type": "integer",
                        "description": "Results per page (max 1000)",
                        "default": 25
                    }
                }
            }
        ),
        
        # Time Entry endpoints
        Tool(
            name="connectwise_get_time_entries",
            description="Search and retrieve time entries. Supports filtering with conditions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "conditions": {
                        "type": "string",
                        "description": "ConnectWise API conditions (e.g., 'member/identifier=\"john\" and timeStart > [2024-01-01]')"
                    },
                    "orderBy": {
                        "type": "string",
                        "description": "Field to order by"
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number (1-based)",
                        "default": 1
                    },
                    "pageSize": {
                        "type": "integer",
                        "description": "Results per page (max 1000)",
                        "default": 25
                    }
                }
            }
        ),
        
        # Project endpoints
        Tool(
            name="connectwise_get_projects",
            description="Search and retrieve projects. Supports filtering with conditions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "conditions": {
                        "type": "string",
                        "description": "ConnectWise API conditions (e.g., 'status/name=\"Open\"')"
                    },
                    "orderBy": {
                        "type": "string",
                        "description": "Field to order by"
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number (1-based)",
                        "default": 1
                    },
                    "pageSize": {
                        "type": "integer",
                        "description": "Results per page (max 1000)",
                        "default": 25
                    }
                }
            }
        ),
        
        # Activity endpoints
        Tool(
            name="connectwise_get_activities",
            description="Search and retrieve activities. Supports filtering with conditions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "conditions": {
                        "type": "string",
                        "description": "ConnectWise API conditions"
                    },
                    "orderBy": {
                        "type": "string",
                        "description": "Field to order by"
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number (1-based)",
                        "default": 1
                    },
                    "pageSize": {
                        "type": "integer",
                        "description": "Results per page (max 1000)",
                        "default": 25
                    }
                }
            }
        ),
        
        # Member endpoints
        Tool(
            name="connectwise_get_members",
            description="Search and retrieve team members. Supports filtering with conditions.",
            inputSchema={
                "type": "object",
                "properties": {
                    "conditions": {
                        "type": "string",
                        "description": "ConnectWise API conditions (e.g., 'inactiveFlag=false')"
                    },
                    "orderBy": {
                        "type": "string",
                        "description": "Field to order by"
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number (1-based)",
                        "default": 1
                    },
                    "pageSize": {
                        "type": "integer",
                        "description": "Results per page (max 1000)",
                        "default": 25
                    }
                }
            }
        ),
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls for read-only ConnectWise operations"""
    try:
        # Companies
        if name == "connectwise_get_companies":
            params = _build_params(arguments)
            data = await cw_client.get("company/companies", params=params)
            return [TextContent(type="text", text=json.dumps(data, indent=2))]
        
        elif name == "connectwise_get_company":
            company_id = arguments.get("company_id")
            data = await cw_client.get(f"company/companies/{company_id}")
            return [TextContent(type="text", text=json.dumps(data, indent=2))]
        
        # Tickets
        elif name == "connectwise_get_tickets":
            params = _build_params(arguments)
            data = await cw_client.get("service/tickets", params=params)
            return [TextContent(type="text", text=json.dumps(data, indent=2))]
        
        elif name == "connectwise_get_ticket":
            ticket_id = arguments.get("ticket_id")
            data = await cw_client.get(f"service/tickets/{ticket_id}")
            return [TextContent(type="text", text=json.dumps(data, indent=2))]
        
        elif name == "connectwise_get_ticket_notes":
            ticket_id = arguments.get("ticket_id")
            page_size = arguments.get("pageSize", 25)
            params = {"pageSize": page_size}
            data = await cw_client.get(f"service/tickets/{ticket_id}/notes", params=params)
            return [TextContent(type="text", text=json.dumps(data, indent=2))]
        
        # Contacts
        elif name == "connectwise_get_contacts":
            params = _build_params(arguments)
            data = await cw_client.get("company/contacts", params=params)
            return [TextContent(type="text", text=json.dumps(data, indent=2))]
        
        elif name == "connectwise_get_contact":
            contact_id = arguments.get("contact_id")
            data = await cw_client.get(f"company/contacts/{contact_id}")
            return [TextContent(type="text", text=json.dumps(data, indent=2))]
        
        # Opportunities
        elif name == "connectwise_get_opportunities":
            params = _build_params(arguments)
            data = await cw_client.get("sales/opportunities", params=params)
            return [TextContent(type="text", text=json.dumps(data, indent=2))]
        
        # Agreements
        elif name == "connectwise_get_agreements":
            params = _build_params(arguments)
            data = await cw_client.get("finance/agreements", params=params)
            return [TextContent(type="text", text=json.dumps(data, indent=2))]
        
        # Time Entries
        elif name == "connectwise_get_time_entries":
            params = _build_params(arguments)
            data = await cw_client.get("time/entries", params=params)
            return [TextContent(type="text", text=json.dumps(data, indent=2))]
        
        # Projects
        elif name == "connectwise_get_projects":
            params = _build_params(arguments)
            data = await cw_client.get("project/projects", params=params)
            return [TextContent(type="text", text=json.dumps(data, indent=2))]
        
        # Activities
        elif name == "connectwise_get_activities":
            params = _build_params(arguments)
            data = await cw_client.get("sales/activities", params=params)
            return [TextContent(type="text", text=json.dumps(data, indent=2))]
        
        # Members
        elif name == "connectwise_get_members":
            params = _build_params(arguments)
            data = await cw_client.get("system/members", params=params)
            return [TextContent(type="text", text=json.dumps(data, indent=2))]
        
        else:
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Unknown tool: {name}"})
            )]
            
    except Exception as e:
        logger.error(f"Error executing tool {name}: {str(e)}")
        return [TextContent(
            type="text",
            text=json.dumps({"error": str(e)})
        )]

def _build_params(arguments: dict) -> dict:
    """Build query parameters from arguments"""
    params = {}
    
    if "conditions" in arguments and arguments["conditions"]:
        params["conditions"] = arguments["conditions"]
    
    if "orderBy" in arguments and arguments["orderBy"]:
        params["orderBy"] = arguments["orderBy"]
    
    if "page" in arguments:
        params["page"] = arguments["page"]
    
    if "pageSize" in arguments:
        params["pageSize"] = arguments["pageSize"]
    
    return params

async def main():
    """Run the MCP server"""
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
