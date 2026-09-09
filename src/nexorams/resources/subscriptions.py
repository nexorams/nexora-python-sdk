"""Nexora Subscriptions Resource.

Retrieves active organization subscription metadata, plan tiers, active feature counts,
resource limits, and authoritative 30-day trial status.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .._http import HttpClient


class SubscriptionsResource:
    """Resource for inspecting organization subscription and trial status."""

    def __init__(self, http: HttpClient) -> None:
        self._http = http

    def get(self, organization_id: str) -> dict[str, Any]:
        """Retrieve subscription and trial status for an organization.

        Args:
            organization_id: Target organization ID.

        Returns:
            Dictionary with subscription details, active features, limits, and trial dates.
        """
        return self._http.get(f"/organizations/{organization_id}/subscription")

    def retrieve(self, organization_id: str) -> dict[str, Any]:
        """Alias for get(organization_id)."""
        return self.get(organization_id)
