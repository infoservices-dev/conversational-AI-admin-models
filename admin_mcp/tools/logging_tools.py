from typing import Any
from tools.base import make_request


async def onboard_logging_config(
    client_id: str,
    aws_account_id: str,
    source: str,
    log_selector: list[str]
) -> dict[str, Any]:
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
