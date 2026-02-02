
import os
import json
import logging
from typing import Any, Dict, Optional, List
import requests
from langchain_core.tools import tool
from uuid import uuid4


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("clairai-toolcalling")

# Config
MCP_ENDPOINT = os.getenv("MCP_ENDPOINT", "http://localhost:8001/mcp")
BACKEND_BASE = os.getenv("BACKEND_API_URL", "https://backend.clairai.cloud")
BEARER_TOKEN = os.getenv("BEARER_TOKEN")

# Common headers for backend calls (not for MCP)
def _backend_auth_headers() -> Dict[str, str]:
    if BEARER_TOKEN:
      return {"Authorization": f"Bearer {BEARER_TOKEN}"}
    return {}

# ---- MCP JSON-RPC caller (sync) ----
def call_mcp_tool(tool_name: str, arguments: dict, timeout: int = 30, try_stream: bool = True) -> Dict[str, Any]:
    """
    Call an MCP tool via JSON-RPC.
    - Attempts streaming SSE if `try_stream` is True (Accept: text/event-stream + stream=True).
    - Falls back to a plain POST if streaming/parse fails.
    Returns a dict: {success: bool, status: int|None, data: Any|None, error: str|None}
    """
    payload = {
        "jsonrpc": "2.0",
        "id": str(uuid4()),
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments}
    }
    # Try SSE streaming first (FastMCP streamable-http expects Accept: text/event-stream)
    if try_stream:
        headers = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
        try:
            resp = requests.post(MCP_ENDPOINT, json=payload, headers=headers, stream=True, timeout=timeout)
        except Exception as e:
            logger.debug("Stream POST failed, will fallback: %s", e)
            resp = None

        if resp is not None:
            status = getattr(resp, "status_code", None)
            if status == 200:
                # Parse SSE stream minimally: collect 'data:' lines
                try:
                    data_chunks: List[str] = []
                    for raw in resp.iter_lines(decode_unicode=True):
                        if not raw:
                            continue
                        line = raw.strip()
                        # SSE `data: ` lines
                        if line.startswith("data:"):
                            data_payload = line[len("data:"):].strip()
                            data_chunks.append(data_payload)
                            # Keep reading until stream ends; but stop if final JSON is received
                            # Some MCP streams send a single data chunk; break after receiving one well-formed JSON
                            try:
                                parsed = json.loads(data_payload)
                                return {"success": True, "status": status, "data": parsed, "error": None}
                            except Exception:
                                # not JSON yet; continue collecting
                                continue
                    # If we collected chunks but couldn't parse, return concatenated string
                    if data_chunks:
                        joined = "\n".join(data_chunks)
                        try:
                            parsed = json.loads(joined)
                            return {"success": True, "status": status, "data": parsed, "error": None}
                        except Exception:
                            return {"success": True, "status": status, "data": joined, "error": None}
                    # Empty stream
                    return {"success": False, "status": status, "data": None, "error": "Empty SSE stream"}
                except Exception as e:
                    logger.debug("Error parsing SSE stream: %s", e)
                    # fall through to fallback POST
            else:
                # Non-200 streaming response; fall back to standard POST below
                logger.debug("SSE response status %s, falling back", status)
    # Fallback: standard POST (non-stream)
    try:
        headers = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
        # include proxy auth token if provided
        
        resp = requests.post(MCP_ENDPOINT, json=payload, headers=headers, timeout=timeout)
        status = resp.status_code
        try:
            data = resp.json()
        except Exception:
            data = resp.text
        if 200 <= status < 300:
            return {"success": True, "status": status, "data": data, "error": None}
        return {"success": False, "status": status, "data": data, "error": f"HTTP {status}"}
    except Exception as e:
        return {"success": False, "status": None, "data": None, "error": str(e)}
    
# ---- Tools that call MCP (alerts & logging) ----
@tool
def get_firing_alerts() -> dict:
    """Fetch currently firing alerts via MCP."""
    return call_mcp_tool("get_firing_alerts", {})

@tool
def get_datasources() -> dict:
    """Fetch Grafana data sources via MCP."""
    return call_mcp_tool("get_datasources", {})
@tool
def create_alert(title: str, severity: str, receiver: str, description: str, datasource: str, threshold_value: float) -> dict:
    """Create a Grafana alert via MCP."""
    args = {
        "title": title,
        "severity": severity,
        "receiver": receiver,
        "description": description,
        "datasource": datasource,
        "threshold_value": threshold_value
    }
    return call_mcp_tool("create_alert", args)

