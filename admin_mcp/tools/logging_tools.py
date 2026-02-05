from typing import Any
from tools.base import make_request


async def onboard_logging_config(
    client_id: str,
    aws_account_id: str,
    source: str,
    log_selector: list[str]
) -> dict[str, Any]:
    """Onboard a new logging configuration.
    
    Returns:
        dict containing the onboarding response.
    """
    return await make_request(
        method="POST",
        endpoint="/api/v1/logging/onboard",
        json_data={
            "client_id": client_id,
            "aws_account_id": aws_account_id,
            "source": source,
            "log_selector": log_selector
        }
    )


async def get_logging_configs(
    client_id: str,
    aws_account_id: str
) -> dict[str, Any]:
    """Get all logging configurations for a client.
    
    Returns:
        dict containing logging configurations.
    """
    return await make_request(
        method="GET",
        endpoint=f"/api/v1/logging/configs/{client_id}/awsid-{aws_account_id}"
    )


async def delete_logging_config(
    client_id: str,
    aws_account_id: str,
    source: str,
    log_selector: list[str]
) -> dict[str, Any]:
    """Delete a logging configuration.
    
    Returns:
        dict containing the deletion response.
    """
    return await make_request(
        method="DELETE",
        endpoint="/api/v1/logging/deboard",
        json_data={
            "client_id": client_id,
            "aws_account_id": aws_account_id,
            "source": source,
            "log_selector": log_selector
        }
    )

async def get_sync_status(client_id: str, aws_account_id: str) -> dict[str, Any]:
    """Get logging sync status for a client and AWS account.
    
    Returns:
        dict containing sync status information.
    """
    return await make_request(
        method="GET",
        endpoint=f"/api/v1/logging/sync-status/{client_id}/awsid-{aws_account_id}"
    )

async def validate_sync(client_id: str, aws_account_id: str) -> dict[str, Any]:
    """Validate logging configuration sync.
    
    Returns:
        dict containing validation results.
    """
    return await make_request(
        method="GET",
        endpoint=f"/api/v1/logging/validate-sync/{client_id}/awsid-{aws_account_id}"
    )
