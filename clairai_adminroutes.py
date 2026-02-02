import os
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
import httpx
import logging

load_dotenv()

# Configuration
BASE_URL = os.getenv("BACKEND_API_URL", "https://backend.clairai.cloud")
BEARER_TOKEN = os.getenv("BEARER_TOKEN")
PORT = int(os.getenv("CLAIRAI_ADMIN_PORT", "8001"))

mcp = FastMCP("clairai-admin", port=PORT, stateless_http=True)

def _get_auth_headers() -> Dict[str, str]:
  if BEARER_TOKEN:
    return {"Authorization": f"Bearer {BEARER_TOKEN}"}
  return {}

async def _request(method: str, path: str, json: Optional[Dict] = None, params: Optional[Dict] = None) -> Dict[str, Any]:
  url = f"{BASE_URL}{path}" if path.startswith("/") else f"{BASE_URL}/{path}"
  headers = _get_auth_headers()
  try:
      async with httpx.AsyncClient(timeout=10) as client:
        response = await client.request(method, url, json=json, params=params, headers=headers)
        status = response.status_code
        try:
          data = response.json()
        except Exception:
          data = response.text
        if 200 <= status < 300:
          return {"success": True, "status": status, "data": data}
        return {"success": False, "status": status, "data": data}
  except Exception as e:
      return {"success": False, "error": str(e)}
  
# --------- Logging Tools ---------

@mcp.tool()
async def get_logging_configs(client_id: str, aws_account_id: str) -> Dict[str, Any]:
    return await _request("GET", f"/api/v1/logging/configs/{client_id}/awsid-{aws_account_id}")

@mcp.tool()
async def onboard_logging_config(client_id: str, aws_account_id: str, source: str, log_selector: List[str]) -> Dict[str, Any]:
    payload = {"client_id": client_id, "aws_account_id": aws_account_id, "source": source, "log_selector": log_selector}
    return await _request("POST", "/api/v1/logging/onboard", json=payload)


@mcp.tool()
async def delete_logging_config(client_id: str, aws_account_id: str, source: str, log_selector: List[str]) -> Dict[str, Any]:
    payload = {"client_id": client_id, "aws_account_id": aws_account_id, "source": source, "log_selector": log_selector}
    # backend uses POST for deboard in some existing code; keep same path/method as original services
    return await _request("POST", "/api/v1/logging/deboard", json=payload)

# --------- Alert Tools ---------
@mcp.tool()
async def get_firing_alerts() -> Dict[str, Any]:
    return await _request("GET", "/api/v1/alerts/firing-alerts")


@mcp.tool()
async def get_datasources() -> Dict[str, Any]:
    return await _request("GET", "/api/v1/alerts/datasources")

@mcp.tool()
async def create_alert(
    title: str,
    severity: str,
    receiver: str,
    description: str,
    datasource: str,
    threshold_value: float,
    for_duration: str = "5m",
    lookback_seconds: int = 600,
    prom_expr: Optional[str] = None,
    log_expr: Optional[str] = None
) -> Dict[str, Any]:
    payload = {
        "title": title,
        "for_duration": for_duration,
        "severity": severity,
        "receiver": receiver,
        "lookback_seconds": lookback_seconds,
        "description": description,
        "datasource": datasource,
        "threshold_value": threshold_value,
        "include_view_data": False,
        "include_dashboard": False,
    }
    if prom_expr:
        payload["prom_expr"] = prom_expr
    if log_expr:
        payload["log_expr"] = log_expr
    return await _request("POST", "/api/v1/alerts/", json=payload)

@mcp.tool()
async def get_all_alerts() -> Dict[str, Any]:
    return await _request("GET", "/api/v1/alerts/get_alerts/")


@mcp.tool()
async def update_alert(alert_id: str, **kwargs) -> Dict[str, Any]:
    return await _request("PUT", f"/api/v1/alerts/update_alerts/{alert_id}", json=kwargs)


@mcp.tool()
async def delete_alert(alert_uid: str) -> Dict[str, Any]:
    return await _request("DELETE", f"/api/v1/alerts/delete_alerts/{alert_uid}")


@mcp.tool()
async def get_specific_alert(alert_id: str) -> Dict[str, Any]:
    return await _request("GET", f"/api/v1/alerts/specific_alerts/{alert_id}")

# --------- Metrics Tools ---------
@mcp.tool()
async def get_metrics_namespaces(account_id: str, region: str, timerange: str) -> Dict[str, Any]:
    params = {"account_id": account_id, "region": region, "timerange": timerange}
    return await _request("GET", "/metrics-namespaces", params=params)


@mcp.tool()
async def get_metrics_metadata(account_id: str, region: str, timerange: str, service: str) -> Dict[str, Any]:
    params = {"account_id": account_id, "region": region, "timerange": timerange, "service": service}
    return await _request("GET", "/metrics-metadata", params=params)


@mcp.tool()
async def create_metric(name: str, namespace: str, account_id: str, region: str, metric_type: str = "gauge", description: Optional[str] = None) -> Dict[str, Any]:
    payload = {"name": name, "namespace": namespace, "account_id": account_id, "region": region, "metric_type": metric_type}
    if description:
        payload["description"] = description
    return await _request("POST", "/api/v1/metrics", json=payload)

@mcp.tool()
async def get_metrics(account_id: str, region: str, namespace: Optional[str] = None, metric_name: Optional[str] = None) -> Dict[str, Any]:
    params = {"account_id": account_id, "region": region}
    if namespace:
        params["namespace"] = namespace
    if metric_name:
        params["metric_name"] = metric_name
    return await _request("GET", "/api/v1/metrics", params=params)

@mcp.tool()
async def update_metric(metric_id: str, name: Optional[str] = None, description: Optional[str] = None, metric_type: Optional[str] = None) -> Dict[str, Any]:
    payload = {}
    if name:
        payload["name"] = name
    if description:
        payload["description"] = description
    if metric_type:
        payload["metric_type"] = metric_type
    return await _request("PUT", f"/api/v1/metrics/{metric_id}", json=payload)


@mcp.tool()
async def delete_metric(metric_id: str) -> Dict[str, Any]:
    return await _request("DELETE", f"/api/v1/metrics/{metric_id}")


@mcp.tool()
async def get_metric_by_id(metric_id: str) -> Dict[str, Any]:
    return await _request("GET", f"/api/v1/metrics/{metric_id}")


if __name__ == "__main__":
    print(f"Starting ClairAI MCP server on port {PORT}...")
    mcp.run(transport="streamable-http")