@tool
def get_all_alerts() -> dict:
    """Retrieve all alert rules via MCP."""
    return call_mcp_tool("get_all_alerts", {})

@tool
def delete_alert(alert_uid: str) -> dict:
    """Delete an alert by UID via MCP."""
    return call_mcp_tool("delete_alert", {"alert_uid": alert_uid})

@tool
def get_specific_alert(alert_id: str) -> dict:
    """Get details for a specific alert via MCP."""
    return call_mcp_tool("get_specific_alert", {"alert_id": alert_id})

@tool
def get_logging_configs(client_id: str, aws_account_id: str) -> dict:
    """Get logging configs for a client and AWS account via MCP."""
    return call_mcp_tool("get_logging_configs", {"client_id": client_id, "aws_account_id": aws_account_id})
@tool
def onboard_logging_config(client_id: str, aws_account_id: str, source: str, log_selector: List[str]) -> dict:
    """Onboard a logging configuration via MCP."""
    return call_mcp_tool("onboard_logging_config", {"client_id": client_id, "aws_account_id": aws_account_id, "source": source, "log_selector": log_selector})

@tool
def delete_logging_config(client_id: str, aws_account_id: str, source: str, log_selector: List[str]) -> dict:
    """Deboard / remove a logging configuration via MCP."""
    return call_mcp_tool("delete_logging_config", {"client_id": client_id, "aws_account_id": aws_account_id, "source": source, "log_selector": log_selector})

# ---- Direct backend metrics CRUD (reuse patterns from metrics-crud.py) ----
def _backend_request(method: str, path: str, json_payload: Optional[dict] = None, params: Optional[dict] = None, timeout: int = 10) -> Dict[str, Any]:
    url = BACKEND_BASE.rstrip("/") + "/" + path.lstrip("/")
    headers = _backend_auth_headers()
    try:
        resp = requests.request(method, url, json=json_payload, params=params, headers=headers, timeout=timeout)
        status = resp.status_code
        try:
            data = resp.json()
        except Exception:
            data = resp.text
        if 200 <= status < 300:
            return {"success": True, "status": status, "data": data, "error": None}
        return {"success": False, "status": status, "data": data, "error": f"HTTP {status}"}
    except Exception as e:
        return {"success": False, "status": None, "data": None, "error": str(e)}

@tool
def create_metric(name: str, namespace: str, account_id: str, region: str, metric_type: str = "gauge", description: Optional[str] = None) -> dict:
    """Create a metric definition in the backend."""
    payload = {"name": name, "namespace": namespace, "account_id": account_id, "region": region, "metric_type": metric_type}
    if description:
        payload["description"] = description
    return _backend_request("POST", "/api/v1/metrics", json_payload=payload)

@tool
def get_metrics(account_id: str, region: str, namespace: Optional[str] = None, metric_name: Optional[str] = None) -> dict:
    """Retrieve metrics from the backend (filters supported)."""
    params = {"account_id": account_id, "region": region}
    if namespace:
        params["namespace"] = namespace
    if metric_name:
        params["metric_name"] = metric_name
    return _backend_request("GET", "/api/v1/metrics", params=params)

@tool
def update_metric(metric_id: str, name: Optional[str] = None, description: Optional[str] = None, metric_type: Optional[str] = None) -> dict:
    """Update an existing metric by ID in the backend."""
    payload = {}
    if name:
        payload["name"] = name
    if description:
        payload["description"] = description
    if metric_type:
        payload["metric_type"] = metric_type
    return _backend_request("PUT", f"/api/v1/metrics/{metric_id}", json_payload=payload)
@tool
def delete_metric(metric_id: str) -> dict:
    """Delete a metric by ID in the backend."""
    return _backend_request("DELETE", f"/api/v1/metrics/{metric_id}")

@tool
def get_metric_by_id(metric_id: str) -> dict:
    """Retrieve a metric by ID from the backend."""
    return _backend_request("GET", f"/api/v1/metrics/{metric_id}")

# ---- Quick CLI test helpers ----
if __name__ == "__main__":
    print("Testing MCP call (stream-first with fallback)...")
    print("MCP_ENDPOINT =", MCP_ENDPOINT)
    print("Calling get_firing_alerts()")
    print(get_firing_alerts.invoke({}))  # direct call returns dict
    print("\nTesting backend metrics list (direct backend call)...")
    print(get_metrics.invoke({"account_id": "test-account", "region": "us-east-1"}))