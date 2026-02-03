import json
import logging
import uuid
from datetime import datetime
from typing import Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from config import settings
from tools import (
    onboard_logging_config,
    get_logging_configs,
    delete_logging_config,
    get_firing_alerts,
    get_datasources,
    create_alert,
    get_all_alerts,
    update_alert,
    delete_alert,
    get_specific_alert,
    get_metrics_namespaces,
    get_metrics_metadata,
)
from tools.base import set_request_token

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format=settings.log_format
)
logger = logging.getLogger(__name__)


def extract_bearer_token(request: Request) -> str | None:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    return None


class MCPRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: str | int | None = None
    method: str
    params: dict[str, Any] | None = None


class MCPResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: str | int | None = None
    result: Any | None = None
    error: dict[str, Any] | None = None


class ToolDefinition(BaseModel):
    name: str
    description: str
    inputSchema: dict[str, Any]


class ServerInfo(BaseModel):
    name: str = settings.server_name
    version: str = settings.server_version
    protocolVersion: str = "2024-11-05"


TOOLS: dict[str, dict[str, Any]] = {
    "onboard_logging_config": {
        "function": onboard_logging_config,
        "description": "Onboard a new logging configuration for a specific client and AWS account. Use when setting up or configuring logging.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "client_id": {"type": "string", "description": "The client identifier"},
                "aws_account_id": {"type": "string", "description": "AWS account ID"},
                "source": {"type": "string", "description": "Source of the logs"},
                "log_selector": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of log selectors"
                }
            },
            "required": ["client_id", "aws_account_id", "source", "log_selector"]
        }
    },
    "get_logging_configs": {
        "function": get_logging_configs,
        "description": "Retrieve all logging configurations for a specific client and AWS account. Use when asking about logging setup.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "client_id": {"type": "string", "description": "The client identifier"},
                "aws_account_id": {"type": "string", "description": "AWS account ID"}
            },
            "required": ["client_id", "aws_account_id"]
        }
    },
    "delete_logging_config": {
        "function": delete_logging_config,
        "description": "Delete logging configurations and deboard a log group. Use when removing or disabling logging.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "client_id": {"type": "string", "description": "The client identifier"},
                "aws_account_id": {"type": "string", "description": "AWS account ID"},
                "source": {"type": "string", "description": "Source of the logs"},
                "log_selector": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of log selectors to remove"
                }
            },
            "required": ["client_id", "aws_account_id", "source", "log_selector"]
        }
    },
    "get_firing_alerts": {
        "function": get_firing_alerts,
        "description": "Fetch all currently firing alerts from Grafana dashboard. Use when asking about current or active alerts.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    "get_datasources": {
        "function": get_datasources,
        "description": "Fetch all Grafana data sources (Prometheus, Loki, etc.) configured in the workspace. Use when asking about available data sources.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    "create_alert": {
        "function": create_alert,
        "description": "Create a new alert rule in Grafana using metrics, logs, or both. Use when setting up a new alert or monitoring rule.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Alert title"},
                "severity": {"type": "string", "enum": ["critical", "warning", "info"], "description": "Alert severity"},
                "receiver": {"type": "string", "description": "Alert receiver/notification channel"},
                "description": {"type": "string", "description": "Alert description"},
                "datasource": {"type": "string", "description": "Data source (prometheus, loki)"},
                "threshold_value": {"type": "number", "description": "Threshold value for the alert"},
                "for_duration": {"type": "string", "default": "5m", "description": "How long condition must be true"},
                "lookback_seconds": {"type": "integer", "default": 600, "description": "Lookback window in seconds"},
                "prom_expr": {"type": "string", "description": "Prometheus query expression (optional)"},
                "log_expr": {"type": "string", "description": "Loki log query expression (optional)"}
            },
            "required": ["title", "severity", "receiver", "description", "datasource", "threshold_value"]
        }
    },
    "get_all_alerts": {
        "function": get_all_alerts,
        "description": "Retrieve a list of all alert rules stored in the system. Use when listing all alerts.",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    "update_alert": {
        "function": update_alert,
        "description": "Update an existing alert rule by its ID. Use when modifying an existing alert.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "alert_id": {"type": "string", "description": "The alert ID to update"},
                "title": {"type": "string", "description": "New alert title"},
                "severity": {"type": "string", "enum": ["critical", "warning", "info"], "description": "New severity"},
                "receiver": {"type": "string", "description": "New receiver"},
                "description": {"type": "string", "description": "New description"},
                "datasource": {"type": "string", "description": "New datasource"},
                "threshold_value": {"type": "number", "description": "New threshold"},
                "for_duration": {"type": "string", "description": "New duration"},
                "lookback_seconds": {"type": "integer", "description": "New lookback"},
                "prom_expr": {"type": "string", "description": "New Prometheus expression"},
                "log_expr": {"type": "string", "description": "New Loki expression"}
            },
            "required": ["alert_id"]
        }
    },
    "delete_alert": {
        "function": delete_alert,
        "description": "Delete an alert rule by its UID. Use when removing an alert.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "alert_uid": {"type": "string", "description": "The unique identifier of the alert to delete"}
            },
            "required": ["alert_uid"]
        }
    },
    "get_specific_alert": {
        "function": get_specific_alert,
        "description": "Get details of a specific alert by its ID. Use when asking about a particular alert.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "alert_id": {"type": "string", "description": "The alert ID to retrieve"}
            },
            "required": ["alert_id"]
        }
    },
    "get_metrics_namespaces": {
        "function": get_metrics_namespaces,
        "description": "Get metrics namespaces for an AWS account. Use when asking about available metrics or namespaces.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "description": "AWS account ID"},
                "region": {"type": "string", "description": "AWS region (e.g., us-east-1)"},
                "timerange": {"type": "string", "description": "Time range (e.g., 1h, 24h)"}
            },
            "required": ["account_id", "region", "timerange"]
        }
    },
    "get_metrics_metadata": {
        "function": get_metrics_metadata,
        "description": "Get metrics metadata for a specific AWS service. Use when asking about metrics for a particular service.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "description": "AWS account ID"},
                "region": {"type": "string", "description": "AWS region (e.g., us-east-1)"},
                "timerange": {"type": "string", "description": "Time range (e.g., 1h, 24h)"},
                "service": {"type": "string", "description": "AWS service name (e.g., EC2, RDS)"}
            },
            "required": ["account_id", "region", "timerange", "service"]
        }
    }
}


