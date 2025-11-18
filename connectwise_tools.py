"""
title: ConnectWise Tools
description: Read-only access to ConnectWise Manage via MCP
author: AI Assistant
version: 1.0.0
license: MIT
requirements: requests
"""

import requests
import json
from typing import Optional
from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        CONNECTWISE_BRIDGE_URL: str = Field(
            default="http://connectwise-mcp-bridge:3002",
            description="URL of the ConnectWise MCP bridge server"
        )
        REQUEST_TIMEOUT: int = Field(
            default=300,
            description="Request timeout in seconds"
        )

    def __init__(self):
        self.valves = self.Valves()

    def _execute_tool(self, tool_name: str, arguments: dict) -> dict:
        """Execute a ConnectWise tool via the MCP bridge"""
        url = f"{self.valves.CONNECTWISE_BRIDGE_URL}/v1/tools/execute"
        
        payload = {
            "tool_name": tool_name,
            "arguments": arguments
        }
        
        try:
            response = requests.post(
                url,
                json=payload,
                timeout=self.valves.REQUEST_TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {str(e)}"}

    def get_companies(
        self,
        conditions: Optional[str] = None,
        order_by: Optional[str] = None,
        page: int = 1,
        page_size: int = 25
    ) -> str:
        """
        Search and retrieve companies from ConnectWise.
        
        :param conditions: Filter conditions (e.g., 'identifier="ACME"' or 'name like "%Corp%"')
        :param order_by: Field to order by (e.g., 'name', 'id')
        :param page: Page number (1-based)
        :param page_size: Results per page (max 1000)
        :return: JSON string with company data
        """
        args = {
            "page": page,
            "pageSize": page_size
        }
        if conditions:
            args["conditions"] = conditions
        if order_by:
            args["orderBy"] = order_by
            
        result = self._execute_tool("connectwise_get_companies", args)
        return json.dumps(result, indent=2)

    def get_company(self, company_id: int) -> str:
        """
        Get a specific company by ID.
        
        :param company_id: Company ID
        :return: JSON string with company data
        """
        result = self._execute_tool("connectwise_get_company", {"company_id": company_id})
        return json.dumps(result, indent=2)

    def get_tickets(
        self,
        conditions: Optional[str] = None,
        order_by: Optional[str] = None,
        page: int = 1,
        page_size: int = 25
    ) -> str:
        """
        Search and retrieve service tickets from ConnectWise.
        
        :param conditions: Filter conditions (e.g., 'status/name="New"' or 'company/identifier="ACME"')
        :param order_by: Field to order by (e.g., 'id desc', 'summary')
        :param page: Page number (1-based)
        :param page_size: Results per page (max 1000)
        :return: JSON string with ticket data
        """
        args = {
            "page": page,
            "pageSize": page_size
        }
        if conditions:
            args["conditions"] = conditions
        if order_by:
            args["orderBy"] = order_by
            
        result = self._execute_tool("connectwise_get_tickets", args)
        return json.dumps(result, indent=2)

    def get_ticket(self, ticket_id: int) -> str:
        """
        Get a specific ticket by ID with full details.
        
        :param ticket_id: Ticket ID
        :return: JSON string with ticket data
        """
        result = self._execute_tool("connectwise_get_ticket", {"ticket_id": ticket_id})
        return json.dumps(result, indent=2)

    def get_ticket_notes(self, ticket_id: int, page_size: int = 25) -> str:
        """
        Get notes for a specific ticket.
        
        :param ticket_id: Ticket ID
        :param page_size: Results per page
        :return: JSON string with ticket notes
        """
        result = self._execute_tool("connectwise_get_ticket_notes", {
            "ticket_id": ticket_id,
            "pageSize": page_size
        })
        return json.dumps(result, indent=2)

    def get_contacts(
        self,
        conditions: Optional[str] = None,
        order_by: Optional[str] = None,
        page: int = 1,
        page_size: int = 25
    ) -> str:
        """
        Search and retrieve contacts from ConnectWise.
        
        :param conditions: Filter conditions (e.g., 'company/identifier="ACME"')
        :param order_by: Field to order by
        :param page: Page number (1-based)
        :param page_size: Results per page (max 1000)
        :return: JSON string with contact data
        """
        args = {
            "page": page,
            "pageSize": page_size
        }
        if conditions:
            args["conditions"] = conditions
        if order_by:
            args["orderBy"] = order_by
            
        result = self._execute_tool("connectwise_get_contacts", args)
        return json.dumps(result, indent=2)

    def get_contact(self, contact_id: int) -> str:
        """
        Get a specific contact by ID.
        
        :param contact_id: Contact ID
        :return: JSON string with contact data
        """
        result = self._execute_tool("connectwise_get_contact", {"contact_id": contact_id})
        return json.dumps(result, indent=2)

    def get_opportunities(
        self,
        conditions: Optional[str] = None,
        order_by: Optional[str] = None,
        page: int = 1,
        page_size: int = 25
    ) -> str:
        """
        Search and retrieve sales opportunities from ConnectWise.
        
        :param conditions: Filter conditions (e.g., 'status/name="Open"')
        :param order_by: Field to order by
        :param page: Page number (1-based)
        :param page_size: Results per page (max 1000)
        :return: JSON string with opportunity data
        """
        args = {
            "page": page,
            "pageSize": page_size
        }
        if conditions:
            args["conditions"] = conditions
        if order_by:
            args["orderBy"] = order_by
            
        result = self._execute_tool("connectwise_get_opportunities", args)
        return json.dumps(result, indent=2)

    def get_agreements(
        self,
        conditions: Optional[str] = None,
        order_by: Optional[str] = None,
        page: int = 1,
        page_size: int = 25
    ) -> str:
        """
        Search and retrieve agreements/contracts from ConnectWise.
        
        :param conditions: Filter conditions
        :param order_by: Field to order by
        :param page: Page number (1-based)
        :param page_size: Results per page (max 1000)
        :return: JSON string with agreement data
        """
        args = {
            "page": page,
            "pageSize": page_size
        }
        if conditions:
            args["conditions"] = conditions
        if order_by:
            args["orderBy"] = order_by
            
        result = self._execute_tool("connectwise_get_agreements", args)
        return json.dumps(result, indent=2)

    def get_time_entries(
        self,
        conditions: Optional[str] = None,
        order_by: Optional[str] = None,
        page: int = 1,
        page_size: int = 25
    ) -> str:
        """
        Search and retrieve time entries from ConnectWise.
        
        :param conditions: Filter conditions (e.g., 'member/identifier="john" and timeStart > [2024-01-01]')
        :param order_by: Field to order by
        :param page: Page number (1-based)
        :param page_size: Results per page (max 1000)
        :return: JSON string with time entry data
        """
        args = {
            "page": page,
            "pageSize": page_size
        }
        if conditions:
            args["conditions"] = conditions
        if order_by:
            args["orderBy"] = order_by
            
        result = self._execute_tool("connectwise_get_time_entries", args)
        return json.dumps(result, indent=2)

    def get_projects(
        self,
        conditions: Optional[str] = None,
        order_by: Optional[str] = None,
        page: int = 1,
        page_size: int = 25
    ) -> str:
        """
        Search and retrieve projects from ConnectWise.
        
        :param conditions: Filter conditions (e.g., 'status/name="Open"')
        :param order_by: Field to order by
        :param page: Page number (1-based)
        :param page_size: Results per page (max 1000)
        :return: JSON string with project data
        """
        args = {
            "page": page,
            "pageSize": page_size
        }
        if conditions:
            args["conditions"] = conditions
        if order_by:
            args["orderBy"] = order_by
            
        result = self._execute_tool("connectwise_get_projects", args)
        return json.dumps(result, indent=2)

    def get_activities(
        self,
        conditions: Optional[str] = None,
        order_by: Optional[str] = None,
        page: int = 1,
        page_size: int = 25
    ) -> str:
        """
        Search and retrieve activities from ConnectWise.
        
        :param conditions: Filter conditions
        :param order_by: Field to order by
        :param page: Page number (1-based)
        :param page_size: Results per page (max 1000)
        :return: JSON string with activity data
        """
        args = {
            "page": page,
            "pageSize": page_size
        }
        if conditions:
            args["conditions"] = conditions
        if order_by:
            args["orderBy"] = order_by
            
        result = self._execute_tool("connectwise_get_activities", args)
        return json.dumps(result, indent=2)

    def get_members(
        self,
        conditions: Optional[str] = None,
        order_by: Optional[str] = None,
        page: int = 1,
        page_size: int = 25
    ) -> str:
        """
        Search and retrieve team members from ConnectWise.
        
        :param conditions: Filter conditions (e.g., 'inactiveFlag=false')
        :param order_by: Field to order by
        :param page: Page number (1-based)
        :param page_size: Results per page (max 1000)
        :return: JSON string with member data
        """
        args = {
            "page": page,
            "pageSize": page_size
        }
        if conditions:
            args["conditions"] = conditions
        if order_by:
            args["orderBy"] = order_by
            
        result = self._execute_tool("connectwise_get_members", args)
        return json.dumps(result, indent=2)
