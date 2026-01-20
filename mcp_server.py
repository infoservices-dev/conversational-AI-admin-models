"""
MCP Server for ClairAI Backend APIs
"""

import asyncio
import httpx
from mcp.server import Server
from mcp import types
import os

# Configuration
BASE_URL = os.getenv("BACKEND_API_URL", "https://backend.clairai.cloud")
BEARER_TOKEN = os.getenv("BEARER_TOKEN")

app = Server("clairai-admin")

async def get_auth_headers():
  if BEARER_TOKEN:
    return {"Authorization": f"Bearer {BEARER_TOKEN}"}
  return {}

@app.list_tools()
async def list_tools():
  return [
    types.Tool(
            name="get_firing_alerts",
            description="Get currently firing alerts",
            inputSchema={
                "type": "object",
                "properties": {},
            }
        ),
        types.Tool(
            name="get_logging_configs", 
            description="Get logging configurations",
            inputSchema={
                "type": "object",
                "properties": {
                    "client_id": {"type": "string"},
                    "aws_account_id": {"type": "string"}
                },
                "required": ["client_id", "aws_account_id"]
            }
        )
  ]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
  async with httpx.AsyncClient() as client:
        headers = await get_auth_headers()
    
        if name == "get_firing_alerts":
            response = await client.get(
                f"{BASE_URL}/api/v1/alerts/firing-alerts",
                headers=headers
            )
            return [types.TextContent(
                type="text",
                text=response.text
            )]
        elif name == "get_logging_configs":
            client_id = arguments["client_id"]
            aws_account_id = arguments["aws_account_id"]
            response = await client.get(
                f"{BASE_URL}/api/v1/logging/configs/{client_id}/awsid-{aws_account_id}",
                headers=headers
            )
            return [types.TextContent(
                type="text",
                text=response.text
            )]
        
if __name__ == "__main__":
    import mcp.server.stdio
    mcp.server.stdio.run_server(app)