class SessionManager:
    def __init__(self):
        self.sessions: dict[str, dict[str, Any]] = {}
    
    def create_session(self, token: str | None = None) -> str:
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "initialized": False,
            "client_info": None,
            "token": token
        }
        logger.info(f"Created session: {session_id}")
        return session_id
    
    def get_session(self, session_id: str) -> dict[str, Any] | None:
        return self.sessions.get(session_id)
    
    def update_session(self, session_id: str, **kwargs):
        if session_id in self.sessions:
            self.sessions[session_id].update(kwargs)
            self.sessions[session_id]["last_activity"] = datetime.utcnow().isoformat()
    
    def delete_session(self, session_id: str):
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Deleted session: {session_id}")


session_manager = SessionManager()


async def handle_initialize(params: dict[str, Any] | None) -> dict[str, Any]:
    return {
        "protocolVersion": "2026-02-02",
        "capabilities": {
            "tools": {"listChanged": True},
            "resources": {"subscribe": False, "listChanged": False},
            "prompts": {"listChanged": False}
        },
        "serverInfo": {
            "name": settings.server_name,
            "version": settings.server_version
        }
    }


async def handle_list_tools() -> dict[str, Any]:
    tools = [
        {
            "name": name,
            "description": info["description"],
            "inputSchema": info["inputSchema"]
        }
        for name, info in TOOLS.items()
    ]
    return {"tools": tools}


async def handle_call_tool(params: dict[str, Any]) -> dict[str, Any]:
    tool_name = params.get("name")
    arguments = params.get("arguments", {})
    
    if tool_name not in TOOLS:
        raise ValueError(f"Unknown tool: {tool_name}")
    
    tool_info = TOOLS[tool_name]
    tool_func = tool_info["function"]
    
    logger.info(f"Calling tool: {tool_name} with args: {arguments}")
    
    try:
        result = await tool_func(**arguments)
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, indent=2, default=str)
                }
            ],
            "isError": not result.get("success", True)
        }
    except Exception as e:
        logger.exception(f"Tool execution failed: {tool_name}")
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({"error": str(e)}, indent=2)
                }
            ],
            "isError": True
        }


async def handle_list_resources() -> dict[str, Any]:
    return {"resources": []}


