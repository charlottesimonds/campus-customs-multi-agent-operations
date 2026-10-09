"""Campus Customs MCP server.

Run from the Homework 5 folder with:  python -m mcp_server.server
"""

from fastmcp import FastMCP

from .tools import register_all

mcp = FastMCP(
    name="campus-customs",
    instructions=(
        "Tools for the Campus Customs shop agents. All data comes from the working "
        "database data/campus_customs_new.db. The shop's current date is desk.date_today. "
        "Report only what the tools return; never fill in missing data."
    ),
)
register_all(mcp)


if __name__ == "__main__":
    mcp.run()
