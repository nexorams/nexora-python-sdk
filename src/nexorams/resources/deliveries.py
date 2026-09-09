"""Nexora Webhook Deliveries Resource.

Provides audit logging, attempt metrics, and manual redelivery triggers
for webhook events dispatched across developer project endpoints.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from .._http import HttpClient


class WebhookDeliveriesResource:
    """Resource for inspecting and retrying webhook delivery attempts."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def list(
        self,
        endpoint_id: Optional[str] = None,
        status: Optional[str] = None,
        page: Optional[int] = None,
        limit: Optional[int] = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """List recent webhook delivery attempts across project endpoints.

        Args:
            endpoint_id: Filter by specific webhook endpoint ID.
            status: Filter by delivery status ('SUCCESS', 'FAILED', 'PENDING', 'RETRY_SCHEDULED').
            page: 1-indexed page offset.
            limit: Maximum records per page (up to 100).

        Returns:
            Paginated dictionary with 'data' (list of delivery logs) and 'pagination' metadata.
        """
        params: dict[str, Any] = {}
        if endpoint_id is not None:
            params["endpointId"] = endpoint_id
        if status is not None:
            params["status"] = status
        if page is not None:
            params["page"] = page
        if limit is not None:
            params["limit"] = limit
        params.update(kwargs)

        return self._http.get("/webhook-deliveries", params=params)

    def get(self, id: str) -> dict[str, Any]:
        """Get full delivery attempt details by ID, including payload, headers, duration, and error trace."""
        return self._http.get(f"/webhook-deliveries/{id}")

    def retrieve(self, id: str) -> dict[str, Any]:
        """Alias for get(id)."""
        return self.get(id)

    def retry(self, id: str) -> dict[str, Any]:
        """Manually trigger a redelivery of a failed webhook event attempt."""
        return self._http.post(f"/webhook-deliveries/{id}/retry", json_data={})
