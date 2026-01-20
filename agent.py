from langchain_core.tools import tool
import subprocess
import json

@tool  
def get_firing_alerts() -> dict:

  result = call_mcp_tool("get_firing_alerts", {})
  return result

@tool
def get_logging_configs(client_id: str, aws_account_id: str) -> dict:

  arguments = {
    "client_id": client_id,
    "aws_account_id": aws_account_id
  }
  result = call_mcp_tool("get_logging_configs", arguments)
  return result

def call_mcp_tool(tool_name: str, arguments: dict) -> dict:
  try:
    # Call the MCP server
    cmd = ["python", "mcp_server.py"]

    return {"success": True, "data": "MCP call result"}
  except Exception as e:
    return {"success": False, "error": str(e)}