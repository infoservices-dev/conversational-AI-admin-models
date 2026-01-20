"""
LangGraph Conversational Agent for Backend APIs with AWS Bedrock
Complete implementation using Amazon Bedrock for LLM inference
"""

from typing import TypedDict, Annotated, Literal
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_aws import ChatBedrock
import requests
import os

# Configuration
BASE_URL = os.getenv("BACKEND_API_URL", "https://backend.clairai.cloud")

# AWS Bedrock Configuration
AWS_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

# Add bearer token support
BEARER_TOKEN = os.getenv("BEARER_TOKEN") 

def get_auth_headers():
    if BEARER_TOKEN:
        return {"Authorization": f"Bearer {BEARER_TOKEN}"}
    return {}    

# STEP 1: DEFINE STATE SCHEMA
class AgentState(TypedDict):
    """
    State schema for the conversational agent.
    - messages: Conversation history with add_messages reducer
    - user_context: User-specific data like client_id, aws_account_id
    - api_results: Store results from API calls
    """
    messages: Annotated[list[BaseMessage], add_messages]
    user_context: dict
    api_results: dict

# STEP 2: CREATE TOOL DEFINITIONS FOR EACH API ENDPOINT

# LOGGING TOOLS 
@tool
def onboard_logging_config(
    client_id: str,
    aws_account_id: str,
    source: str,
    log_selector: list[str]
) -> dict:
    """
    Onboard a new logging configuration for a specific client and AWS account.
    Use this when user wants to set up or configure logging.
    
    Args:
        client_id: The client identifier
        aws_account_id: AWS account ID
        source: Source of the logs
        log_selector: List of log selectors
    """
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/logging/onboard",
            json={
                "client_id": client_id,
                "aws_account_id": aws_account_id,
                "source": source,
                "log_selector": log_selector
            },
            timeout=10
        )
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def get_logging_configs(client_id: str, aws_account_id: str) -> dict:
    """
    Retrieve all logging configurations for a specific client and AWS account.
    Use this when user asks about their logging setup or configurations.
    
    Args:
        client_id: The client identifier
        aws_account_id: AWS account ID
    """
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/logging/configs/{client_id}/awsid-{aws_account_id}",
            headers=get_auth_headers(),
            timeout=10
        )
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def delete_logging_config(
    client_id: str,
    aws_account_id: str,
    source: str,
    log_selector: list[str]
) -> dict:
    """
    Delete logging configurations and deboard a log group.
    Use this when user wants to remove or disable logging.
    
    Args:
        client_id: The client identifier
        aws_account_id: AWS account ID
        source: Source of the logs
        log_selector: List of log selectors to remove
    """
    try:
        response = requests.delete(
            f"{BASE_URL}/api/v1/logging/deboard",
            json={
                "client_id": client_id,
                "aws_account_id": aws_account_id,
                "source": source,
                "log_selector": log_selector
            },
            timeout=10
        )
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ALERT TOOLS 
@tool
def get_firing_alerts() -> dict:
    """
    Fetch all currently firing alerts from Grafana dashboard.
    Use this when user asks about current alerts, active alerts, or what's firing.
    """
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/alerts/firing-alerts",
            headers=get_auth_headers(),
            timeout=10
        )
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def get_datasources() -> dict:
    """
    Fetch all Grafana data sources (Prometheus, Loki, etc.) configured in the workspace.
    Use this when user asks about available data sources or monitoring systems.
    """
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/alerts/datasources",
            timeout=10
        )
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def create_alert(
    title: str,
    severity: str,
    receiver: str,
    description: str,
    datasource: str,
    threshold_value: float,
    for_duration: str = "5m",
    lookback_seconds: int = 600,
    prom_expr: str = None,
    log_expr: str = None
) -> dict:
    """
    Create a new alert rule in Grafana using metrics, logs, or both.
    Use this when user wants to set up a new alert or monitoring rule.
    
    Args:
        title: Alert title
        severity: Alert severity (e.g., 'critical', 'warning', 'info')
        receiver: Alert receiver/notification channel
        description: Alert description
        datasource: Data source to use (e.g., 'prometheus', 'loki')
        threshold_value: Threshold value for the alert
        for_duration: How long condition must be true (default: '5m')
        lookback_seconds: Lookback window in seconds (default: 600)
        prom_expr: Prometheus query expression (optional)
        log_expr: Loki log query expression (optional)
    """
    try:
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
            "include_dashboard": False
        }
        
        if prom_expr:
            payload["prom_expr"] = prom_expr
        if log_expr:
            payload["log_expr"] = log_expr
        
        response = requests.post(
            f"{BASE_URL}/api/v1/alerts/",
            json=payload,
            timeout=10
        )
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def get_all_alerts() -> dict:
    """
    Retrieve a list of all alert rules stored in the system.
    Use this when user asks to see all alerts or list alert configurations.
    """
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/alerts/get_alerts/",
            timeout=10
        )
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def update_alert(alert_id: str, **kwargs) -> dict:
    """
    Update an existing alert rule by its ID.
    Use this when user wants to modify an existing alert.
    
    Args:
        alert_id: The alert ID to update
        **kwargs: Fields to update (title, severity, threshold_value, etc.)
    """
    try:
        response = requests.put(
            f"{BASE_URL}/api/v1/alerts/update_alerts/{alert_id}",
            json=kwargs,
            timeout=10
        )
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def delete_alert(alert_uid: str) -> dict:
    """
    Delete an alert rule by its UID.
    Use this when user wants to remove an alert.
    
    Args:
        alert_uid: The unique identifier of the alert to delete
    """
    try:
        response = requests.delete(
            f"{BASE_URL}/api/v1/alerts/delete_alerts/{alert_uid}",
            timeout=10
        )
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def get_specific_alert(alert_id: str) -> dict:
    """
    Get details of a specific alert by its ID.
    Use this when user asks about a particular alert's details.
    
    Args:
        alert_id: The alert ID to retrieve
    """
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/alerts/specific_alerts/{alert_id}",
            timeout=10
        )
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ---------- METRICS TOOLS ----------
@tool
def get_metrics_namespaces(account_id: str, region: str, timerange: str) -> dict:
    """
    Get metrics namespaces for an AWS account.
    Use this when user asks about available metrics or namespaces.
    
    Args:
        account_id: AWS account ID
        region: AWS region (e.g., 'us-east-1')
        timerange: Time range for metrics (e.g., '1h', '24h')
    """
    try:
        response = requests.get(
            f"{BASE_URL}/metrics-namespaces",
            params={
                "account_id": account_id,
                "region": region,
                "timerange": timerange
            },
            timeout=10
        )
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
def get_metrics_metadata(
    account_id: str,
    region: str,
    timerange: str,
    service: str
) -> dict:
    """
    Get metrics metadata for a specific AWS service.
    Use this when user asks about metrics for a particular service.
    
    Args:
        account_id: AWS account ID
        region: AWS region (e.g., 'us-east-1')
        timerange: Time range for metrics (e.g., '1h', '24h')
        service: AWS service name (e.g., 'EC2', 'RDS')
    """
    try:
        response = requests.get(
            f"{BASE_URL}/metrics-metadata",
            params={
                "account_id": account_id,
                "region": region,
                "timerange": timerange,
                "service": service
            },
            timeout=10
        )
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except Exception as e:
        return {"success": False, "error": str(e)}
# STEP 3: BUILD THE GRAPH

# Collect all tools
all_tools = [
    # Logging tools
    onboard_logging_config,
    get_logging_configs,
    delete_logging_config,
    # Alert tools
    get_firing_alerts,
    get_datasources,
    create_alert,
    get_all_alerts,
    update_alert,
    delete_alert,
    get_specific_alert,
    # Metrics tools
    get_metrics_namespaces,
    get_metrics_metadata,
]