async def handle_list_prompts() -> dict[str, Any]:
    return {"prompts": []}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.server_name} v{settings.server_version}")
    logger.info(f"Backend API: {settings.backend_api_url}")
    logger.info(f"Listening on {settings.host}:{settings.port}")
    yield
    logger.info("Shutting down MCP server")


app = FastAPI(
    title=settings.server_name,
    version=settings.server_version,
    description="Production-grade MCP Server for ClairAI Admin APIs",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "server": settings.server_name,
        "version": settings.server_version,
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/info")
async def server_info():
    return {
        "name": settings.server_name,
        "version": settings.server_version,
        "protocolVersion": "2024-11-05",
        "tools_count": len(TOOLS),
        "tools": list(TOOLS.keys())
    }


@app.post("/mcp")
async def mcp_endpoint(request: Request):
    token = extract_bearer_token(request)
    set_request_token(token)
    
    try:
        body = await request.json()
        
        if isinstance(body, list):
            responses = []
            for req in body:
                resp = await process_mcp_request(req)
                if resp:
                    responses.append(resp)
            return JSONResponse(content=responses)
        
        response = await process_mcp_request(body)
        if response:
            return JSONResponse(content=response)
        return Response(status_code=204)
        
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error"}
            }
        )
    except Exception as e:
        logger.exception("MCP request failed")
        return JSONResponse(
            status_code=500,
            content={
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32603, "message": str(e)}
            }
        )


@app.get("/mcp/sse")
async def mcp_sse_endpoint(request: Request):
    token = extract_bearer_token(request)
    session_id = session_manager.create_session(token=token)
    
    async def event_generator():
        yield {
            "event": "session",
            "data": json.dumps({"session_id": session_id})
        }
        
        yield {
            "event": "server_info",
            "data": json.dumps({
                "name": settings.server_name,
                "version": settings.server_version,
                "protocolVersion": "2024-11-05"
            })
        }
        
        while True:
            if await request.is_disconnected():
                session_manager.delete_session(session_id)
                break
            
            yield {
                "event": "ping",
                "data": json.dumps({"timestamp": datetime.utcnow().isoformat()})
            }
            
            import asyncio
            await asyncio.sleep(30)
    
    return EventSourceResponse(event_generator())


@app.post("/mcp/sse/{session_id}")
async def mcp_sse_request(session_id: str, request: Request):
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    token = extract_bearer_token(request) or session.get("token")
    set_request_token(token)
    
    try:
        body = await request.json()
        
        async def stream_response():
            yield {
                "event": "progress",
                "data": json.dumps({"status": "processing", "request_id": body.get("id")})
            }
            
            response = await process_mcp_request(body)
            
            yield {
                "event": "result",
                "data": json.dumps(response) if response else "{}"
            }
            
            yield {
                "event": "done",
                "data": json.dumps({"request_id": body.get("id")})
            }
        
        return EventSourceResponse(stream_response())
        
    except Exception as e:
        logger.exception("SSE request failed")
        raise HTTPException(status_code=500, detail=str(e))


async def process_mcp_request(req: dict[str, Any]) -> dict[str, Any] | None:
    method = req.get("method", "")
    params = req.get("params", {})
    req_id = req.get("id")
    
    logger.debug(f"Processing MCP method: {method}")
    
    try:
        if method == "initialize":
            result = await handle_initialize(params)
        elif method == "initialized":
            return None
        elif method == "tools/list":
            result = await handle_list_tools()
        elif method == "tools/call":
            result = await handle_call_tool(params)
        elif method == "resources/list":
            result = await handle_list_resources()
        elif method == "prompts/list":
            result = await handle_list_prompts()
        elif method == "ping":
            result = {"pong": True}
        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"}
            }
        
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": result
        }
        
    except ValueError as e:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32602, "message": str(e)}
        }
    except Exception as e:
        logger.exception(f"Error processing method: {method}")
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32603, "message": str(e)}
        }


@app.get("/api/tools")
async def list_tools_api():
    return {
        "tools": [
            {
                "name": name,
                "description": info["description"],
                "parameters": info["inputSchema"]
            }
            for name, info in TOOLS.items()
        ]
    }


@app.post("/api/tools/{tool_name}")
async def call_tool_api(tool_name: str, request: Request):
    if tool_name not in TOOLS:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_name}")
    
    token = extract_bearer_token(request)
    set_request_token(token)
    
    try:
        body = await request.json()
    except:
        body = {}
    
    tool_func = TOOLS[tool_name]["function"]
    result = await tool_func(**body)
    return result


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "server:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True
    )
