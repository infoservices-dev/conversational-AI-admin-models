from typing import Any
from tools.base import make_request


async def get_firing_alerts() -> dict[str, Any]:
    return await make_request(
        method="GET",
        endpoint="/api/v1/alerts/firing-alerts"
    )


async def get_datasources() -> dict[str, Any]:
    return await make_request(
        method="GET",
        endpoint="/api/v1/alerts/datasources"
    )


async def create_alert(
    title: str,
    severity: str,
    receiver: str,
    description: str,
    datasource: str,
    threshold_value: float,
    for_duration: str = "5m",
    lookback_seconds: int = 600,
    prom_expr: str | None = None,
    log_expr: str | None = None
) -> dict[str, Any]:
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
        
    return await make_request(
        method="POST",
        endpoint="/api/v1/alerts/",
        json_data=payload
    )


async def get_all_alerts() -> dict[str, Any]:
    return await make_request(
        method="GET",
        endpoint="/api/v1/alerts/get_alerts/"
    )


async def update_alert(
    alert_id: str,
    title: str | None = None,
    severity: str | None = None,
    receiver: str | None = None,
    description: str | None = None,
    datasource: str | None = None,
    threshold_value: float | None = None,
    for_duration: str | None = None,
    lookback_seconds: int | None = None,
    prom_expr: str | None = None,
    log_expr: str | None = None
) -> dict[str, Any]:
    payload = {}
    
    if title is not None:
        payload["title"] = title
    if severity is not None:
        payload["severity"] = severity
    if receiver is not None:
        payload["receiver"] = receiver
    if description is not None:
        payload["description"] = description
    if datasource is not None:
        payload["datasource"] = datasource
    if threshold_value is not None:
        payload["threshold_value"] = threshold_value
    if for_duration is not None:
        payload["for_duration"] = for_duration
    if lookback_seconds is not None:
        payload["lookback_seconds"] = lookback_seconds
    if prom_expr is not None:
        payload["prom_expr"] = prom_expr
    if log_expr is not None:
        payload["log_expr"] = log_expr
        
    return await make_request(
        method="PUT",
        endpoint=f"/api/v1/alerts/update_alerts/{alert_id}",
        json_data=payload
    )


async def delete_alert(alert_uid: str) -> dict[str, Any]:
    return await make_request(
        method="DELETE",
        endpoint=f"/api/v1/alerts/delete_alerts/{alert_uid}"
    )


async def get_specific_alert(alert_id: str) -> dict[str, Any]:
    return await make_request(
        method="GET",
        endpoint=f"/api/v1/alerts/specific_alerts/{alert_id}"
    )

async def get_metrics_catalog() -> dict[str, Any]:
    return await make_request(
        method="GET",
        endpoint="/api/v1/alerts/metrics/catalog"
    )

async def get_dashboards() -> dict[str, Any]:
    return await make_request(
        method="GET",
        endpoint="/api/v1/alerts/dashboards"
    )

async def get_alertmanager_groups() -> dict[str, Any]:
    return await make_request(
        method="GET",
        endpoint="/api/v1/alerts/alertmanager/groups"
    )

async def get_contact_points() -> dict[str, Any]:
    return await make_request(
        method="GET",
        endpoint="/api/v1/alerts/alertmanager/contact-points"
    )

async def get_silences() -> dict[str, Any]:
    return await make_request(
        method="GET",
        endpoint="/api/v1/alerts/alertmanager/silences"
    )