"""
title: ConnectWise Tools
description: Read-only access to ConnectWise Manage via MCP
author: AI Assistant
version: 1.1.0
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

    # IT Asset Management
    def get_configurations(
        self,
        conditions: Optional[str] = None,
        order_by: Optional[str] = None,
        page: int = 1,
        page_size: int = 25
    ) -> str:
        """
        Search and retrieve IT configurations/assets from ConnectWise.

        :param conditions: Filter conditions (e.g., 'company/identifier="ACME"' or 'type/name="Server"')
        :param order_by: Field to order by
        :param page: Page number (1-based)
        :param page_size: Results per page (max 1000)
        :return: JSON string with configuration data
        """
        args = {
            "page": page,
            "pageSize": page_size
        }
        if conditions:
            args["conditions"] = conditions
        if order_by:
            args["orderBy"] = order_by

        result = self._execute_tool("connectwise_get_configurations", args)
        return json.dumps(result, indent=2)

    def get_configuration(self, configuration_id: int) -> str:
        """
        Get a specific configuration/asset by ID.

        :param configuration_id: Configuration ID
        :return: JSON string with configuration data
        """
        result = self._execute_tool("connectwise_get_configuration", {"configuration_id": configuration_id})
        return json.dumps(result, indent=2)

    def get_configuration_types(
        self,
        conditions: Optional[str] = None,
        page: int = 1,
        page_size: int = 100
    ) -> str:
        """
        Get all configuration types for categorizing IT assets.

        :param conditions: Filter conditions
        :param page: Page number (1-based)
        :param page_size: Results per page (max 1000)
        :return: JSON string with configuration type data
        """
        args = {
            "page": page,
            "pageSize": page_size
        }
        if conditions:
            args["conditions"] = conditions

        result = self._execute_tool("connectwise_get_configuration_types", args)
        return json.dumps(result, indent=2)

    def get_company_sites(
        self,
        company_id: int,
        page: int = 1,
        page_size: int = 25
    ) -> str:
        """
        Get sites/locations for a specific company.

        :param company_id: Company ID
        :param page: Page number (1-based)
        :param page_size: Results per page (max 1000)
        :return: JSON string with company site data
        """
        args = {
            "company_id": company_id,
            "page": page,
            "pageSize": page_size
        }

        result = self._execute_tool("connectwise_get_company_sites", args)
        return json.dumps(result, indent=2)

    # Reference Data - Company
    def get_company_types(
        self,
        conditions: Optional[str] = None,
        page: int = 1,
        page_size: int = 100
    ) -> str:
        """
        Get all company types for categorizing companies.

        :param conditions: Filter conditions
        :param page: Page number (1-based)
        :param page_size: Results per page (max 1000)
        :return: JSON string with company type data
        """
        args = {
            "page": page,
            "pageSize": page_size
        }
        if conditions:
            args["conditions"] = conditions

        result = self._execute_tool("connectwise_get_company_types", args)
        return json.dumps(result, indent=2)

    def get_company_statuses(
        self,
        conditions: Optional[str] = None,
        page: int = 1,
        page_size: int = 100
    ) -> str:
        """
        Get all company statuses for tracking company state.

        :param conditions: Filter conditions
        :param page: Page number (1-based)
        :param page_size: Results per page (max 1000)
        :return: JSON string with company status data
        """
        args = {
            "page": page,
            "pageSize": page_size
        }
        if conditions:
            args["conditions"] = conditions

        result = self._execute_tool("connectwise_get_company_statuses", args)
        return json.dumps(result, indent=2)

    # Reference Data - Tickets
    def get_ticket_priorities(
        self,
        conditions: Optional[str] = None,
        page: int = 1,
        page_size: int = 100
    ) -> str:
        """
        Get all ticket priorities for categorizing urgency.

        :param conditions: Filter conditions
        :param page: Page number (1-based)
        :param page_size: Results per page (max 1000)
        :return: JSON string with ticket priority data
        """
        args = {
            "page": page,
            "pageSize": page_size
        }
        if conditions:
            args["conditions"] = conditions

        result = self._execute_tool("connectwise_get_ticket_priorities", args)
        return json.dumps(result, indent=2)

    def get_ticket_sources(
        self,
        conditions: Optional[str] = None,
        page: int = 1,
        page_size: int = 100
    ) -> str:
        """
        Get all ticket sources for tracking how tickets are created.

        :param conditions: Filter conditions
        :param page: Page number (1-based)
        :param page_size: Results per page (max 1000)
        :return: JSON string with ticket source data
        """
        args = {
            "page": page,
            "pageSize": page_size
        }
        if conditions:
            args["conditions"] = conditions

        result = self._execute_tool("connectwise_get_ticket_sources", args)
        return json.dumps(result, indent=2)

    # Reference Data - Contacts
    def get_contact_types(
        self,
        conditions: Optional[str] = None,
        page: int = 1,
        page_size: int = 100
    ) -> str:
        """
        Get all contact types for categorizing contacts.

        :param conditions: Filter conditions
        :param page: Page number (1-based)
        :param page_size: Results per page (max 1000)
        :return: JSON string with contact type data
        """
        args = {
            "page": page,
            "pageSize": page_size
        }
        if conditions:
            args["conditions"] = conditions

        result = self._execute_tool("connectwise_get_contact_types", args)
        return json.dumps(result, indent=2)

    # Finance & Billing
    def get_invoices(
        self,
        conditions: Optional[str] = None,
        order_by: Optional[str] = None,
        page: int = 1,
        page_size: int = 25
    ) -> str:
        """
        Search and retrieve invoices from ConnectWise.

        :param conditions: Filter conditions (e.g., 'company/identifier="ACME"' or 'status="Open"')
        :param order_by: Field to order by
        :param page: Page number (1-based)
        :param page_size: Results per page (max 1000)
        :return: JSON string with invoice data
        """
        args = {
            "page": page,
            "pageSize": page_size
        }
        if conditions:
            args["conditions"] = conditions
        if order_by:
            args["orderBy"] = order_by

        result = self._execute_tool("connectwise_get_invoices", args)
        return json.dumps(result, indent=2)

    def get_expense_entries(
        self,
        conditions: Optional[str] = None,
        order_by: Optional[str] = None,
        page: int = 1,
        page_size: int = 25
    ) -> str:
        """
        Search and retrieve expense entries from ConnectWise.

        :param conditions: Filter conditions (e.g., 'member/identifier="john" and date > [2024-01-01]')
        :param order_by: Field to order by
        :param page: Page number (1-based)
        :param page_size: Results per page (max 1000)
        :return: JSON string with expense entry data
        """
        args = {
            "page": page,
            "pageSize": page_size
        }
        if conditions:
            args["conditions"] = conditions
        if order_by:
            args["orderBy"] = order_by

        result = self._execute_tool("connectwise_get_expense_entries", args)
        return json.dumps(result, indent=2)

    def get_billing_cycles(
        self,
        conditions: Optional[str] = None,
        page: int = 1,
        page_size: int = 100
    ) -> str:
        """
        Get all billing cycles for recurring billing.

        :param conditions: Filter conditions
        :param page: Page number (1-based)
        :param page_size: Results per page (max 1000)
        :return: JSON string with billing cycle data
        """
        args = {
            "page": page,
            "pageSize": page_size
        }
        if conditions:
            args["conditions"] = conditions

        result = self._execute_tool("connectwise_get_billing_cycles", args)
        return json.dumps(result, indent=2)

    def get_agreement_additions(
        self,
        agreement_id: int,
        page: int = 1,
        page_size: int = 25
    ) -> str:
        """
        Get additions/add-ons for a specific agreement.

        :param agreement_id: Agreement ID
        :param page: Page number (1-based)
        :param page_size: Results per page (max 1000)
        :return: JSON string with agreement addition data
        """
        args = {
            "agreement_id": agreement_id,
            "page": page,
            "pageSize": page_size
        }

        result = self._execute_tool("connectwise_get_agreement_additions", args)
        return json.dumps(result, indent=2)

    # Service Desk Enhancements
    def get_service_boards(
        self,
        conditions: Optional[str] = None,
        page: int = 1,
        page_size: int = 100
    ) -> str:
        """
        Get all service boards for organizing tickets.

        :param conditions: Filter conditions
        :param page: Page number (1-based)
        :param page_size: Results per page (max 1000)
        :return: JSON string with service board data
        """
        args = {
            "page": page,
            "pageSize": page_size
        }
        if conditions:
            args["conditions"] = conditions

        result = self._execute_tool("connectwise_get_service_boards", args)
        return json.dumps(result, indent=2)

    def get_board_statuses(
        self,
        board_id: int,
        page: int = 1,
        page_size: int = 100
    ) -> str:
        """
        Get all statuses for a specific service board.

        :param board_id: Board ID
        :param page: Page number (1-based)
        :param page_size: Results per page (max 1000)
        :return: JSON string with board status data
        """
        args = {
            "board_id": board_id,
            "page": page,
            "pageSize": page_size
        }

        result = self._execute_tool("connectwise_get_board_statuses", args)
        return json.dumps(result, indent=2)

    def get_ticket_tasks(
        self,
        ticket_id: int,
        page: int = 1,
        page_size: int = 25
    ) -> str:
        """
        Get tasks/checklist items for a specific ticket.

        :param ticket_id: Ticket ID
        :param page: Page number (1-based)
        :param page_size: Results per page (max 1000)
        :return: JSON string with ticket task data
        """
        args = {
            "ticket_id": ticket_id,
            "page": page,
            "pageSize": page_size
        }

        result = self._execute_tool("connectwise_get_ticket_tasks", args)
        return json.dumps(result, indent=2)

    def get_ticket_schedules(
        self,
        ticket_id: int,
        page: int = 1,
        page_size: int = 25
    ) -> str:
        """
        Get schedule entries for a specific ticket.

        :param ticket_id: Ticket ID
        :param page: Page number (1-based)
        :param page_size: Results per page (max 1000)
        :return: JSON string with ticket schedule data
        """
        args = {
            "ticket_id": ticket_id,
            "page": page,
            "pageSize": page_size
        }

        result = self._execute_tool("connectwise_get_ticket_schedules", args)
        return json.dumps(result, indent=2)
