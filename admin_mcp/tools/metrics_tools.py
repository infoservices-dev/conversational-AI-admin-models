from typing import Any
from tools.base import make_request


async def get_metrics_namespaces(
    account_id: str,
    region: str,
    timerange: str
) -> dict[str, Any]:
    return await make_request(
        method="GET",
        endpoint="/metrics-namespaces",
        params={
            "account_id": account_id,
            "region": region,
            "timerange": timerange
        }
    )


async def get_metrics_metadata(
    account_id: str,
    region: str,
    timerange: str,
    service: str
) -> dict[str, Any]:
    return await make_request(
        method="GET",
        endpoint="/metrics-metadata",
        params={
            "account_id": account_id,
            "region": region,
            "timerange": timerange,
            "service": service
        }
    )
