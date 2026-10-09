"""Tool modules for the Campus Customs MCP server.

To add tools: create a module here with a register(mcp) function and add it
to TOOL_MODULES.
"""

from fastmcp import FastMCP

from . import inventory, invoices, leases, maintenance, payments, tickets

TOOL_MODULES = [tickets, inventory, invoices, leases, payments, maintenance]


def register_all(mcp: FastMCP) -> None:
    for module in TOOL_MODULES:
        module.register(mcp)
