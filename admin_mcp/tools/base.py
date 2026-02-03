import httpx
import logging
from typing import Any
from contextvars import ContextVar

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings

logger = logging.getLogger(__name__)

request_token: ContextVar[str | None] = ContextVar("request_token", default=None)


def set_request_token(token: str | None):
    request_token.set(token)


def get_auth_headers() -> dict[str, str]:
    token = request_token.get()
    if token:
        return {"Authorization": f"Bearer {token}"}
    if settings.bearer_token:
        return {"Authorization": f"Bearer {settings.bearer_token}"}
    return {}


async def make_request(
    method: str,
    endpoint: str,
    json_data: dict | None = None,
    params: dict | None = None,
) -> dict[str, Any]:
    url = f"{settings.backend_api_url}{endpoint}"
    headers = get_auth_headers()
    headers["Content-Type"] = "application/json"
    
    try:
        async with httpx.AsyncClient(timeout=settings.api_timeout) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                json=json_data,
                params=params,
            )
            response.raise_for_status()
            
            try:
                data = response.json()
            except Exception:
                data = {"raw_response": response.text}
                
            logger.info(f"API request successful: {method} {endpoint}")
            return {"success": True, "data": data, "status_code": response.status_code}
            
    except httpx.TimeoutException as e:
        logger.error(f"Request timeout: {method} {endpoint} - {e}")
        return {"success": False, "error": f"Request timeout: {str(e)}", "status_code": 408}
        
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error: {method} {endpoint} - {e.response.status_code}")
        return {
            "success": False, 
            "error": f"HTTP {e.response.status_code}: {e.response.text}",
            "status_code": e.response.status_code
        }
        
    except Exception as e:
        logger.exception(f"Request failed: {method} {endpoint}")
        return {"success": False, "error": str(e), "status_code": 500}
